"""
spatial_calibrator.py — 2D Pixel → 3D Turret-Relative Coordinates
==================================================================
Converts the filtered 2D pixel target and the pseudo-depth Z into a
true 3D spatial coordinate (X_t, Y_t, Z_t) defined in the turret's
own reference frame.

Coordinate System (World Frame — origin at camera lens):
    X = rightward (from camera's perspective)
    Y = downward
    Z = forward (into the scene)

The transformation:
    1. Pixel → Camera-Space via pinhole model
    2. Camera-Space → Turret-Space via offset subtraction

Reverse projection (for virtual laser overlay):
    Given servo angles, compute where the laser would appear in the
    camera frame. This enables visual debugging of the math.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger("sentry.kinematics.spatial")

# Minimum allowed turret-to-target depth (cm).
# Prevents math explosion when the target is very close to the turret.
_MIN_TURRET_DEPTH_CM = 20.0


@dataclass
class SpatialCoordinate:
    """3D coordinate relative to the turret's rotational center (cm)."""
    x: float  # Positive = rightward
    y: float  # Positive = downward
    z: float  # Positive = forward (away from turret, toward scene)


class SpatialCalibrator:
    """
    Translates 2D pixel targets into 3D turret-relative coordinates,
    and reverse-projects servo angles back to camera pixels.

    Parameters
    ----------
    frame_width, frame_height : int
        Camera resolution in pixels.
    focal_length_px : float
        Camera focal length in pixels (from DepthEstimator).
    offset_x_cm, offset_y_cm, offset_z_cm : float
        Physical displacement vector from camera to turret (cm).
    """

    def __init__(
        self,
        frame_width: int = 640,
        frame_height: int = 480,
        focal_length_px: float = 554.26,
        offset_x_cm: float = 0.0,
        offset_y_cm: float = 27.0,
        offset_z_cm: float = 47.0,
    ) -> None:
        self._cx = frame_width / 2.0
        self._cy = frame_height / 2.0
        self._focal = focal_length_px
        self._offset_x = offset_x_cm
        self._offset_y = offset_y_cm
        self._offset_z = offset_z_cm

        logger.info(
            "[SpatialCalibrator] center=(%.0f, %.0f), focal=%.1f, "
            "offset=(%.1f, %.1f, %.1f)",
            self._cx, self._cy, self._focal,
            self._offset_x, self._offset_y, self._offset_z,
        )

    def transform(
        self, pixel_x: float, pixel_y: float, depth_cm: float
    ) -> SpatialCoordinate:
        """
        Convert a 2D pixel coordinate + depth into a 3D turret-relative
        spatial coordinate.

        Parameters
        ----------
        pixel_x, pixel_y : float
            Target position in the camera frame (pixels).
        depth_cm : float
            Estimated depth from camera to target (cm).

        Returns
        -------
        SpatialCoordinate
            (X_t, Y_t, Z_t) in centimetres relative to the turret origin.
        """
        # Step 1: Pixel → Camera-Space (pinhole model)
        rel_px = pixel_x - self._cx
        rel_py = pixel_y - self._cy

        cam_x = (rel_px / self._focal) * depth_cm
        cam_y = (rel_py / self._focal) * depth_cm

        # Step 2: Camera-Space → Turret-Space (offset subtraction)
        turret_x = cam_x - self._offset_x
        turret_y = cam_y - self._offset_y
        turret_z = depth_cm - self._offset_z

        # Clamp turret_z to prevent math explosion at close range
        if turret_z < _MIN_TURRET_DEPTH_CM:
            logger.warning(
                "[SpatialCalibrator] turret_z=%.1f < %.1f — clamping "
                "(target too close to turret)",
                turret_z, _MIN_TURRET_DEPTH_CM,
            )
            turret_z = _MIN_TURRET_DEPTH_CM

        logger.debug(
            "[Spatial] px=(%.0f,%.0f) Z=%.0f → cam=(%.1f,%.1f) "
            "→ turret=(%.1f,%.1f,%.1f)",
            pixel_x, pixel_y, depth_cm,
            cam_x, cam_y, turret_x, turret_y, turret_z,
        )

        return SpatialCoordinate(x=turret_x, y=turret_y, z=turret_z)

    def reverse_project(
        self,
        servo_pan: int,
        servo_tilt: int,
        pan_dir: int,
        tilt_dir: int,
        depth_cm: float,
    ) -> tuple[int, int]:
        """
        Reverse-project commanded servo angles back to camera pixel
        coordinates. Used to draw the virtual laser overlay.

        This is the mathematical inverse of transform() + IK.compute().

        Parameters
        ----------
        servo_pan, servo_tilt : int
            Commanded servo angles [0, 180].
        pan_dir, tilt_dir : int
            Servo direction multipliers (±1).
        depth_cm : float
            Estimated depth from camera to target (cm).

        Returns
        -------
        tuple[int, int]
            (pixel_x, pixel_y) where the laser should appear on camera.
        """
        # Undo IK: servo → aiming angles in radians
        theta_pan = math.radians((servo_pan - 90) / pan_dir)
        theta_tilt = math.radians((servo_tilt - 90) / tilt_dir)

        # Reconstruct turret-relative target position
        turret_z = max(depth_cm - self._offset_z, _MIN_TURRET_DEPTH_CM)
        turret_x = turret_z * math.tan(theta_pan)
        h_dist = math.sqrt(turret_x ** 2 + turret_z ** 2)
        turret_y = h_dist * math.tan(theta_tilt)

        # Turret-space → Camera world-space
        cam_x = turret_x + self._offset_x
        cam_y = turret_y + self._offset_y
        cam_z = turret_z + self._offset_z  # ≈ depth_cm

        # Camera world-space → pixel (pinhole inverse)
        if cam_z < 1.0:
            return (int(self._cx), int(self._cy))

        pixel_x = (cam_x / cam_z) * self._focal + self._cx
        pixel_y = (cam_y / cam_z) * self._focal + self._cy

        return (int(round(pixel_x)), int(round(pixel_y)))
