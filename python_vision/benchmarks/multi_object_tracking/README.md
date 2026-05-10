# Multi-Object Tracking (MOT) Ablation Benchmark

## Overview

This benchmark evaluates the temporal identity consistency of tracking algorithms when paired with our chosen vision backbone (YOLO11m-Pose). It tests the system's ability to maintain a lock on a single target across sequential frames, evaluating robustness against motion blur, occlusion, and crossing trajectories.

**Script:** `benchmark_tracking_ablation.py`
**Config:** `config.py`

## How it Works

The benchmark leverages `motmetrics` to compare the predicted bounding boxes from the tracking algorithms (ByteTrack and DeepSORT) against a normalized YOLO-format Ground Truth exported from Roboflow. The script dynamically translates the Roboflow dataset into a MOTChallenge-compliant tensor, computing penalties for False Positives, Misses, and Identity Switches.

### Metrics Explained
*   **MOTA (Multi-Object Tracking Accuracy):** The gold standard tracking metric. It aggregates false positives, false negatives, and identity switches. Higher is better.
*   **IDF1 (Identity F1 Score):** Measures the consistency of the ID assignment. It drops significantly if the tracker randomly assigns a new ID to the target mid-video.
*   **Precision & Recall:** Precision measures how often a drawn box actually contains the target (avoiding "ghost" boxes). Recall measures how often the target is successfully captured (avoiding drops).
*   **MOTP (Multi-Object Tracking Precision):** Calculates the average pixel distance error between the predicted box and the exact ground truth. Lower is better.

## The Results & What They Prove

*   **ByteTrack:** MOTA = 94.07% | IDF1 = 63.60% | Precision = 97.23%
*   **DeepSORT:** MOTA = 90.50% | IDF1 = 61.57% | Precision = 92.77%

ByteTrack significantly outperformed DeepSORT because of how it handles low-confidence frames. DeepSORT aggressively drops blurry frames and relies on a heavy CNN visual embedder. ByteTrack intelligently uses Kalman filters to mathematically predict where the target went during a blur, linking the low-confidence detections via Intersection-over-Union (IoU).

### Final Decision: ByteTrack
We selected **ByteTrack** for the Sentry Turret. Its elite **97.23% Precision** guarantees that the tracker hallucinated almost zero "Ghost Targets" (False Positives). For the hardware turret, false positives are fatal—they cause the physical servo motors to violently snap away from the true target. Furthermore, because ByteTrack uses pure mathematics instead of DeepSORT's CNN feature extractor, it consumes zero extra VRAM, allowing the YOLO11m backbone to maintain >90 FPS real-time speeds.

---
## Usage

**Data Required:**
- Sequence of images in `custom_datasets/images/`
- Roboflow YOLO labels in `custom_datasets/labels/`

**Run the Benchmark:**
```bash
python benchmark_tracking_ablation.py --images-dir ../custom_datasets/images --labels-dir ../custom_datasets/labels --output output --trackers bytetrack,deepsort
```

Outputs are securely timestamped inside the `output/run_YYYYMMDD_HHMMSS/` directory to prevent data overwriting.
