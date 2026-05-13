"""
depth_estimator.py — Hybrid Depth Estimation
==============================================
Estimates depth using two methods and picks the most reliable:

1. **Shoulder Width** (primary): Uses bi-acromial distance — stable
   across postures. Z = (W_real × f) / W_pixel

2. **Bounding Box Height** (fallback): Uses full YOLO bbox height with
   an assumed visible-body proportion. Less accurate but always available.
"""

from __future__ import annotations

import logging
import math

logger = logging.getLogger("sentry.kinematics.depth")

# Average visible body height (head-to-hip) in cm — used for bbox fallback
_VISIBLE_BODY_HEIGHT_CM = 85.0


class DepthEstimator:
    """
    Hybrid monocular depth estimator.

    Parameters
    ----------
    shoulder_width_cm : float
        Average adult bi-acromial width (cm).
    fov_h_deg : float
        Horizontal FOV of the camera (degrees).
    frame_width : int
        Width of the captured frame (pixels).
    default_depth_cm : float
        Fallback depth when no estimation is possible.
    """

    def __init__(
        self,
        shoulder_width_cm: float = 40.0,
        focal_length_px: float | None = None,
        fov_h_deg: float = 62.0,
        frame_width: int = 640,
        default_depth_cm: float = 200.0,
    ) -> None:
        self._shoulder_width_cm = shoulder_width_cm
        self._default_depth_cm = default_depth_cm

        if focal_length_px is not None:
            self._focal_px = focal_length_px
        else:
            half_fov_rad = math.radians(fov_h_deg / 2.0)
            self._focal_px = (frame_width / 2.0) / math.tan(half_fov_rad)

        # Last estimated depth (for HUD display)
        self.last_shoulder_px: float = 0.0
        self.last_method: str = "default"

        logger.info(
            "[DepthEstimator] shoulder=%.1f cm, focal=%.1f px, default=%.1f cm",
            self._shoulder_width_cm, self._focal_px, self._default_depth_cm,
        )

    @property
    def focal_length_px(self) -> float:
        return self._focal_px

    def estimate(
        self,
        left_shoulder_px: tuple[float, float] | None,
        right_shoulder_px: tuple[float, float] | None,
        bbox: tuple[float, float, float, float] | None = None,
    ) -> float:
        """
        Estimate depth using shoulders (primary) or bbox (fallback).

        Parameters
        ----------
        left_shoulder_px, right_shoulder_px : tuple | None
            Shoulder keypoint pixel coordinates.
        bbox : tuple | None
            (x1, y1, x2, y2) YOLO bounding box for bbox-height fallback.

        Returns
        -------
        float
            Estimated depth in centimetres.
        """
        # ── Method 1: Shoulder Width (most accurate) ─────────────────
        if left_shoulder_px is not None and right_shoulder_px is not None:
            dx = left_shoulder_px[0] - right_shoulder_px[0]
            dy = left_shoulder_px[1] - right_shoulder_px[1]
            pixel_width = math.sqrt(dx * dx + dy * dy)

            if pixel_width > 10.0:  # Need reasonable pixel span
                z_cm = (self._shoulder_width_cm * self._focal_px) / pixel_width
                z_cm = max(50.0, min(z_cm, 800.0))
                self.last_shoulder_px = pixel_width
                self.last_method = "shoulder"
                return z_cm

        # ── Method 2: Bounding Box Height (fallback) ─────────────────
        if bbox is not None:
            _, y1, _, y2 = bbox
            bbox_height = abs(y2 - y1)
            if bbox_height > 20.0:
                z_cm = (_VISIBLE_BODY_HEIGHT_CM * self._focal_px) / bbox_height
                z_cm = max(50.0, min(z_cm, 800.0))
                self.last_shoulder_px = 0.0
                self.last_method = "bbox"
                return z_cm

        # ── Fallback ─────────────────────────────────────────────────
        self.last_shoulder_px = 0.0
        self.last_method = "default"
        return self._default_depth_cm
