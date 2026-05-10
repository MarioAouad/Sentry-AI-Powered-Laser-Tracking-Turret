from __future__ import annotations

import os
from pathlib import Path

# 1. Get the exact folder where this config.py file lives
CURRENT_DIR = Path(__file__).resolve().parent

# 2. Climb up two folders to hit the 'python_vision' root directory
PYTHON_VISION_ROOT = CURRENT_DIR.parent.parent

# 3. Point to the universal models folder
DEFAULT_MODELS_DIR = PYTHON_VISION_ROOT / "models"

# 4. CRITICAL CHANGE: Point to your custom dataset, NOT COCO!
# CURRENT_DIR is live_inference_performance
# CURRENT_DIR.parent is the benchmarks folder
DEFAULT_IMAGES_DIR = CURRENT_DIR.parent / "custom_datasets" / "images"

# Keep the output local to this specific benchmark
DEFAULT_OUTPUT_DIR = CURRENT_DIR / "output"

DEFAULT_YOLO_MODEL = "all"
DEFAULT_DEVICE = "auto"
DEFAULT_CONF_THRESHOLD = 0.25
DEFAULT_SAMPLE_RATE = 1

# We keep the model list identical so we can test the exact same architectures
YOLO_POSE_MODELS = {
    "yolov8n": str(DEFAULT_MODELS_DIR / "yolov8n-pose.pt"),
    "yolov8s": str(DEFAULT_MODELS_DIR / "yolov8s-pose.pt"),
    "yolov8m": str(DEFAULT_MODELS_DIR / "yolov8m-pose.pt"),
    "yolo11n": str(DEFAULT_MODELS_DIR / "yolo11n-pose.pt"),
    "yolo11s": str(DEFAULT_MODELS_DIR / "yolo11s-pose.pt"),
    "yolo11m": str(DEFAULT_MODELS_DIR / "yolo11m-pose.pt"),
}

