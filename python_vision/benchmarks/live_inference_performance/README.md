# Hardware & Environment Live Inference Benchmark

## Overview

This benchmark validates the real-world runtime performance of the models directly on the target edge-compute hardware (RTX 4060). It measures how fast and stable the models are when exposed to environmental noise, motion blur, and webcam domain shift.

**Script:** `benchmark_vision_hardware.py`
**Config:** `config.py`

## How it Works

The script reads a custom sequential evaluation dataset (1,055 frames of a human moving with intentional occlusions) from `custom_datasets/images/`. It processes these frames using YOLO architectures (on GPU) and MediaPipe (on CPU), recording the exact latency, framerate, and confidence score degradations.

### Metrics Explained
*   **FPS (Frames Per Second):** The total system throughput. The Turret strictly requires >30 FPS to calculate real-time Inverse Kinematics and pass smooth PID angles to the ESP32.
*   **Total Latency (ms):** The exact delay introduced by the AI processing layer (Preprocessing + Inference + Postprocessing).
*   **Mean Confidence:** A critical metric for evaluating "Domain Shift". If a model performs perfectly on the theoretical COCO dataset but drops to 40% confidence on a cheap, grainy webcam, it fails the real-world test.

## The Results & What They Prove

*   **FPS Headroom:** The nano models (`yolov8n`, `yolo11n`) reached ~150 FPS, proving the RTX 4060 has massive overhead.
*   **Confidence Stability:** The **YOLO11m** model maintained an astonishing **85.7% average confidence** across all 1,055 frames of the noisy webcam data, vastly outperforming MediaPipe's CPU baseline (66.3%).

### Final Decision: YOLO11m-Pose
Because we had tremendous FPS overhead, we did not need to sacrifice intelligence for speed. **YOLO11m** runs at **~96.1 FPS** (3x the required baseline) with an inference latency of just ~10.8ms. This provides us the perfect balance: it is extremely fast, highly resistant to webcam noise (eliminating confidence degradation), and provides rock-solid `(X, Y)` keypoints for the downstream kinematic translation.

---
## Usage

**Data Required:**
- Custom image sequence in `custom_datasets/images/`

**Run the Benchmark:**
```bash
python benchmark_vision_hardware.py --images-dir ../custom_datasets/images --output output --yolo-model all
```

Outputs are securely timestamped inside the `output/run_YYYYMMDD_HHMMSS/` directory to prevent data overwriting.
