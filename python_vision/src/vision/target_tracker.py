"""
target_tracker.py — YOLO11m-Pose + ByteTrack Deep Learning Tracker
===================================================================
Level 2 of the two-tier detection cascade.  This module is activated
ONLY after the HOG+SVM gate confirms a human presence.  It performs:

1.  Full skeletal pose estimation using YOLO11m-Pose (17 COCO keypoints).
2.  Frame-to-frame identity persistence via the ByteTrack tracker.
3.  Target keypoint extraction based on the user-selected body part
    (head / chest) received from the frontend UI.

COCO 17-Keypoint Index Map:
    0  Nose              9  Left Wrist
    1  Left Eye         10  Right Wrist
    2  Right Eye        11  Left Hip
    3  Left Ear         12  Right Hip
    4  Right Ear        13  Left Knee
    5  Left Shoulder    14  Right Knee
    6  Right Shoulder   15  Left Ankle
    7  Left Elbow       16  Right Ankle
    8  Right Elbow
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import numpy as np

logger = logging.getLogger("sentry.vision.tracker")

# ── Target modes mapped to keypoint indices ──────────────────────────
TargetMode = Literal["head", "chest"]

# Which keypoint indices to average for each targeting mode
_TARGET_KEYPOINTS: dict[TargetMode, list[int]] = {
    "head": [0],          # Nose
    "chest": [5, 6],      # Midpoint of left+right shoulders
}

# Shoulder indices for depth estimation (always needed)
_LEFT_SHOULDER = 5
_RIGHT_SHOULDER = 6


# ── Result Container ─────────────────────────────────────────────────
@dataclass
class TrackerResult:
    """Immutable snapshot of the tracking output for one frame."""

    detected: bool = False
    track_id: int = -1
    confidence: float = 0.0

    # Raw target pixel coordinate (the selected body part)
    target_px: tuple[float, float] = (0.0, 0.0)

    # Shoulder keypoints for depth estimation (pixel coords)
    left_shoulder_px: tuple[float, float] | None = None
    right_shoulder_px: tuple[float, float] | None = None

    # All 17 keypoints as (x, y, confidence) for optional visualisation
    all_keypoints: np.ndarray = field(default_factory=lambda: np.zeros((17, 3)))

    # Bounding box [x1, y1, x2, y2]
    bbox: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)


# ── Tracker ──────────────────────────────────────────────────────────
class TargetTracker:
    """
    YOLO11m-Pose + ByteTrack skeletal tracker.

    Parameters
    ----------
    model_path : str | Path
        Absolute path to the ``yolo11m-pose.pt`` weights file.
    confidence : float
        Minimum detection confidence for YOLO.
    device : str
        Compute device — ``"cuda:0"`` for GPU, ``"cpu"`` for fallback.
    """

    def __init__(
        self,
        model_path: str | Path,
        confidence: float = 0.45,
        device: str = "cuda:0",
    ) -> None:
        from ultralytics import YOLO

        self._model_path = Path(model_path)
        if not self._model_path.exists():
            raise FileNotFoundError(
                f"YOLO model not found at {self._model_path}. "
                "Place yolo11m-pose.pt in python_vision/models/"
            )

        self._model = YOLO(str(self._model_path))
        self._confidence = confidence
        self._device = device
        self._target_mode: TargetMode = "chest"

        logger.info(
            "[TargetTracker] Loaded %s on device=%s, conf=%.2f",
            self._model_path.name,
            self._device,
            self._confidence,
        )

    # ── Configuration ────────────────────────────────────────────────
    def set_target_mode(self, mode: TargetMode) -> None:
        """Change which body part the turret targets."""
        if mode not in _TARGET_KEYPOINTS:
            logger.warning("[TargetTracker] Invalid target mode '%s', ignoring", mode)
            return
        self._target_mode = mode
        logger.info("[TargetTracker] Target mode changed → %s", mode)

    @property
    def target_mode(self) -> TargetMode:
        return self._target_mode

    # ── Core Tracking ────────────────────────────────────────────────
    def track(self, frame: np.ndarray) -> TrackerResult:
        """
        Run YOLO11m-Pose + ByteTrack on a single BGR frame.

        Returns a ``TrackerResult`` with the selected target keypoint,
        shoulder positions for depth estimation, and track identity.
        """
        results = self._model.track(
            source=frame,
            tracker="bytetrack.yaml",
            conf=self._confidence,
            device=self._device,
            persist=True,
            verbose=False,
            classes=[0],  # Filter for "person" class only (COCO class 0)
        )

        if not results or len(results) == 0:
            return TrackerResult(detected=False)

        result = results[0]

        # -- Guard: no detections or no tracking IDs assigned --
        if result.boxes is None or result.boxes.id is None or len(result.boxes) == 0:
            return TrackerResult(detected=False)

        # -- Guard: no keypoints available --
        if result.keypoints is None or result.keypoints.xy is None:
            return TrackerResult(detected=False)

        # Pick the highest-confidence person track
        confs = result.boxes.conf.cpu().numpy()
        best_idx = int(np.argmax(confs))

        track_id = int(result.boxes.id.cpu().numpy()[best_idx])
        confidence = float(confs[best_idx])
        bbox_xyxy = result.boxes.xyxy.cpu().numpy()[best_idx]

        # Extract all 17 keypoints for this person: shape (17, 3) — x, y, conf
        kps_xy = result.keypoints.xy.cpu().numpy()[best_idx]        # (17, 2)
        kps_conf = result.keypoints.conf.cpu().numpy()[best_idx]    # (17,)
        all_kps = np.column_stack([kps_xy, kps_conf])               # (17, 3)

        # -- Compute target pixel coordinate --
        target_indices = _TARGET_KEYPOINTS[self._target_mode]
        target_coords = []
        for idx in target_indices:
            kp_x, kp_y = kps_xy[idx]
            kp_c = kps_conf[idx]
            if kp_c > 0.3:  # Only use visible keypoints
                target_coords.append((kp_x, kp_y))

        if not target_coords:
            # Fallback: use bounding box center if keypoints are occluded
            cx = (bbox_xyxy[0] + bbox_xyxy[2]) / 2
            cy = (bbox_xyxy[1] + bbox_xyxy[3]) / 2
            target_px = (float(cx), float(cy))
            logger.debug("[TargetTracker] Keypoints occluded, using bbox center")
        else:
            # Average the selected keypoints
            avg_x = sum(c[0] for c in target_coords) / len(target_coords)
            avg_y = sum(c[1] for c in target_coords) / len(target_coords)
            target_px = (float(avg_x), float(avg_y))

        # -- Extract shoulder keypoints for depth estimation --
        left_sh: tuple[float, float] | None = None
        right_sh: tuple[float, float] | None = None

        if kps_conf[_LEFT_SHOULDER] > 0.3:
            left_sh = (float(kps_xy[_LEFT_SHOULDER][0]), float(kps_xy[_LEFT_SHOULDER][1]))
        if kps_conf[_RIGHT_SHOULDER] > 0.3:
            right_sh = (float(kps_xy[_RIGHT_SHOULDER][0]), float(kps_xy[_RIGHT_SHOULDER][1]))

        logger.debug(
            "[TargetTracker] Track #%d  target=(%6.1f, %6.1f)  mode=%s  conf=%.2f",
            track_id, target_px[0], target_px[1], self._target_mode, confidence,
        )

        return TrackerResult(
            detected=True,
            track_id=track_id,
            confidence=confidence,
            target_px=target_px,
            left_shoulder_px=left_sh,
            right_shoulder_px=right_sh,
            all_keypoints=all_kps,
            bbox=(
                float(bbox_xyxy[0]), float(bbox_xyxy[1]),
                float(bbox_xyxy[2]), float(bbox_xyxy[3]),
            ),
        )
