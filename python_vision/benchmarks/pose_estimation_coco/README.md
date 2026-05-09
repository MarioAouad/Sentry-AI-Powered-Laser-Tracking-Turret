# COCO-Pose Theoretical Accuracy Benchmark

Script:

```text
benchmark_vision_coco.py
```

Editable config:

```text
config.py
```

This benchmark measures pure skeleton accuracy on a COCO-Pose validation subset. It compares YOLO pose models against MediaPipe BlazePose using:

- official COCO keypoint `mAP`, `AP50`, `AP75`, and `AR` through `pycocotools`
- OKS-based precision, recall, and F1
- mean OKS
- PCK
- mean and median latency

## Data

Required:

- COCO validation images folder, for example `val2017`
- COCO keypoint annotations, for example `person_keypoints_val2017.json`

By default, `config.py` points to:

```text
images/
person_keypoints_val2017.json
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

## Example

```bash
python benchmark_vision_coco.py --images C:\datasets\coco\val2017 --annotations C:\datasets\coco\annotations\person_keypoints_val2017.json --output output --limit 200 --yolo-model all
```

You can also edit `config.py` and run:

```bash
python benchmark_vision_coco.py
```

## Outputs

- `coco_predictions_yolov8n.json`
- `coco_predictions_yolov8s.json`
- `coco_predictions_yolov8m.json`
- `coco_predictions_yolo11n.json`
- `coco_predictions_yolo11s.json`
- `coco_predictions_yolo11m.json`
- `coco_predictions_mediapipe.json`
- `benchmark_vision_coco_report.json`
- `benchmark_vision_coco_summary.csv`

