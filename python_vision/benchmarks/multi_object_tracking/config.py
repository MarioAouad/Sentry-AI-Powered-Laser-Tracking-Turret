from __future__ import annotations

import os
from pathlib import Path


# Edit these values during analysis instead of changing benchmark_tracking_ablation.py.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = Path(SCRIPT_DIR).parent.parent

IMAGES_DIR = PROJECT_ROOT / "benchmarks" / "custom_datasets" / "images"
LABELS_DIR = PROJECT_ROOT / "benchmarks" / "custom_datasets" / "labels"
OUTPUT_FOLDER = Path(os.path.join(SCRIPT_DIR, "output"))

# The user chose YOLO11m based on the previous benchmark
DEFAULT_DETECTOR = str(PROJECT_ROOT / "models" / "yolo11m-pose.pt")
DEFAULT_TRACKERS = "bytetrack,deepsort"
DEFAULT_CONF_THRESHOLD = 0.25
DEFAULT_DEVICE = "auto"

