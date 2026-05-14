# Python Vision Backend

Real-time vision, kinematics, API, and serial control for the Sentry turret.

## Responsibilities

- Capture frames from the configured webcam.
- Detect and track a human target with YOLO pose tracking.
- Estimate target depth from shoulder width or bounding box fallback.
- Convert camera pixels into turret-space coordinates.
- Compute pan/tilt servo angles.
- Stream annotated MJPEG video through FastAPI.
- Broadcast telemetry to the React dashboard over WebSocket.
- Send serial commands to the ESP32 actuator node.

## Setup

Python 3.10 is recommended.

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

For CUDA acceleration, install the PyTorch build that matches your GPU and CUDA runtime before installing the rest of the requirements. The portable `requirements.txt` avoids machine-local `file:///C:/...` paths.

## Model Weights

Model weights are ignored by Git. Create a local models directory and place the pose model there:

```powershell
mkdir models
# place yolo11m-pose.pt in python_vision\models
```

The orchestrator expects:

```text
python_vision/models/yolo11m-pose.pt
```

## Configuration

Edit `config/hardware_offsets.yaml` before running on hardware:

- `camera.device_index`
- `camera.frame_width` and `camera.frame_height`
- `turret_offset_cm`
- `servo_direction`
- `servo_trim`
- `serial.port`
- `serial.baud_rate`
- `vision.default_target_mode`

## Run

```powershell
python main_orchestrator.py
```

The API exposes:

- `GET /health`
- `GET /video-feed`
- `POST /target-mode`
- `POST /system-control`
- `WS /ws/telemetry`

Default backend URL:

```text
http://localhost:8000
```

## Calibration

Use the calibration helper after the camera, laser, and servos are mounted:

```powershell
python pre_deployment_calibration.py
```

It prompts for observed laser positions and produces calibration data for the kinematics pipeline.

## Benchmarks

Benchmark-only dependencies are kept separate:

```powershell
pip install -r requirements-benchmark.txt
```

Benchmark folders:

- `benchmarks/live_inference_performance`
- `benchmarks/multi_object_tracking`
- `benchmarks/pose_estimation_coco`

## Main Files

- `main_orchestrator.py`: runtime entry point.
- `src/vision/target_tracker.py`: YOLO pose tracking and target point selection.
- `src/vision/cascade_detector.py`: optional HOG gate.
- `src/kinematics/`: depth, filtering, spatial transform, inverse kinematics.
- `src/comms/serial_tether.py`: ESP32 serial transport.
- `src/api/`: FastAPI app and WebSocket telemetry.
- `config/hardware_offsets.yaml`: hardware and runtime tuning.
