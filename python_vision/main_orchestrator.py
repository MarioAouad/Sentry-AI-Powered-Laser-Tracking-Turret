"""
main_orchestrator.py — Sentry AI Vision Pipeline Entry Point
=============================================================
The central nervous system of the turret.  Runs two concurrent tasks
inside a single ``asyncio`` event loop:

    1.  **Vision Loop** — Captures webcam frames → HOG gate → YOLO +
        ByteTrack → EMA filter → Depth → Spatial → IK → Serial command.

    2.  **API Server** — FastAPI + uvicorn serving the React dashboard
        via WebSocket telemetry and MJPEG video stream.

State Machine:
    SCANNING  →  TRACKING  →  LOCKED
       ↑            ↓
       ←── REACQUIRING ──┘

Usage:
    cd python_vision
    python main_orchestrator.py
"""

from __future__ import annotations

import asyncio
import logging
import math
import sys
import time
from collections import deque
from pathlib import Path

import cv2
import numpy as np
import yaml

# ── Resolve project paths ───────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_DIR = SCRIPT_DIR / "config"
MODELS_DIR = SCRIPT_DIR / "models"

# Add the python_vision directory to sys.path so imports work
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from src.vision.cascade_detector import CascadeDetector
from src.vision.target_tracker import TargetTracker
from src.kinematics.signal_filter import SignalFilter
from src.kinematics.depth_estimator import DepthEstimator
from src.kinematics.spatial_calibrator import SpatialCalibrator
from src.kinematics.inverse_kinematics import InverseKinematics
from src.comms.serial_tether import SerialTether, STATE_SCANNING, STATE_LOCKED, STATE_OFF
from src.api.websocket_manager import WebSocketManager
from src.api.api_server import create_app, APISharedState


# ── Logging Setup ────────────────────────────────────────────────────
def _setup_logging() -> None:
    """Configure structured console logging for all sentry.* loggers."""
    root = logging.getLogger("sentry")
    root.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s │ %(levelname)-5s │ %(message)s",
        datefmt="%H:%M:%S",
    ))
    root.addHandler(handler)


# ── Config Loader ────────────────────────────────────────────────────
def _load_config() -> dict:
    """Load hardware_offsets.yaml."""
    config_path = CONFIG_DIR / "hardware_offsets.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ── System State Enum ────────────────────────────────────────────────
class TurretState:
    SCANNING = "Scanning"
    TARGET_DETECTED = "Target Detected"
    TRACKING_LOCKED = "Tracking Locked"
    REACQUIRING = "Reacquiring"


