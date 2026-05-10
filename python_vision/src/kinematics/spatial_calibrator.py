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
    affine_matrix_path : str | Path | None
        Path to ``dynamic_matrix.json``.
    """

    def __init__(
        self,
        frame_width: int = 640,
        frame_height: int = 480,
        focal_length_px: float = 554.26,
        offset_x_cm: float = 30.0,
        offset_y_cm: float = -10.0,
        offset_z_cm: float = 15.0,
        affine_matrix_path: str | Path | None = None,
    ) -> None:
        self._cx = frame_width / 2.0   # Principal point X
        self._cy = frame_height / 2.0  # Principal point Y
        self._focal = focal_length_px
        self._offset = np.array([offset_x_cm, offset_y_cm, offset_z_cm], dtype=np.float64)

        # Load the affine correction matrix (default = identity)
        self._affine = np.array([[1.0, 0.0, 0.0],
                                  [0.0, 1.0, 0.0]], dtype=np.float64)
        self._calibrated = False

        if affine_matrix_path is not None:
            self._load_affine(Path(affine_matrix_path))

        logger.info(
            "[SpatialCalibrator] Initialised — center=(%.0f, %.0f), focal=%.1f, "
            "offset=(%.1f, %.1f, %.1f), calibrated=%s",
            self._cx, self._cy, self._focal,
            *self._offset, self._calibrated,
        )

    def _load_affine(self, path: Path) -> None:
        """Load the affine correction matrix from JSON."""
        if not path.exists():
            logger.warning("[SpatialCalibrator] %s not found — using identity matrix", path)
            return

        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            self._calibrated = data.get("calibrated", False)
            matrix = data.get("affine_matrix")
            if matrix and len(matrix) == 2:
                self._affine = np.array(matrix, dtype=np.float64)
                if self._calibrated:
                    logger.info("[SpatialCalibrator] Loaded calibrated affine matrix from %s", path)
                else:
                    logger.info("[SpatialCalibrator] Loaded default (identity) affine matrix")
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.error("[SpatialCalibrator] Failed to parse %s: %s", path, exc)

    @property
    def is_calibrated(self) -> bool:
        return self._calibrated

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
        turret_x = cam_x - self._offset[0]
        turret_y = cam_y - self._offset[1]
        turret_z = cam_z - self._offset[2]

        # Step 3: Apply affine error correction
        # The affine matrix maps (turret_x, turret_y) → corrected (x, y)
        point = np.array([turret_x, turret_y, 1.0], dtype=np.float64)
        corrected = self._affine @ point  # shape (2,)
        final_x = float(corrected[0])
        final_y = float(corrected[1])

        logger.debug(
            "[SpatialCalibrator] px=(%.1f, %.1f) Z=%.1f → cam=(%.1f, %.1f, %.1f) "
            "→ turret=(%.1f, %.1f, %.1f)",
            pixel_x, pixel_y, depth_cm,
            cam_x, cam_y, cam_z,
            final_x, final_y, turret_z,
        )

        return SpatialCoordinate(x=final_x, y=final_y, z=turret_z)
