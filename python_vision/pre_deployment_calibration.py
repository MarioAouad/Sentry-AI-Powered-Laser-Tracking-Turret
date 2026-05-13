"""
pre_deployment_calibration.py — 3-Point Laser Calibration
==========================================================
Standalone script that generates the ``config/dynamic_matrix.json``
affine correction matrix.  This corrects for static hardware sag, lens
distortion, and non-planar mounting that would otherwise cause the
laser to miss the target despite mathematically correct kinematics.

Procedure:
    1.  The script commands the turret to 3 preset servo angle pairs.
    2.  At each angle, the laser fires and the live camera feed is
        displayed in an OpenCV window.
    3.  The user clicks the laser dot on the screen (the bright red spot).
    4.  After 3 clicks, ``cv2.getAffineTransform`` maps the 3 clicked
        pixel positions to the 3 known servo angle pairs.
    5.  The resulting 2×3 affine matrix is saved to dynamic_matrix.json.

Usage:
    cd python_vision
    python pre_deployment_calibration.py
"""

from __future__ import annotations

import json
import logging
import math
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import yaml

# ── Path Setup ───────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_DIR = SCRIPT_DIR / "config"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from src.comms.serial_tether import SerialTether, STATE_LOCKED

# ── Logging ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-5s │ %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("sentry.calibration")

# ── Calibration Points ───────────────────────────────────────────────
# Three servo angle pairs that stay WITHIN the camera's FOV.
# Camera V-FOV is only ~46° (half=23°). The user confirmed that
# tilt=80 (10° from center) already shoots above the camera view,
# so we use very tight angles: ±10° pan, ±5° tilt.
# Format: (pan_degrees, tilt_degrees)
CALIBRATION_ANGLES: list[tuple[int, int]] = [
    (80, 87),    # Left, slightly above center
    (100, 87),   # Right, slightly above center
    (90, 95),    # Center, slightly below center
]


# ── Click Handler ────────────────────────────────────────────────────
class ClickCollector:
    """Collects mouse clicks on the OpenCV window."""

    def __init__(self) -> None:
        self.clicked: bool = False
        self.point: tuple[int, int] = (0, 0)

    def callback(self, event: int, x: int, y: int, flags: int, param: object) -> None:
        if event == cv2.EVENT_LBUTTONDOWN:
            self.point = (x, y)
            self.clicked = True
            logger.info("  → Click registered at pixel (%d, %d)", x, y)


