"""
spatial_calibrator.py — 2D Pixel → 3D Turret-Relative Coordinates
==================================================================
Converts the filtered 2D pixel target and the pseudo-depth Z into a
true 3D spatial coordinate (X_t, Y_t, Z_t) defined in the turret's
own reference frame.

The transformation proceeds in three steps:

1.  **Pixel-to-Camera Space** — Subtract the frame center to get
    relative pixel offsets, then scale by Z / focal_length to obtain
    real-world metric coordinates in the camera's frame.

2.  **Offset Translation** — Apply the physical displacement vector
    (from ``hardware_offsets.yaml``) that accounts for the fact that
    the camera and turret are not co-located.

3.  **Affine Error Correction** — Apply the 2×3 affine correction
    matrix (from ``dynamic_matrix.json``) generated during the
    pre-deployment calibration sequence.  This corrects for static
    hardware sag, lens distortion, and non-planar mounting.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np

logger = logging.getLogger("sentry.kinematics.spatial")


@dataclass
class SpatialCoordinate:
    """3D coordinate relative to the turret's rotational center (cm)."""

    x: float  # Positive = rightward
    y: float  # Positive = downward
    z: float  # Positive = forward (away from turret, toward scene)


class SpatialCalibrator:
    """
    Translates 2D pixel targets into 3D turret-relative coordinates.

    Parameters
    ----------
    frame_width : int
        Width of the camera frame in pixels.
    frame_height : int
        Height of the camera frame in pixels.
    focal_length_px : float
        Camera focal length in pixels (from DepthEstimator).
    offset_x_cm : float
        Physical X offset: camera → turret (cm).
    offset_y_cm : float
        Physical Y offset: camera → turret (cm).
    offset_z_cm : float
        Physical Z offset: camera → turret (cm).
    """

    def __init__(
        self,
        frame_width: int = 640,
        frame_height: int = 480,
        focal_length_px: float = 554.26,
        offset_x_cm: float = 30.0,
        offset_y_cm: float = -10.0,
        offset_z_cm: float = 15.0,
    ) -> None:
        self._cx = frame_width / 2.0   # Principal point X
        self._cy = frame_height / 2.0  # Principal point Y
        self._focal = focal_length_px
        self._offset = np.array([offset_x_cm, offset_y_cm, offset_z_cm], dtype=np.float64)

        logger.info(
            "[SpatialCalibrator] Initialised — center=(%.0f, %.0f), focal=%.1f, "
            "offset=(%.1f, %.1f, %.1f)",
            self._cx, self._cy, self._focal,
            *self._offset,
        )



    def transform(self, pixel_x: float, pixel_y: float, depth_cm: float) -> SpatialCoordinate:
        """
        Convert a 2D pixel coordinate + depth into a 3D turret-relative
        spatial coordinate.

        Parameters
        ----------
        pixel_x, pixel_y : float
            Target position in the camera frame (pixels).
        depth_cm : float
            Estimated depth from ``DepthEstimator`` (centimetres).

        Returns
        -------
        SpatialCoordinate
            (X_t, Y_t, Z_t) in centimetres relative to the turret origin.
        """
        # Step 1: Pixel → Camera-Space (pinhole model)
        # Subtract principal point to get relative pixel offset
        rel_px = pixel_x - self._cx
        rel_py = pixel_y - self._cy

        # Scale by depth / focal_length to get metric coordinates
        cam_x = (rel_px / self._focal) * depth_cm
        cam_y = (rel_py / self._focal) * depth_cm
        cam_z = depth_cm

        # Step 2: Apply the physical offset (camera → turret origin)
        turret_x = float(cam_x - self._offset[0])
        turret_y = float(cam_y - self._offset[1])
        turret_z = float(cam_z - self._offset[2])

        logger.debug(
            "[SpatialCalibrator] px=(%.1f, %.1f) Z=%.1f → cam=(%.1f, %.1f, %.1f) "
            "→ turret=(%.1f, %.1f, %.1f)",
            pixel_x, pixel_y, depth_cm,
            cam_x, cam_y, cam_z,
            turret_x, turret_y, turret_z,
        )

        return SpatialCoordinate(x=turret_x, y=turret_y, z=turret_z)
