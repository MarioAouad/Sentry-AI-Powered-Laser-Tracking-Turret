# Vision Benchmark Suite

This folder contains the benchmark code required by the project spec:

- `benchmark_pose_coco.py` compares YOLOv8/YOLO11 pose variants and MediaPipe BlazePose on a COCO-Pose subset.
- `benchmark_live_inference.py` measures live webcam/video latency, FPS, and confidence degradation.
- `benchmark_tracking_metrics.py` evaluates ByteTrack/DeepSORT outputs against annotated ground truth using MOTA, ID switches, precision, recall, and mean IoU.

## Install optional dependencies

Install only the tools you need for the benchmark you are running:

```bash
pip install opencv-python ultralytics mediapipe
```

## Pose accuracy benchmark

Use a COCO keypoint annotations file and the matching image folder:

```bash
python benchmark_pose_coco.py --model yolo --images C:\datasets\coco\val2017 --annotations C:\datasets\coco\annotations\person_keypoints_val2017.json --limit 200
python benchmark_pose_coco.py --model mediapipe --images C:\datasets\coco\val2017 --annotations C:\datasets\coco\annotations\person_keypoints_val2017.json --limit 200
```

Named YOLO variants:

```bash
python benchmark_pose_coco.py --model yolo --yolo-variant yolov8n --images C:\datasets\coco\val2017 --annotations C:\datasets\coco\annotations\person_keypoints_val2017.json
python benchmark_pose_coco.py --model yolo --yolo-variant yolov8s --images C:\datasets\coco\val2017 --annotations C:\datasets\coco\annotations\person_keypoints_val2017.json
python benchmark_pose_coco.py --model yolo --yolo-variant yolov8m --images C:\datasets\coco\val2017 --annotations C:\datasets\coco\annotations\person_keypoints_val2017.json
python benchmark_pose_coco.py --model yolo --yolo-variant yolo11n --images C:\datasets\coco\val2017 --annotations C:\datasets\coco\annotations\person_keypoints_val2017.json
python benchmark_pose_coco.py --model yolo --yolo-variant yolo11s --images C:\datasets\coco\val2017 --annotations C:\datasets\coco\annotations\person_keypoints_val2017.json
python benchmark_pose_coco.py --model yolo --yolo-variant yolo11m --images C:\datasets\coco\val2017 --annotations C:\datasets\coco\annotations\person_keypoints_val2017.json
```

Run all YOLO COCO variants in one command:

```bash
python benchmark_pose_coco.py --model yolo --yolo-variant all --images C:\datasets\coco\val2017 --annotations C:\datasets\coco\annotations\person_keypoints_val2017.json
```

Outputs are written to `benchmark_results/pose_coco_<model>.json`.

## Live hardware-loop inference benchmark

Use webcam `0`, a video file, or the ESP32/webcam stream URL:

```bash
python benchmark_live_inference.py --model yolo --source 0 --frames 300
python benchmark_live_inference.py --model mediapipe --source 0 --frames 300
```

Run a specific YOLO variant:

```bash
python benchmark_live_inference.py --model yolo --yolo-variant yolov8n --source 0 --frames 300
python benchmark_live_inference.py --model yolo --yolo-variant yolov8s --source 0 --frames 300
python benchmark_live_inference.py --model yolo --yolo-variant yolov8m --source 0 --frames 300
python benchmark_live_inference.py --model yolo --yolo-variant yolo11n --source 0 --frames 300
python benchmark_live_inference.py --model yolo --yolo-variant yolo11s --source 0 --frames 300
python benchmark_live_inference.py --model yolo --yolo-variant yolo11m --source 0 --frames 300
```

Outputs include per-frame latency CSVs and summary JSON files.

## Tracking benchmark

Export your annotated ground truth and tracker predictions as CSV files with this schema:

```csv
frame,track_id,x,y,w,h
0,1,120,80,90,210
1,1,123,81,90,210
```

Then run:

```bash
python benchmark_tracking_metrics.py --tracker-name bytetrack --ground-truth ground_truth.csv --predictions bytetrack_predictions.csv
python benchmark_tracking_metrics.py --tracker-name deepsort --ground-truth ground_truth.csv --predictions deepsort_predictions.csv
```

This gives the ablation metrics needed to compare target persistence after occlusion.