# ── Main Calibration ─────────────────────────────────────────────────
def run_calibration() -> None:
    logger.info("═══════════════════════════════════════════")
    logger.info("  SENTRY AI — Pre-Deployment Calibration")
    logger.info("═══════════════════════════════════════════")

    # Load config
    config_path = CONFIG_DIR / "hardware_offsets.yaml"
    with config_path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    cam_cfg = config["camera"]
    ser_cfg = config["serial"]

    # Connect to the ESP32
    serial = SerialTether(
        port=ser_cfg["port"],
        baud_rate=ser_cfg["baud_rate"],
        auto_detect=ser_cfg["auto_detect"],
    )
    if not serial.connect():
        logger.error("Cannot connect to ESP32 — aborting calibration")
        sys.exit(1)
    serial.start()

    # Open the webcam at high resolution for better calibration accuracy
    cap = cv2.VideoCapture(cam_cfg["device_index"])
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

    if not cap.isOpened():
        logger.error("Cannot open webcam — aborting calibration")
        serial.stop()
        sys.exit(1)

    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    logger.info("Webcam opened — resolution %dx%d", actual_w, actual_h)
    logger.info("Point laser at a wall 2-3 meters away for best results.")

    # Collect pixel positions for each calibration angle
    pixel_points: list[tuple[int, int]] = []
    angle_points: list[tuple[int, int]] = []

    window_name = "Sentry Calibration — Click the laser dot"
    # Use WINDOW_NORMAL so you can drag the corners to make it fullscreen
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    # Force the window to open large immediately 
    cv2.resizeWindow(window_name, 1280, 720)

    collector = ClickCollector()
    cv2.setMouseCallback(window_name, collector.callback)

    for i, (pan, tilt) in enumerate(CALIBRATION_ANGLES):
        logger.info("")
        logger.info("── Point %d/%d ────────────────────────────", i + 1, len(CALIBRATION_ANGLES))
        logger.info("  Commanding turret to PAN=%d, TILT=%d", pan, tilt)

        # Command the turret to this position with laser ON (STATE_LOCKED)
        serial.send_command(pan, tilt, STATE_LOCKED)
        time.sleep(1.5)  # Wait for the servo to settle

        logger.info("  Now CLICK the laser dot on the camera feed")
        logger.info("  Press 'q' to abort calibration")

        collector.clicked = False

        while not collector.clicked:
            ok, frame = cap.read()
            if not ok:
                continue

            # Draw instructions on the frame
            cv2.putText(
                frame,
                f"Point {i+1}/{len(CALIBRATION_ANGLES)} — Click the LASER DOT",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2,
            )
            cv2.putText(
                frame,
                f"Servo: PAN={pan}, TILT={tilt}",
                (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1,
            )

            # Draw previously clicked points
            for j, pt in enumerate(pixel_points):
                cv2.circle(frame, pt, 8, (0, 255, 0), 2)
                cv2.putText(frame, f"P{j+1}", (pt[0]+10, pt[1]-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

            cv2.imshow(window_name, frame)
            key = cv2.waitKey(30) & 0xFF
            if key == ord("q"):
                logger.warning("Calibration aborted by user")
                cap.release()
                cv2.destroyAllWindows()
                serial.send_command(90, 90, 0)
                serial.stop()
                sys.exit(0)

        pixel_points.append(collector.point)
        angle_points.append((pan, tilt))
        logger.info("  ✓ Recorded: pixel=(%d, %d) → servo=(%d, %d)",
                     collector.point[0], collector.point[1], pan, tilt)

    # ── Compute Affine Transform ─────────────────────────────────────
    logger.info("")
    logger.info("── Computing Affine Transform ──────────────")

    # We need to map mathematically PREDICTED angles to REAL physical angles
    predicted_angles: list[tuple[float, float]] = []

    # Reconstruct the math pipeline (must match inverse_kinematics.py)
    cx = cam_cfg["frame_width"] / 2.0
    cy = cam_cfg["frame_height"] / 2.0
    fov_h_rad = math.radians(cam_cfg["fov_h_deg"])
    focal = (cam_cfg["frame_width"] / 2.0) / math.tan(fov_h_rad / 2.0)

    # Servo direction flags (must match hardware_offsets.yaml)
    dir_cfg = config.get("servo_direction", {})
    pan_dir = dir_cfg.get("pan", 1)
    tilt_dir = dir_cfg.get("tilt", 1)

    # We don't know the distance to the wall during calibration,
    # so we assume a nominal depth of 150cm.
    z_cm = 150.0

    for px, py in pixel_points:
        # 1. Pixel -> Camera Space
        rel_px = px - cx
        rel_py = py - cy

        cam_x = (rel_px / focal) * z_cm
        cam_y = (rel_py / focal) * z_cm

        # 2. Camera -> Turret Offset
        turret_x = float(cam_x - config["turret_offset_cm"]["x"])
        turret_y = float(cam_y - config["turret_offset_cm"]["y"])
        turret_z = float(z_cm - config["turret_offset_cm"]["z"])

        # 3. Inverse Kinematics Prediction (with direction flags)
        theta_pan = math.atan2(turret_x, turret_z)
        horizontal_dist = math.sqrt(turret_x * turret_x + turret_z * turret_z)
        theta_tilt = math.atan2(turret_y, horizontal_dist)

        pred_pan = 90.0 + pan_dir * math.degrees(theta_pan)
        pred_tilt = 90.0 + tilt_dir * math.degrees(theta_tilt)
        predicted_angles.append((pred_pan, pred_tilt))

    src_pts = np.float32(predicted_angles)
    dst_pts = np.float32(angle_points)

    # cv2.getAffineTransform requires exactly 3 point pairs → 2×3 matrix
    affine_matrix = cv2.getAffineTransform(src_pts, dst_pts)

    logger.info("  Affine Matrix:")
    logger.info("    [%.6f, %.6f, %.6f]", affine_matrix[0][0], affine_matrix[0][1], affine_matrix[0][2])
    logger.info("    [%.6f, %.6f, %.6f]", affine_matrix[1][0], affine_matrix[1][1], affine_matrix[1][2])

    # ── Save to JSON ─────────────────────────────────────────────────
    output = {
        "description": "Affine correction matrix generated by pre_deployment_calibration.py",
        "calibrated": True,
        "affine_matrix": affine_matrix.tolist(),
        "calibration_points": {
            "pixel_coords": [list(p) for p in pixel_points],
            "predicted_angles": [list(p) for p in predicted_angles],
            "servo_angles": [list(a) for a in angle_points],
        },
    }

    output_path = CONFIG_DIR / "dynamic_matrix.json"
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    logger.info("  ✓ Saved to %s", output_path)

    # ── Cleanup ──────────────────────────────────────────────────────
    serial.send_command(90, 90, 0)  # Center turret, laser off
    time.sleep(0.5)
    serial.stop()
    cap.release()
    cv2.destroyAllWindows()

    logger.info("")
    logger.info("═══════════════════════════════════════════")
    logger.info("  CALIBRATION COMPLETE")
    logger.info("  The turret will now apply error correction")
    logger.info("  during live tracking.")
    logger.info("═══════════════════════════════════════════")


if __name__ == "__main__":
    run_calibration()
