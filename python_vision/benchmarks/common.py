from __future__ import annotations

import csv
import json
import math
import statistics
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence


COCO_KEYPOINTS = 17
COCO_OKS_SIGMAS = (
    0.26,
    0.25,
    0.25,
    0.35,
    0.35,
    0.79,
    0.79,
    0.72,
    0.72,
    0.62,
    0.62,
    1.07,
    1.07,
    0.87,
    0.87,
    0.89,
    0.89,
)

YOLO_POSE_MODELS = {
    "yolov8n": "yolov8n-pose.pt",
    "yolov8s": "yolov8s-pose.pt",
    "yolov8m": "yolov8m-pose.pt",
    "yolo11n": "yolo11n-pose.pt",
    "yolo11s": "yolo11s-pose.pt",
    "yolo11m": "yolo11m-pose.pt",
}


def resolve_yolo_model_path(yolo_variant: str, model_path: str | None) -> str:
    if model_path:
        return model_path
    try:
        return YOLO_POSE_MODELS[yolo_variant]
    except KeyError as exc:
        known = ", ".join(sorted(YOLO_POSE_MODELS))
        raise ValueError(f"Unknown YOLO variant '{yolo_variant}'. Expected one of: {known}") from exc


@dataclass
class LatencyStats:
    frames: int
    mean_ms: float
    median_ms: float
    p95_ms: float
    fps: float
    mean_confidence: float | None = None
    min_confidence: float | None = None


def percentile(values: Sequence[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered) - 1) * pct
    low = math.floor(index)
    high = math.ceil(index)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (index - low)


def summarize_latency(latencies_ms: Sequence[float], confidences: Sequence[float] | None = None) -> LatencyStats:
    if not latencies_ms:
        return LatencyStats(frames=0, mean_ms=0.0, median_ms=0.0, p95_ms=0.0, fps=0.0)
    total_seconds = sum(latencies_ms) / 1000.0
    confidence_values = [float(c) for c in confidences or [] if c is not None]
    return LatencyStats(
        frames=len(latencies_ms),
        mean_ms=statistics.fmean(latencies_ms),
        median_ms=statistics.median(latencies_ms),
        p95_ms=percentile(latencies_ms, 0.95),
        fps=(len(latencies_ms) / total_seconds) if total_seconds > 0 else 0.0,
        mean_confidence=statistics.fmean(confidence_values) if confidence_values else None,
        min_confidence=min(confidence_values) if confidence_values else None,
    )


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: Iterable[dict]) -> None:
    rows = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def stats_to_dict(stats: LatencyStats) -> dict:
    return asdict(stats)


def iou_xywh(a: Sequence[float], b: Sequence[float]) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ax2, ay2 = ax + aw, ay + ah
    bx2, by2 = bx + bw, by + bh
    inter_w = max(0.0, min(ax2, bx2) - max(ax, bx))
    inter_h = max(0.0, min(ay2, by2) - max(ay, by))
    inter = inter_w * inter_h
    union = aw * ah + bw * bh - inter
    return inter / union if union > 0 else 0.0


def coco_oks(
    predicted: Sequence[Sequence[float]],
    target: Sequence[Sequence[float]],
    object_area: float,
) -> float:
    """Compute COCO-style object keypoint similarity for one person."""
    if object_area <= 0:
        return 0.0
    scores: list[float] = []
    for idx in range(min(len(predicted), len(target), COCO_KEYPOINTS)):
        tx, ty, visible = target[idx][:3]
        if visible <= 0:
            continue
        px, py = predicted[idx][:2]
        dx = px - tx
        dy = py - ty
        sigma = COCO_OKS_SIGMAS[idx] / 10.0
        denominator = 2 * (sigma**2) * object_area
        scores.append(math.exp(-((dx * dx + dy * dy) / denominator)))
    return statistics.fmean(scores) if scores else 0.0


class Timer:
    def __enter__(self) -> "Timer":
        self.started = time.perf_counter()
        self.elapsed_ms = 0.0
        return self

    def __exit__(self, *_: object) -> None:
        self.elapsed_ms = (time.perf_counter() - self.started) * 1000.0
