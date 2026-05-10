"""
inverse_kinematics.py — Trigonometric Servo Angle Prediction
============================================================
Given a calibrated 3D spatial coordinate (X_t, Y_t, Z_t) relative to
the turret's rotational center, this module computes the exact absolute
servo angles required to point the laser directly at the target.

The formulas (from the project specification):

    θ_pan  = arctan(X_t / Z_t)
    θ_tilt = arctan(Y_t / √(X_t² + Z_t²))

Radians are translated to hardware servo integers assuming the
forward-facing mechanical center is at the 90° position:

    servo_pan  = 90 + (θ_pan  × 180 / π)
    servo_tilt = 90 + (θ_tilt × 180 / π)

Both outputs are strictly clamped to the integer range [0, 180] to
prevent the SG90 plastic gears from stripping.
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

logger = logging.getLogger("sentry.kinematics.ik")

# Hardware limits matching Config.h on the ESP32
_SERVO_MIN = 0
_SERVO_MAX = 180
_SERVO_CENTER = 90


@dataclass
class ServoCommand:
    """Final integer servo angles ready for serial transmission."""

    pan: int    # [0, 180] — horizontal yaw
    tilt: int   # [0, 180] — vertical pitch


class InverseKinematics:
    """
    Converts 3D turret-relative coordinates into absolute servo angles.

    The computations use the standard ``atan2`` for numerical stability
    (handles the case where Z_t ≈ 0 gracefully).
    """

    def __init__(
        self,
        affine_matrix_path: str | Path | None = None,
        pan_direction: int = 1,
        tilt_direction: int = 1,
    ) -> None:
        self._pan_dir = pan_direction
        self._tilt_dir = tilt_direction
        self._affine = np.array([[1.0, 0.0, 0.0],
                                  [0.0, 1.0, 0.0]], dtype=np.float64)
        self._calibrated = False

        if affine_matrix_path is not None:
            self._load_affine(Path(affine_matrix_path))

        logger.info(
            "[InverseKinematics] Initialised — center=%d, range=[%d, %d], "
            "pan_dir=%d, tilt_dir=%d, calibrated=%s",
             _SERVO_CENTER, _SERVO_MIN, _SERVO_MAX,
             self._pan_dir, self._tilt_dir, self._calibrated
        )

    def _load_affine(self, path: Path) -> None:
        """Load the affine correction matrix from JSON."""
        if not path.exists():
            logger.warning("[InverseKinematics] %s not found — using identity matrix", path)
            return

        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            self._calibrated = data.get("calibrated", False)
            matrix = data.get("affine_matrix")
            if matrix and len(matrix) == 2:
                self._affine = np.array(matrix, dtype=np.float64)
                if self._calibrated:
                    logger.info("[InverseKinematics] Loaded calibrated affine matrix from %s", path)
                else:
                    logger.info("[InverseKinematics] Loaded default (identity) affine matrix")
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.error("[InverseKinematics] Failed to parse %s: %s", path, exc)

    def compute(self, x_t: float, y_t: float, z_t: float) -> ServoCommand:
        """
        Compute servo angles from a 3D spatial coordinate.

        Parameters
        ----------
        x_t : float
            Horizontal position relative to turret (cm).  Positive = right.
        y_t : float
            Vertical position relative to turret (cm).  Positive = down.
        z_t : float
            Depth from turret (cm).  Positive = forward.

        Returns
        -------
        ServoCommand
            Clamped integer pan and tilt angles.
        """
        # Guard against degenerate depth
        if abs(z_t) < 0.01:
            logger.warning("[IK] Z_t ≈ 0 — target directly at turret, holding position")
            return ServoCommand(pan=_SERVO_CENTER, tilt=_SERVO_CENTER)

        # ── Pan (Yaw) — horizontal ──────────────────────────────────
        # θ_pan = arctan(X_t / Z_t)
        theta_pan = math.atan2(x_t, z_t)

        # ── Tilt (Pitch) — vertical ─────────────────────────────────
        # θ_tilt = arctan(Y_t / √(X_t² + Z_t²))
        horizontal_dist = math.sqrt(x_t * x_t + z_t * z_t)
        theta_tilt = math.atan2(y_t, horizontal_dist)

        # ── Radians → Servo degrees ─────────────────────────────────
        # servo = 90 + direction × (θ × 180/π)
        # direction = -1 inverts the servo for reversed mounting
        pan_deg = _SERVO_CENTER + self._pan_dir * math.degrees(theta_pan)
        tilt_deg = _SERVO_CENTER + self._tilt_dir * math.degrees(theta_tilt)

        # ── Affine Error Correction ─────────────────────────────────
        # Only apply the correction if a real calibration was performed.
        # Without calibration, pass through the raw trig angles directly.
        if self._calibrated:
            point = np.array([pan_deg, tilt_deg, 1.0], dtype=np.float64)
            corrected = self._affine @ point
            final_pan = float(corrected[0])
            final_tilt = float(corrected[1])
        else:
            final_pan = pan_deg
            final_tilt = tilt_deg

        # ── Strict integer clamp [0, 180] ───────────────────────────
        pan_clamped = max(_SERVO_MIN, min(_SERVO_MAX, int(round(final_pan))))
        tilt_clamped = max(_SERVO_MIN, min(_SERVO_MAX, int(round(final_tilt))))

        logger.debug(
            "[IK] (X=%.1f, Y=%.1f, Z=%.1f) → pred_θ=(%.2f°, %.2f°) → corrected=(%.1f°, %.1f°) → servo=(%d, %d)",
            x_t, y_t, z_t,
            math.degrees(theta_pan), math.degrees(theta_tilt),
            final_pan, final_tilt,
            pan_clamped, tilt_clamped,
        )

        return ServoCommand(pan=pan_clamped, tilt=tilt_clamped)
