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
        self._running = True
        self._fps: float = 0.0
        self._confidence: float = 0.0
        self._pan: int = 90
        self._tilt: int = 90
        self._logs: deque[str] = deque(maxlen=10)
        self._track_lost_timer: float = 0.0

        # Debug pipeline values (exposed in telemetry)
        self._debug_raw_pan: int = 90
        self._debug_raw_tilt: int = 90
        self._debug_spatial: tuple = (0.0, 0.0, 0.0)
        self._debug_depth: float = 0.0
        self._debug_target_px: tuple = (0.0, 0.0)
        self._debug_vlaser_px: tuple = (0.0, 0.0)  # Where laser hits on camera

        # ── Camera ───────────────────────────────────────────────────
        cam_cfg = config["camera"]
        self._cam_index = cam_cfg["device_index"]
        self._frame_w = cam_cfg["frame_width"]
        self._frame_h = cam_cfg["frame_height"]

        # ── Vision: HOG Cascade ──────────────────────────────────────
        vis_cfg = config["vision"]
        self._bypass_hog = vis_cfg.get("bypass_hog_gate", False)

        # If bypassing HOG, start directly in TARGET_DETECTED so YOLO runs
        if self._bypass_hog:
            self._state = TurretState.TARGET_DETECTED
            self._cascade = None  # Not needed
            self._logger.info("HOG gate BYPASSED — YOLO runs on every frame")
        else:
            self._state = TurretState.SCANNING
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
        )

        # ── Kinematics: Inverse Kinematics ───────────────────────────
        dir_cfg = config.get("servo_direction", {})
        self._pan_dir = dir_cfg.get("pan", 1)
        self._tilt_dir = dir_cfg.get("tilt", 1)
        self._ik = InverseKinematics(
            pan_direction=self._pan_dir,
            tilt_direction=self._tilt_dir,
        )

        # ── Servo Trim (fine-tune bias) ──────────────────────────────
        trim_cfg = config.get("servo_trim", {})
        self._pan_trim = trim_cfg.get("pan", 0)
        self._tilt_trim = trim_cfg.get("tilt", 0)
        if self._pan_trim or self._tilt_trim:
            self._logger.info("Servo trim: pan=%+d, tilt=%+d", self._pan_trim, self._tilt_trim)

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
            "fps": round(self._fps, 1),
            "confidence": round(self._confidence, 2),
            "tracker": "ByteTrack",
            "model": "YOLO11m-Pose",
            "yaw": self._pan,
            "pitch": self._tilt,
            "indicator": indicator,
            "targetMode": self._shared.target_mode,
            "logs": list(self._logs),
            # Pipeline debug — shows exactly what the math computed
            "debug": {
                "rawPan": self._debug_raw_pan,
                "rawTilt": self._debug_raw_tilt,
                "spatialX": round(self._debug_spatial[0], 1),
                "spatialY": round(self._debug_spatial[1], 1),
                "spatialZ": round(self._debug_spatial[2], 1),
                "depthCm": round(self._debug_depth, 1),
                "targetPx": [round(self._debug_target_px[0], 1),
                             round(self._debug_target_px[1], 1)],
                "vlaserPx": [round(self._debug_vlaser_px[0], 1),
                             round(self._debug_vlaser_px[1], 1)],
                "frameW": self._frame_w,
                "frameH": self._frame_h,
                "panDir": self._pan_dir,
                "tiltDir": self._tilt_dir,
                "panTrim": self._pan_trim,
                "tiltTrim": self._tilt_trim,
            },
        }

    # ── COCO Skeleton Connections ──────────────────────────────────────
    # Pairs of keypoint indices to draw as bones
    _SKELETON = [
        (0, 1), (0, 2), (1, 3), (2, 4),          # Face
        (5, 6),                                     # Shoulders
        (5, 7), (7, 9), (6, 8), (8, 10),           # Arms
        (5, 11), (6, 12), (11, 12),                # Torso
        (11, 13), (13, 15), (12, 14), (14, 16),    # Legs
    ]

    def _draw_skeleton(self, frame: np.ndarray, keypoints: np.ndarray) -> None:
        """Draw the 17-point COCO skeleton on the frame."""
        kp_color = (0, 255, 255)    # Yellow dots
        bone_color = (0, 200, 200)  # Yellow-ish bones
        target_kp_color = (0, 0, 255)  # Red for target keypoints

        # Draw bones (lines between connected keypoints)
        for i, j in self._SKELETON:
            if keypoints[i][2] > 0.3 and keypoints[j][2] > 0.3:
                pt1 = (int(keypoints[i][0]), int(keypoints[i][1]))
                pt2 = (int(keypoints[j][0]), int(keypoints[j][1]))
                cv2.line(frame, pt1, pt2, bone_color, 2)

        # Draw keypoint dots
        for idx, (x, y, conf) in enumerate(keypoints):
            if conf > 0.3:
                cv2.circle(frame, (int(x), int(y)), 4, kp_color, -1)

    def _annotate_frame(
        self,
        frame: np.ndarray,
        cascade_bbox: tuple[int, int, int, int] | None = None,
        tracker_result=None,
        target_xy: tuple[float, float] | None = None,
        depth_cm: float = 0.0,
        spatial_debug: tuple[float, float, float] | None = None,
    ) -> np.ndarray:
        """Draw the full HUD overlay on the frame for the MJPEG stream."""
        h, w = frame.shape[:2]
        annotated = frame.copy()

        # ── State badge colors ───────────────────────────────────────
        color_map = {
            TurretState.SCANNING: (248, 189, 56),        # Cyan
            TurretState.TARGET_DETECTED: (8, 171, 234),  # Yellow
            TurretState.TRACKING_LOCKED: (86, 197, 34),  # Green
            TurretState.REACQUIRING: (22, 115, 249),     # Orange
        }
        color = color_map.get(self._state, (255, 255, 255))

        # ── HOG bounding box (SCANNING mode) ─────────────────────────
        if cascade_bbox is not None:
            bx, by, bw, bh = cascade_bbox
            cv2.rectangle(annotated, (bx, by), (bx + bw, by + bh), (248, 189, 56), 2)
            cv2.putText(annotated, "HOG", (bx, by - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (248, 189, 56), 1)

        # ── YOLO bbox + skeleton + target (TRACKING mode) ────────────
        if tracker_result is not None and tracker_result.detected:
            x1, y1, x2, y2 = tracker_result.bbox

            # Bounding box
            cv2.rectangle(annotated, (int(x1), int(y1)), (int(x2), int(y2)),
                          (86, 197, 34), 2)
            label = f"ID#{tracker_result.track_id}  {tracker_result.confidence:.0%}"
            cv2.putText(annotated, label, (int(x1), int(y1) - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (86, 197, 34), 2)

            # Skeleton
            self._draw_skeleton(annotated, tracker_result.all_keypoints)

            # Target crosshair (red — where YOLO says the body part is)
            if target_xy is not None:
                tx, ty = int(target_xy[0]), int(target_xy[1])
                cv2.drawMarker(annotated, (tx, ty), (0, 0, 255),
                               cv2.MARKER_CROSS, 20, 2)
                cv2.circle(annotated, (tx, ty), 12, (0, 0, 255), 2)

            # Depth label
            if depth_cm > 0:
                cv2.putText(annotated, f"Z={depth_cm:.0f}cm", (int(x1), int(y2) + 18),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        # ── HUD text overlay ─────────────────────────────────────────
        cv2.putText(annotated, f"STATE: {self._state}", (10, 25),
                     cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        cv2.putText(annotated, f"FPS: {int(self._fps)}", (10, 50),
                     cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        cv2.putText(annotated, f"PAN: {self._pan}  TILT: {self._tilt}", (10, 75),
                     cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        cv2.putText(annotated, f"TARGET: {self._shared.target_mode.upper()}", (10, 100),
                     cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        # Debug: turret-relative coordinates + depth info
        if spatial_debug is not None:
            sx, sy, sz = spatial_debug
            cv2.putText(annotated, f"T_XYZ: ({sx:.0f}, {sy:.0f}, {sz:.0f})cm",
                        (10, 125), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 255), 1)
        if depth_cm > 0:
            method = self._depth.last_method
            cv2.putText(annotated, f"DEPTH: {depth_cm:.0f}cm [{method}]",
                        (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 255, 180), 1)

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

        # Open the webcam (use DirectShow on Windows for faster capture)
        cap = cv2.VideoCapture(self._cam_index, cv2.CAP_DSHOW)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._frame_w)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._frame_h)
        cap.set(cv2.CAP_PROP_FPS, 60)            # Request highest available FPS
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)       # Minimize capture latency
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))  # Faster codec

        if not cap.isOpened():
            self._log("FATAL: Cannot open webcam at index %d" % self._cam_index)
            self._logger.error("Cannot open webcam — aborting vision loop")
            return

        self._log("Webcam opened — resolution %dx%d" % (self._frame_w, self._frame_h))
        if self._bypass_hog:
            self._log("HOG bypassed — YOLO active immediately")
        else:
            self._log("Entering SCANNING state (HOG+SVM active)")

        frame_times: deque[float] = deque(maxlen=10)
        last_broadcast = time.perf_counter()
        frame_count = 0  # For skipping JPEG encode on alternating frames

        # Per-frame annotation data
        cascade_bbox = None
        tracker_result_viz = None
        target_xy = None
        depth_cm = 0.0
        spatial_debug = None

        try:
            while self._running:
                t_start = time.perf_counter()

                ok, frame = cap.read()
                if not ok:
                    await asyncio.sleep(0.01)
                    continue

                # Reset per-frame viz data
                cascade_bbox = None
                tracker_result_viz = None
                target_xy = None
                spatial_debug = None

                # ── State Machine ────────────────────────────────────
                if self._state == TurretState.SCANNING and not self._bypass_hog:
                    # Level 1: HOG+SVM lightweight scan
                    cascade_result = self._cascade.detect(frame)

                    # Store bbox for visualization even before gate opens
                    cascade_bbox = cascade_result.bbox

                    if cascade_result.detected:
                        self._state = TurretState.TARGET_DETECTED
                        self._cascade.reset()
                        self._log("HOG cascade triggered — waking YOLO")
                        self._serial.send_command(self._pan, self._tilt, STATE_SCANNING)

                elif self._state in (
                    TurretState.TARGET_DETECTED,
                    TurretState.TRACKING_LOCKED,
                    TurretState.REACQUIRING,
                ):
                    # Level 2: YOLO11m-Pose + ByteTrack
                    tracker_result = self._tracker.track(frame)
                    tracker_result_viz = tracker_result  # Store for annotation

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
                        target_xy = (filtered.x, filtered.y)

                        # Stage 2: Depth estimation (with bbox fallback)
                        depth_cm = self._depth.estimate(
                            tracker_result.left_shoulder_px,
                            tracker_result.right_shoulder_px,
                            bbox=tracker_result.bbox,
                        )

                        # Stage 3: Spatial calibration
                        spatial = self._spatial.transform(filtered.x, filtered.y, depth_cm)
                        spatial_debug = (spatial.x, spatial.y, spatial.z)

                        # Stage 4: Inverse kinematics + trim correction
                        servo = self._ik.compute(spatial.x, spatial.y, spatial.z)
                        raw_pan = servo.pan + self._pan_trim
                        raw_tilt = servo.tilt + self._tilt_trim

                        # Clamp to FOV-safe range (prevent laser overshooting camera)
                        self._pan = max(30, min(150, raw_pan))
                        self._tilt = max(30, min(150, raw_tilt))

                        # Store debug values for telemetry
                        self._debug_raw_pan = servo.pan
                        self._debug_raw_tilt = servo.tilt
                        self._debug_spatial = (spatial.x, spatial.y, spatial.z)
                        self._debug_depth = depth_cm
                        self._debug_target_px = target_xy

                        # Compute virtual laser pixel position (reverse projection)
                        if depth_cm > 0:
                            # Subtract trim because trim is for physical hardware correction.
                            # The camera view assumes perfect hardware.
                            sim_pan = self._pan - self._pan_trim
                            sim_tilt = self._tilt - self._tilt_trim
                            vl_x, vl_y = self._spatial.reverse_project(
                                sim_pan, sim_tilt,
                                self._pan_dir, self._tilt_dir,
                                depth_cm,
                            )
                            self._debug_vlaser_px = (float(vl_x), float(vl_y))
                        else:
                            self._debug_vlaser_px = target_xy

                        # Stage 5: Serial command
                        self._serial.send_command(self._pan, self._tilt, STATE_LOCKED)

                    else:
                        # No detection this frame — check timeout
                        self._track_lost_timer += time.perf_counter() - t_start
                        self._confidence = 0.0

                        if self._state != TurretState.REACQUIRING:
                            self._state = TurretState.REACQUIRING
                            self._log("Track LOST — reacquiring...")

                        if self._track_lost_timer >= self._track_lost_timeout:
                            # Timeout: fall back
                            self._filter.reset()
                            self._track_lost_timer = 0.0
                            self._serial.send_command(90, 90, STATE_SCANNING)
                            if self._bypass_hog:
                                # Stay in TARGET_DETECTED so YOLO keeps running
                                self._state = TurretState.TARGET_DETECTED
                                self._log("Reacquisition timeout — continuing YOLO scan")
                            else:
                                self._state = TurretState.SCANNING
                                self._log("Reacquisition timeout — returning to HOG scanning")

                # ── FPS Calculation ───────────────────────────────────
                t_end = time.perf_counter()
                frame_times.append(t_end - t_start)
                if len(frame_times) > 1:
                    avg_time = sum(frame_times) / len(frame_times)
                    self._fps = 1.0 / avg_time if avg_time > 0 else 0.0

                # ── Annotate & publish MJPEG frame ────────────────────
                frame_count += 1
                annotated = self._annotate_frame(
                    frame,
                    cascade_bbox=cascade_bbox,
                    tracker_result=tracker_result_viz,
                    target_xy=target_xy,
                    depth_cm=depth_cm,
                    spatial_debug=spatial_debug,
                )
                # Encode JPEG (quality 50 for speed; skip odd frames to halve encode cost)
                if frame_count % 2 == 0 or self._shared.latest_frame_jpeg is None:
                    _, jpeg_buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 50])
                    self._shared.latest_frame_jpeg = jpeg_buf.tobytes()

                # ── Broadcast telemetry to WebSocket clients ──────────
                # Throttle WS broadcasts to ~10Hz to avoid flooding
                now = time.perf_counter()
                if now - last_broadcast >= 0.1:
                    telemetry = self._build_telemetry()
                    await self._ws_manager.set_telemetry(telemetry)
                    await self._ws_manager.broadcast()
                    last_broadcast = now

                # Yield control to the event loop (minimal delay)
                await asyncio.sleep(0)

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
