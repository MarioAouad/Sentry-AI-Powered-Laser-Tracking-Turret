from __future__ import annotations

import os
from pathlib import Path


# Edit these values during analysis instead of changing benchmark_tracking_ablation.py.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

VIDEO_PATH = Path(os.path.join(SCRIPT_DIR, "tracking_video.mp4"))
GROUND_TRUTH_PATH = Path(os.path.join(SCRIPT_DIR, "ground_truth.txt"))
OUTPUT_FOLDER = Path(os.path.join(SCRIPT_DIR, "output"))

DEFAULT_DETECTOR = "yolov8n-pose.pt"
DEFAULT_TRACKERS = "bytetrack,deepsort"
DEFAULT_CONF_THRESHOLD = 0.25
DEFAULT_DEVICE = "auto"

