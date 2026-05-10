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

import logging
import math
from dataclasses import dataclass

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

    def __init__(self) -> None:
        logger.info("[InverseKinematics] Initialised — center=%d°, range=[%d, %d]",
                     _SERVO_CENTER, _SERVO_MIN, _SERVO_MAX)

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
        # servo = 90 + (θ × 180/π)
        pan_deg = _SERVO_CENTER + math.degrees(theta_pan)
        tilt_deg = _SERVO_CENTER + math.degrees(theta_tilt)

        # ── Strict integer clamp [0, 180] ───────────────────────────
        pan_clamped = max(_SERVO_MIN, min(_SERVO_MAX, int(round(pan_deg))))
        tilt_clamped = max(_SERVO_MIN, min(_SERVO_MAX, int(round(tilt_deg))))

        logger.debug(
            "[IK] (X=%.1f, Y=%.1f, Z=%.1f) → θ_pan=%.2f° θ_tilt=%.2f° → servo=(%d, %d)",
            x_t, y_t, z_t,
            math.degrees(theta_pan), math.degrees(theta_tilt),
            pan_clamped, tilt_clamped,
        )

        return ServoCommand(pan=pan_clamped, tilt=tilt_clamped)
