# Hardware & Environment Video Benchmark

Script:

```text
benchmark_vision_hardware.py
```

This benchmark measures real-world runtime performance on a custom video or webcam. It compares YOLO pose models on GPU when available against MediaPipe BlazePose on CPU using:

- FPS
- total latency
- preprocess, inference, and postprocess latency
- confidence per frame
- frame brightness for later domain-shift analysis
- YOLO VRAM usage when available
- MediaPipe CPU RAM usage

## Data

Required:

- `Dataset.mp4`, or use `--webcam`

By default, the script looks for:

```text
Dataset.mp4
output/
```

inside this folder.

## Models

By default, `--yolo-model all` runs:

```text
yolov8n-pose.pt
yolov8s-pose.pt
yolov8m-pose.pt
yolo11n-pose.pt
yolo11s-pose.pt
yolo11m-pose.pt
```

MediaPipe BlazePose is also evaluated once.

## Examples

```bash
python benchmark_vision_hardware.py --video Dataset.mp4 --output output --yolo-model all
```

Webcam:

```bash
python benchmark_vision_hardware.py --webcam --output output --yolo-model all
```

## Outputs

- `benchmark_vision_hardware_per_frame.csv`
- `benchmark_vision_hardware_report.json`
- `confidence_plot.png` if `matplotlib` is installed
- `latency_plot.png` if `matplotlib` is installed

