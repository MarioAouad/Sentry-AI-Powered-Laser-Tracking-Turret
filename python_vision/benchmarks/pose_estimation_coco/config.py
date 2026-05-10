from __future__ import annotations

import os
from pathlib import Path

# 1. Get the exact folder where this config.py file lives
CURRENT_DIR = Path(__file__).resolve().parent

# 2. Climb up two folders to hit the 'python_vision' root directory
# CURRENT_DIR = pose_estimation_coco
# .parent = benchmarks
# .parent.parent = python_vision
PYTHON_VISION_ROOT = CURRENT_DIR.parent.parent

# 3. Point to the universal models folder
DEFAULT_MODELS_DIR = PYTHON_VISION_ROOT / "models"

# Keep your existing local paths for images and output
DEFAULT_IMAGES_DIR = CURRENT_DIR / "images"
DEFAULT_ANNOTATIONS = CURRENT_DIR / "person_keypoints_val2017.json"
DEFAULT_OUTPUT_DIR = CURRENT_DIR / "output"

DEFAULT_IMAGE_LIMIT = None
DEFAULT_YOLO_MODEL = "all"
DEFAULT_DEVICE = "auto"
DEFAULT_CONF_THRESHOLD = 0.25
DEFAULT_OKS_THRESHOLD = 0.50
DEFAULT_PCK_THRESHOLD = 0.20

YOLO_POSE_MODELS = {
    "yolov8n": str(DEFAULT_MODELS_DIR / "yolov8n-pose.pt"),
    "yolov8s": str(DEFAULT_MODELS_DIR / "yolov8s-pose.pt"),
    "yolov8m": str(DEFAULT_MODELS_DIR / "yolov8m-pose.pt"),
    "yolo11n": str(DEFAULT_MODELS_DIR / "yolo11n-pose.pt"),
    "yolo11s": str(DEFAULT_MODELS_DIR / "yolo11s-pose.pt"),
    "yolo11m": str(DEFAULT_MODELS_DIR / "yolo11m-pose.pt"),
}

# COCO keypoint OKS sigmas. OKS is like IoU for skeletons: it rewards keypoints
# that are close to ground truth after normalizing by person scale.
COCO_OKS_SIGMAS = [
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
]

# MediaPipe BlazePose has 33 landmarks. This table maps the 17 COCO keypoints
# to the corresponding MediaPipe landmark indexes.
MEDIAPIPE_TO_COCO = [0, 2, 5, 7, 8, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28]

