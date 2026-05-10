"""
cascade_detector.py — Classical HOG+SVM Pedestrian Wake-Up Gate
===============================================================
Level 1 of the two-tier detection cascade.  Scans raw frames using
OpenCV's built-in Histogram of Oriented Gradients (HOG) paired with a
pre-trained Support Vector Machine (SVM) pedestrian classifier.

This module is intentionally lightweight: it runs entirely on the CPU
and avoids invoking the heavy YOLO neural network until a human shape
is confidently detected for several consecutive frames.

State Behaviour:
    - When NO person is detected → returns False (YOLO stays asleep).
    - When a person IS detected for `min_consecutive` frames in a row →
      returns True, signalling the orchestrator to wake up YOLO.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import cv2
import numpy as np

logger = logging.getLogger("sentry.vision.cascade")


# ── Result Container ─────────────────────────────────────────────────
@dataclass
class CascadeResult:
    """Immutable snapshot returned by each detection call."""

    detected: bool = False
    bbox: tuple[int, int, int, int] | None = None  # (x, y, w, h) of the largest hit
    consecutive_count: int = 0


# ── Detector ─────────────────────────────────────────────────────────
class CascadeDetector:
    """
    HOG + SVM pedestrian detector acting as a low-power activation gate.

    Parameters
    ----------
    min_consecutive : int
        How many frames in a row must contain a person before the gate
        opens (prevents single-frame false triggers).
    hit_threshold : float
        SVM decision-function threshold passed to ``detectMultiScale``.
        Lower → more sensitive; higher → fewer false positives.
    """

    def __init__(
        self,
        min_consecutive: int = 3,
        hit_threshold: float = 0.3,
    ) -> None:
        # Initialise the HOG descriptor with OpenCV's default people detector
        self._hog = cv2.HOGDescriptor()
        self._hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

        self._min_consecutive = max(1, min_consecutive)
        self._hit_threshold = hit_threshold
        self._consecutive: int = 0

        logger.info(
            "[CascadeDetector] Initialised — min_consecutive=%d, hit_threshold=%.2f",
            self._min_consecutive,
            self._hit_threshold,
        )

    # ── Public API ───────────────────────────────────────────────────
    def detect(self, frame: np.ndarray) -> CascadeResult:
        """
        Run HOG+SVM on a single BGR frame.

        Returns a ``CascadeResult`` whose ``.detected`` flag is True only
        after ``min_consecutive`` successive frames with at least one
        pedestrian detection.
        """
        # Resize for consistent detection speed (HOG is scale-sensitive)
        small = cv2.resize(frame, (640, 480))

        # Run the multi-scale sliding-window detector
        rects, weights = self._hog.detectMultiScale(
            small,
            winStride=(8, 8),
            padding=(4, 4),
            scale=1.05,
            hitThreshold=self._hit_threshold,
        )

        if len(rects) > 0:
            self._consecutive += 1

            # Pick the LARGEST bounding box (most likely the real person)
            areas = [w * h for (_, _, w, h) in rects]
            best_idx = int(np.argmax(areas))
            x, y, w, h = rects[best_idx]

            # Scale bbox back to original frame coordinates
            scale_x = frame.shape[1] / 640
            scale_y = frame.shape[0] / 480
            bbox = (
                int(x * scale_x),
                int(y * scale_y),
                int(w * scale_x),
                int(h * scale_y),
            )

            gate_open = self._consecutive >= self._min_consecutive
            if gate_open:
                logger.info(
                    "[CascadeDetector] GATE OPEN — person confirmed for %d consecutive frames",
                    self._consecutive,
                )

            return CascadeResult(
                detected=gate_open,
                bbox=bbox,
                consecutive_count=self._consecutive,
            )
        else:
            # No detection this frame — reset the counter
            if self._consecutive > 0:
                logger.debug(
                    "[CascadeDetector] Detection streak broken after %d frames",
                    self._consecutive,
                )
            self._consecutive = 0
            return CascadeResult(detected=False, bbox=None, consecutive_count=0)

    def reset(self) -> None:
        """Reset the consecutive counter (called when YOLO takes over)."""
        self._consecutive = 0
        logger.debug("[CascadeDetector] Consecutive counter reset")
