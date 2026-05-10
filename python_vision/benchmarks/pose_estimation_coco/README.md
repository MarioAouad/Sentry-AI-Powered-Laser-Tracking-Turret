# COCO-Pose Theoretical Accuracy Benchmark

## Overview

This benchmark measures the theoretical accuracy of state-of-the-art pose estimation models against a standard COCO validation subset. It evaluates pure skeletal keypoint extraction capability in a highly controlled, multi-person environment.

**Script:** `benchmark_vision_coco.py`
**Config:** `config.py`

## How it Works

The script iterates through a subset of the COCO 2017 validation dataset and evaluates each model using standard Multi-Person Pose Estimation metrics. It compares Ultralytics YOLO-Pose architectures against the CPU-baseline MediaPipe BlazePose. 

### Metrics Explained
*   **mAP (Mean Average Precision):** Evaluates overall spatial accuracy of the keypoints across varying IoU thresholds. 
*   **F1-Score:** The harmonic mean of Precision (avoiding false positives) and Recall (finding all targets). Crucial for knowing how "intelligent" the model is at recognizing human shapes without hallucinating.
*   **OKS (Object Keypoint Similarity):** Measures how close the predicted keypoint is to the ground truth, normalized by the scale of the person.
*   **PCK (Percentage of Correct Keypoints):** Measures the percentage of keypoints that fall within a strict pixel threshold of the ground truth.

## The Results & What They Prove

*   **MediaPipe Failure:** MediaPipe completely collapsed on the multi-person COCO dataset (mAP: ~0.13), proving that a robust, GPU-accelerated deep learning model is required for environments with severe occlusion.
*   **YOLO11m-Pose vs YOLOv8m-Pose:** Both medium variants dominated the tests. While YOLOv8m slightly won the raw mAP (0.616), **YOLO11m-Pose** won the critical F1-Score (0.671).

### Final Decision: YOLO11m-Pose
We selected **YOLO11m-Pose** because its superior F1-Score guarantees the best balance of Precision and Recall. It minimizes false positives (which would cause the turret servos to wildly actuate) while maintaining elite spatial accuracy, which is required for our mathematical Z-axis depth estimation.

---
## Usage

**Data Required:**
- COCO validation images folder (`val2017`)
- COCO keypoint annotations (`person_keypoints_val2017.json`)

**Run the Benchmark:**
```bash
python benchmark_vision_coco.py --images C:\datasets\coco\val2017 --annotations C:\datasets\coco\annotations\person_keypoints_val2017.json --output output --limit 200 --yolo-model all
```

Outputs are securely timestamped inside the `output/run_YYYYMMDD_HHMMSS/` directory to prevent data overwriting.
