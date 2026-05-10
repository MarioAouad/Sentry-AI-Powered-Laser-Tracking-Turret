"""
signal_filter.py — Two-Stage Noise Rejection Pipeline
=====================================================
Raw AI keypoint coordinates naturally jitter pixel-by-pixel between
frames.  Before these coordinates can drive physical servo motors, they
must pass through a two-stage filter to eliminate noise:

Stage 1 — Rolling Median Filter (5-frame window)
    Aggressively rejects single-frame AI bounding-box glitches by taking
    the statistical median of the last N raw values.  Unlike a mean, the
    median is completely immune to outliers.

Stage 2 — Exponential Moving Average (EMA) Low-Pass Filter
    Smooths the median-filtered output to produce a buttery-smooth
    trajectory suitable for servo actuation:

        S_t = α · Y_t + (1 − α) · S_{t-1}

    where S_t is the smoothed coordinate, Y_t is the current median
    value, and α ∈ (0, 1] is the smoothing factor.
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger("sentry.kinematics.filter")


@dataclass
class FilteredPoint:
    """Output of the two-stage filter."""

    x: float
    y: float


class SignalFilter:
    """
    Two-stage signal conditioner: Rolling Median → EMA.

    Parameters
    ----------
    alpha : float
        EMA smoothing factor (0 < α ≤ 1).  Lower = more smoothing.
    median_window : int
        Size of the rolling median buffer.  Must be odd.
    """

    def __init__(self, alpha: float = 0.35, median_window: int = 5) -> None:
        if not (0.0 < alpha <= 1.0):
            raise ValueError(f"EMA alpha must be in (0, 1], got {alpha}")
        if median_window < 1:
            raise ValueError(f"median_window must be ≥ 1, got {median_window}")

        self._alpha = alpha
        self._median_window = median_window

        # Rolling buffers for the median filter (separate X and Y)
        self._x_buffer: deque[float] = deque(maxlen=median_window)
        self._y_buffer: deque[float] = deque(maxlen=median_window)

        # EMA state (None until the first value arrives)
        self._ema_x: float | None = None
        self._ema_y: float | None = None

        logger.info(
            "[SignalFilter] Initialised — α=%.3f, median_window=%d",
            alpha,
            median_window,
        )

    def update(self, raw_x: float, raw_y: float) -> FilteredPoint:
        """
        Push a raw (X, Y) coordinate through the filter pipeline.

        Returns the smoothed ``FilteredPoint``.
        """
        # ── Stage 1: Rolling Median ──────────────────────────────────
        self._x_buffer.append(raw_x)
        self._y_buffer.append(raw_y)

        median_x = float(np.median(list(self._x_buffer)))
        median_y = float(np.median(list(self._y_buffer)))

        # ── Stage 2: Exponential Moving Average ──────────────────────
        if self._ema_x is None:
            # First sample — initialise directly (no history to blend)
            self._ema_x = median_x
            self._ema_y = median_y
        else:
            self._ema_x = self._alpha * median_x + (1.0 - self._alpha) * self._ema_x
            self._ema_y = self._alpha * median_y + (1.0 - self._alpha) * self._ema_y

        logger.debug(
            "[SignalFilter] raw=(%.1f, %.1f) → median=(%.1f, %.1f) → ema=(%.1f, %.1f)",
            raw_x, raw_y, median_x, median_y, self._ema_x, self._ema_y,
        )

        return FilteredPoint(x=self._ema_x, y=self._ema_y)

    def reset(self) -> None:
        """Flush all filter state (called on track loss)."""
        self._x_buffer.clear()
        self._y_buffer.clear()
        self._ema_x = None
        self._ema_y = None
        logger.debug("[SignalFilter] State reset")
