"""
inverse_kinematics.py — Trigonometric Servo Angle Prediction
============================================================
Given a 3D spatial coordinate (X_t, Y_t, Z_t) relative to the turret's
rotational center, this module computes the exact absolute servo angles
required to point the laser directly at the target.

The formulas:
    θ_pan  = arctan2(X_t, Z_t)
    θ_tilt = arctan2(Y_t, √(X_t² + Z_t²))

Servo mapping (90° = forward-facing mechanical center):
    servo_pan  = 90 + pan_direction × degrees(θ_pan)
    servo_tilt = 90 + tilt_direction × degrees(θ_tilt)

Both outputs are clamped to [0, 180] to protect the SG90 gears.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

logger = logging.getLogger("sentry.kinematics.ik")

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
    Uses standard atan2 for numerical stability.
    """

    def __init__(
        self,
        pan_direction: int = 1,
        tilt_direction: int = 1,
    ) -> None:
        self._pan_dir = pan_direction
        self._tilt_dir = tilt_direction

        logger.info(
            "[InverseKinematics] Initialised — center=%d, range=[%d, %d], "
            "pan_dir=%d, tilt_dir=%d",
            _SERVO_CENTER, _SERVO_MIN, _SERVO_MAX,
            self._pan_dir, self._tilt_dir,
        )

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
        if abs(z_t) < 1.0:
            logger.warning("[IK] Z_t ≈ 0 — target at turret, holding center")
            return ServoCommand(pan=_SERVO_CENTER, tilt=_SERVO_CENTER)

        # ── Pan (Yaw) — horizontal ──────────────────────────────────
        theta_pan = math.atan2(x_t, z_t)

        # ── Tilt (Pitch) — vertical ─────────────────────────────────
        horizontal_dist = math.sqrt(x_t * x_t + z_t * z_t)
        theta_tilt = math.atan2(y_t, horizontal_dist)

        # ── Radians → Servo degrees ─────────────────────────────────
        pan_deg = _SERVO_CENTER + self._pan_dir * math.degrees(theta_pan)
        tilt_deg = _SERVO_CENTER + self._tilt_dir * math.degrees(theta_tilt)

        # ── Clamp [0, 180] ──────────────────────────────────────────
        pan_clamped = max(_SERVO_MIN, min(_SERVO_MAX, int(round(pan_deg))))
        tilt_clamped = max(_SERVO_MIN, min(_SERVO_MAX, int(round(tilt_deg))))

        logger.debug(
            "[IK] (X=%.1f, Y=%.1f, Z=%.1f) → θ=(%.2f°, %.2f°) → servo=(%d, %d)",
            x_t, y_t, z_t,
            math.degrees(theta_pan), math.degrees(theta_tilt),
            pan_clamped, tilt_clamped,
        )

        return ServoCommand(pan=pan_clamped, tilt=tilt_clamped)