# ── Orchestrator ─────────────────────────────────────────────────────
class SentryOrchestrator:
    """
    Main pipeline controller.  Initialises all subsystems from the YAML
    config and runs the vision loop + API server concurrently.
    """

    def __init__(self, config: dict) -> None:
        self._config = config
        self._logger = logging.getLogger("sentry.orchestrator")

        # ── State ────────────────────────────────────────────────────
        self._state = TurretState.SCANNING
        self._running = True
        self._fps: float = 0.0
        self._confidence: float = 0.0
        self._pan: int = 90
        self._tilt: int = 90
        self._logs: deque[str] = deque(maxlen=10)
        self._track_lost_timer: float = 0.0

        # ── Camera ───────────────────────────────────────────────────
        cam_cfg = config["camera"]
        self._cam_index = cam_cfg["device_index"]
        self._frame_w = cam_cfg["frame_width"]
        self._frame_h = cam_cfg["frame_height"]

        # ── Vision: HOG Cascade ──────────────────────────────────────
        vis_cfg = config["vision"]
        self._cascade = CascadeDetector(
            min_consecutive=vis_cfg["hog_min_consecutive"],
            hit_threshold=vis_cfg["hog_hit_threshold"],
        )

        # ── Vision: YOLO + ByteTrack ─────────────────────────────────
        model_path = MODELS_DIR / "yolo11m-pose.pt"
        self._tracker = TargetTracker(
            model_path=model_path,
            confidence=vis_cfg["yolo_confidence"],
            device="cuda:0",
        )
        self._tracker.set_target_mode(vis_cfg["default_target_mode"])

        # ── Kinematics: Signal Filter ────────────────────────────────
        filt_cfg = config["filters"]
        self._filter = SignalFilter(
            alpha=filt_cfg["ema_alpha"],
            median_window=filt_cfg["median_window"],
        )

        # ── Kinematics: Depth Estimator ──────────────────────────────
        bio_cfg = config["biometrics"]
        self._depth = DepthEstimator(
            shoulder_width_cm=bio_cfg["shoulder_width_cm"],
            fov_h_deg=cam_cfg["fov_h_deg"],
            frame_width=self._frame_w,
        )

        # ── Kinematics: Spatial Calibrator ───────────────────────────
        off_cfg = config["turret_offset_cm"]
        self._spatial = SpatialCalibrator(
            frame_width=self._frame_w,
            frame_height=self._frame_h,
            focal_length_px=self._depth.focal_length_px,
            offset_x_cm=off_cfg["x"],
            offset_y_cm=off_cfg["y"],
            offset_z_cm=off_cfg["z"],
            affine_matrix_path=CONFIG_DIR / "dynamic_matrix.json",
        )

        # ── Kinematics: Inverse Kinematics ───────────────────────────
        self._ik = InverseKinematics()

        # ── Comms: Serial Tether ─────────────────────────────────────
        ser_cfg = config["serial"]
        self._serial = SerialTether(
            port=ser_cfg["port"],
            baud_rate=ser_cfg["baud_rate"],
            reconnect_timeout=ser_cfg["reconnect_timeout_sec"],
            auto_detect=ser_cfg["auto_detect"],
        )

        # ── Timing Constants ─────────────────────────────────────────
        self._track_lost_timeout = vis_cfg["track_lost_timeout_sec"]

        # ── API Shared State ─────────────────────────────────────────
        self._ws_manager = WebSocketManager()
        self._shared = APISharedState()
        self._shared.system_running = True
        self._shared.target_mode = vis_cfg["default_target_mode"]
        self._shared.on_target_mode_change = self._on_target_mode_change
        self._shared.on_system_command = self._on_system_command

        self._app = create_app(self._ws_manager, self._shared)

        self._log("System initialised")
        self._log("Camera index: %d" % self._cam_index)
        self._log("Model: YOLO11m-Pose + ByteTrack")

    # ── Callbacks from the API ───────────────────────────────────────
    def _on_target_mode_change(self, mode: str) -> None:
        self._tracker.set_target_mode(mode)  # type: ignore[arg-type]
        self._shared.target_mode = mode
        self._log(f"Target mode → {mode}")

    def _on_system_command(self, command: str) -> None:
        if command == "stop":
            self._running = False
            self._serial.send_command(90, 90, STATE_OFF)
            self._log("System STOPPED by user")
        elif command == "start":
            self._running = True
            self._state = TurretState.SCANNING
            self._log("System STARTED by user")
        elif command == "calibrate":
            self._log("Calibration requested — run pre_deployment_calibration.py")

    # ── Logging Helper ───────────────────────────────────────────────
    def _log(self, message: str) -> None:
        self._logger.info(message)
        self._logs.appendleft(message)

    # ── Telemetry Builder ────────────────────────────────────────────
    def _build_telemetry(self) -> dict:
        """Build the telemetry JSON matching the frontend's expected shape."""
        if self._state == TurretState.TRACKING_LOCKED:
            indicator = "Active"
        elif self._state == TurretState.TARGET_DETECTED:
            indicator = "Armed"
        else:
            indicator = "Standby"

        return {
            "systemState": self._state,
            "fps": int(round(self._fps)),
            "confidence": round(self._confidence, 2),
            "tracker": "ByteTrack",
            "model": "YOLO11m-Pose",
            "yaw": self._pan,
            "pitch": self._tilt,
            "indicator": indicator,
            "targetMode": self._shared.target_mode,
            "logs": list(self._logs),
        }

    # ── Frame Annotation ─────────────────────────────────────────────
    def _annotate_frame(self, frame: np.ndarray) -> np.ndarray:
        """Draw the HUD overlay on the frame for the MJPEG stream."""
        h, w = frame.shape[:2]
        annotated = frame.copy()

        # State badge
        color_map = {
            TurretState.SCANNING: (248, 189, 56),        # Cyan-ish
            TurretState.TARGET_DETECTED: (8, 171, 234),  # Yellow
            TurretState.TRACKING_LOCKED: (86, 197, 34),  # Green
            TurretState.REACQUIRING: (22, 115, 249),     # Orange
        }
        color = color_map.get(self._state, (255, 255, 255))

        # Top-left state label
        cv2.putText(annotated, f"STATE: {self._state}", (10, 25),
                     cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        # FPS
        cv2.putText(annotated, f"FPS: {int(self._fps)}", (10, 50),
                     cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        # Servo angles
        cv2.putText(annotated, f"PAN: {self._pan}  TILT: {self._tilt}", (10, 75),
                     cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        # Target mode
        cv2.putText(annotated, f"TARGET: {self._shared.target_mode.upper()}", (10, 100),
                     cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        # Crosshair at frame center
        cv2.line(annotated, (w // 2 - 20, h // 2), (w // 2 + 20, h // 2), (255, 255, 255), 1)
        cv2.line(annotated, (w // 2, h // 2 - 20), (w // 2, h // 2 + 20), (255, 255, 255), 1)

        return annotated

    # ── Vision Loop ──────────────────────────────────────────────────
    async def _vision_loop(self) -> None:
        """
        The high-speed frame processing pipeline.  Runs in a thread
        executor to avoid blocking the asyncio event loop.
        """
        self._logger.info("═══════════════════════════════════════════")
        self._logger.info("  SENTRY AI — Vision Loop Starting")
        self._logger.info("═══════════════════════════════════════════")

        # Connect serial (non-fatal if it fails — turret just won't move)
        if self._serial.connect():
            self._serial.start()
            self._log("Serial tether connected")
        else:
            self._log("Serial tether OFFLINE — turret will not move")

        # Open the webcam
        cap = cv2.VideoCapture(self._cam_index)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._frame_w)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._frame_h)

        if not cap.isOpened():
            self._log("FATAL: Cannot open webcam at index %d" % self._cam_index)
            self._logger.error("Cannot open webcam — aborting vision loop")
            return

        self._log("Webcam opened — resolution %dx%d" % (self._frame_w, self._frame_h))
        self._log("Entering SCANNING state (HOG+SVM active)")

        frame_times: deque[float] = deque(maxlen=30)

        try:
            while self._running:
                t_start = time.perf_counter()

                ok, frame = cap.read()
                if not ok:
                    await asyncio.sleep(0.01)
                    continue

                # ── State Machine ────────────────────────────────────
                if self._state == TurretState.SCANNING:
                    # Level 1: HOG+SVM lightweight scan
                    cascade_result = self._cascade.detect(frame)

                    if cascade_result.detected:
                        self._state = TurretState.TARGET_DETECTED
                        self._cascade.reset()
                        self._log("HOG cascade triggered — waking YOLO")
                        # Send SCANNING state to ESP32
                        self._serial.send_command(self._pan, self._tilt, STATE_SCANNING)

                elif self._state in (
                    TurretState.TARGET_DETECTED,
                    TurretState.TRACKING_LOCKED,
                    TurretState.REACQUIRING,
                ):
                    # Level 2: YOLO11m-Pose + ByteTrack
                    tracker_result = self._tracker.track(frame)

                    if tracker_result.detected:
                        self._confidence = tracker_result.confidence
                        self._track_lost_timer = 0.0

                        # Update state
                        if self._state != TurretState.TRACKING_LOCKED:
                            self._state = TurretState.TRACKING_LOCKED
                            self._log("Track LOCKED — ID #%d" % tracker_result.track_id)

                        # ── Pipeline: Filter → Depth → Spatial → IK ─
                        # Stage 1: EMA filter
                        filtered = self._filter.update(
                            tracker_result.target_px[0],
                            tracker_result.target_px[1],
                        )

                        # Stage 2: Depth estimation
                        z_cm = self._depth.estimate(
                            tracker_result.left_shoulder_px,
                            tracker_result.right_shoulder_px,
                        )

                        # Stage 3: Spatial calibration
                        spatial = self._spatial.transform(filtered.x, filtered.y, z_cm)

                        # Stage 4: Inverse kinematics
                        servo = self._ik.compute(spatial.x, spatial.y, spatial.z)
                        self._pan = servo.pan
                        self._tilt = servo.tilt

                        # Stage 5: Serial command
                        self._serial.send_command(servo.pan, servo.tilt, STATE_LOCKED)

                        # Draw target circle on the annotated frame
                        cv2.circle(
                            frame,
                            (int(filtered.x), int(filtered.y)),
                            10, (0, 0, 255), 2,
                        )

                    else:
                        # No detection this frame — check timeout
                        self._track_lost_timer += time.perf_counter() - t_start
                        self._confidence = 0.0

                        if self._state != TurretState.REACQUIRING:
                            self._state = TurretState.REACQUIRING
                            self._log("Track LOST — reacquiring...")

                        if self._track_lost_timer >= self._track_lost_timeout:
                            # Timeout: fall back to HOG scanning
                            self._state = TurretState.SCANNING
                            self._filter.reset()
                            self._track_lost_timer = 0.0
                            self._serial.send_command(90, 90, STATE_SCANNING)
                            self._log("Reacquisition timeout — returning to SCANNING")

                # ── FPS Calculation ───────────────────────────────────
                t_end = time.perf_counter()
                frame_times.append(t_end - t_start)
                if len(frame_times) > 1:
                    avg_time = sum(frame_times) / len(frame_times)
                    self._fps = 1.0 / avg_time if avg_time > 0 else 0.0

                # ── Annotate & publish MJPEG frame ────────────────────
                annotated = self._annotate_frame(frame)
                _, jpeg_buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 70])
                self._shared.latest_frame_jpeg = jpeg_buf.tobytes()

                # ── Broadcast telemetry to WebSocket clients ──────────
                telemetry = self._build_telemetry()
                await self._ws_manager.set_telemetry(telemetry)
                await self._ws_manager.broadcast()

                # Yield control to the event loop briefly
                await asyncio.sleep(0.001)

        except Exception as exc:
            self._logger.exception("Vision loop crashed: %s", exc)
        finally:
            cap.release()
            self._serial.send_command(90, 90, STATE_OFF)
            self._serial.stop()
            self._log("Vision loop terminated — camera released")

    # ── Entry Point ──────────────────────────────────────────────────
    async def run(self) -> None:
        """Launch both the vision loop and the API server concurrently."""
        import uvicorn

        api_cfg = self._config["api"]

        self._logger.info("═══════════════════════════════════════════")
        self._logger.info("  SENTRY AI — Orchestrator Starting")
        self._logger.info("  API: http://%s:%d", api_cfg["host"], api_cfg["port"])
        self._logger.info("  WebSocket: ws://%s:%d/ws/telemetry", api_cfg["host"], api_cfg["port"])
        self._logger.info("  MJPEG: http://%s:%d/video-feed", api_cfg["host"], api_cfg["port"])
        self._logger.info("═══════════════════════════════════════════")

        # Create the uvicorn server config
        uvi_config = uvicorn.Config(
            app=self._app,
            host=api_cfg["host"],
            port=api_cfg["port"],
            log_level="warning",
            access_log=False,
        )
        server = uvicorn.Server(uvi_config)

        # Run both tasks concurrently
        await asyncio.gather(
            server.serve(),
            self._vision_loop(),
        )


# ── Main ─────────────────────────────────────────────────────────────
def main() -> None:
    _setup_logging()
    logger = logging.getLogger("sentry.main")

    logger.info("Loading configuration from config/hardware_offsets.yaml")
    config = _load_config()

    orchestrator = SentryOrchestrator(config)
    asyncio.run(orchestrator.run())


if __name__ == "__main__":
    main()
