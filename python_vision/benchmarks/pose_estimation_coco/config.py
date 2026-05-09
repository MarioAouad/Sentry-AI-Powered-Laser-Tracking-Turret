from __future__ import annotations

import os
from pathlib import Path


# Edit these values during analysis instead of changing benchmark_vision_coco.py.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

DEFAULT_IMAGES_DIR = Path(os.path.join(SCRIPT_DIR, "images"))
DEFAULT_ANNOTATIONS = Path(os.path.join(SCRIPT_DIR, "person_keypoints_val2017.json"))
DEFAULT_OUTPUT_DIR = Path(os.path.join(SCRIPT_DIR, "output"))

DEFAULT_IMAGE_LIMIT = 200
DEFAULT_YOLO_MODEL = "all"
DEFAULT_DEVICE = "auto"
DEFAULT_CONF_THRESHOLD = 0.25
DEFAULT_OKS_THRESHOLD = 0.50
DEFAULT_PCK_THRESHOLD = 0.20

YOLO_POSE_MODELS = {
    "yolov8n": "yolov8n-pose.pt",
    "yolov8s": "yolov8s-pose.pt",
    "yolov8m": "yolov8m-pose.pt",
    "yolo11n": "yolo11n-pose.pt",
    "yolo11s": "yolo11s-pose.pt",
    "yolo11m": "yolo11m-pose.pt",
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

