from __future__ import annotations

import os
from pathlib import Path


# Edit these values during analysis instead of changing benchmark_vision_hardware.py.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

VIDEO_PATH = Path(os.path.join(SCRIPT_DIR, "Dataset.mp4"))
OUTPUT_FOLDER = Path(os.path.join(SCRIPT_DIR, "output"))

DEFAULT_YOLO_MODEL = "all"
DEFAULT_DEVICE = "auto"
DEFAULT_CONF_THRESHOLD = 0.25
DEFAULT_SAMPLE_RATE = 1

YOLO_POSE_MODELS = {
    "yolov8n": "yolov8n-pose.pt",
    "yolov8s": "yolov8s-pose.pt",
    "yolov8m": "yolov8m-pose.pt",
    "yolo11n": "yolo11n-pose.pt",
    "yolo11s": "yolo11s-pose.pt",
    "yolo11m": "yolo11m-pose.pt",
}

