"""
depth_estimator.py — Pseudo-Depth Z-Axis Estimation
====================================================
Standard webcams provide no native depth information.  To position the
target in 3-D space, this module exploits the pinhole camera model and
the physiologically constant human bi-acromial (shoulder-to-shoulder)
width.

The inverse relationship between the pixel width of the shoulders and
the physical distance yields:

    Z = (REAL_SHOULDER_WIDTH_CM × FOCAL_LENGTH_PX) / pixel_shoulder_width

Focal length in pixels is derived from the horizontal field-of-view:

    focal_px = (frame_width / 2) / tan(fov_h / 2)

Because the shoulder width remains constant regardless of the subject's
posture (unlike the volatile full-body bounding-box height), this method
is highly stable even when the subject crouches, bends, or raises arms.
"""

from __future__ import annotations

import logging
import math

logger = logging.getLogger("sentry.kinematics.depth")


class DepthEstimator:
    """
    Monocular pseudo-depth estimator based on shoulder pixel width.

    Parameters
    ----------
    shoulder_width_cm : float
        Average adult bi-acromial width in centimetres.
    focal_length_px : float
        Camera focal length in pixels.  If not provided, it is computed
        from ``fov_h_deg`` and ``frame_width``.
    fov_h_deg : float
        Horizontal field-of-view of the camera in degrees.
    frame_width : int
        Width of the captured frame in pixels.
    default_depth_cm : float
        Fallback depth (cm) when shoulders are not visible.
    """

    def __init__(
        self,
        shoulder_width_cm: float = 40.0,
        focal_length_px: float | None = None,
        fov_h_deg: float = 62.0,
        frame_width: int = 640,
        default_depth_cm: float = 150.0,
    ) -> None:
        self._shoulder_width_cm = shoulder_width_cm
        self._default_depth_cm = default_depth_cm

        if focal_length_px is not None:
            self._focal_px = focal_length_px
        else:
            # Derive from horizontal FOV:  f = (w/2) / tan(θ/2)
            half_fov_rad = math.radians(fov_h_deg / 2.0)
            self._focal_px = (frame_width / 2.0) / math.tan(half_fov_rad)

        logger.info(
            "[DepthEstimator] Initialised — shoulder=%.1f cm, focal=%.1f px, default_Z=%.1f cm",
            self._shoulder_width_cm,
            self._focal_px,
            self._default_depth_cm,
        )

    @property
    def focal_length_px(self) -> float:
        """Focal length in pixels (read-only)."""
        return self._focal_px

    def estimate(
        self,
        left_shoulder_px: tuple[float, float] | None,
        right_shoulder_px: tuple[float, float] | None,
    ) -> float:
        """
        Compute pseudo-depth Z in centimetres.

        Parameters
        ----------
        left_shoulder_px : tuple | None
            (x, y) pixel coordinate of the left shoulder keypoint.
        right_shoulder_px : tuple | None
            (x, y) pixel coordinate of the right shoulder keypoint.

        Returns
        -------
        float
            Estimated depth Z in centimetres.  Returns the default
            fallback if either shoulder is not visible.
        """
        if left_shoulder_px is None or right_shoulder_px is None:
            logger.debug(
                "[DepthEstimator] Shoulder(s) not visible — using default Z=%.1f cm",
                self._default_depth_cm,
            )
            return self._default_depth_cm

        # Euclidean pixel distance between the two shoulders
        dx = left_shoulder_px[0] - right_shoulder_px[0]
        dy = left_shoulder_px[1] - right_shoulder_px[1]
        pixel_width = math.sqrt(dx * dx + dy * dy)

        if pixel_width < 1.0:
            # Shoulders overlapping — unreliable, fall back
            logger.debug("[DepthEstimator] Pixel width < 1 — using default Z")
            return self._default_depth_cm

        # Pinhole camera model: Z = (W_real * f) / W_pixel
        z_cm = (self._shoulder_width_cm * self._focal_px) / pixel_width

        # Sanity clamp: prevent absurd values (too close or too far)
        z_cm = max(30.0, min(z_cm, 1000.0))

        logger.debug(
            "[DepthEstimator] shoulder_px=%.1f → Z=%.1f cm",
            pixel_width,
            z_cm,
        )
        return z_cm
