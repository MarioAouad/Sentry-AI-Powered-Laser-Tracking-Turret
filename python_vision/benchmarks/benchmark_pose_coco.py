from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path

from common import Timer, coco_oks, stats_to_dict, summarize_latency, write_json


def load_coco_people(annotation_path: Path, limit: int | None) -> list[dict]:
    data = json.loads(annotation_path.read_text(encoding="utf-8"))
    image_by_id = {image["id"]: image for image in data["images"]}
    people = []
    for ann in data["annotations"]:
        if ann.get("iscrowd", 0) or ann.get("num_keypoints", 0) == 0:
            continue
        image = image_by_id.get(ann["image_id"])
        if not image:
            continue
        keypoints = [
            ann["keypoints"][idx : idx + 3]
            for idx in range(0, len(ann["keypoints"]), 3)
        ]
        people.append(
            {
                "image_path": image["file_name"],
                "bbox": ann["bbox"],
                "area": float(ann.get("area") or ann["bbox"][2] * ann["bbox"][3]),
                "keypoints": keypoints,
            }
        )
        if limit and len(people) >= limit:
            break
    return people


def predict_yolo(model, image_path: Path) -> tuple[list[list[float]] | None, float | None]:
    results = model.predict(str(image_path), verbose=False)
    if not results or results[0].keypoints is None or len(results[0].keypoints.xy) == 0:
        return None, None
    boxes = results[0].boxes
    best_index = int(boxes.conf.argmax().item()) if boxes is not None and boxes.conf is not None else 0
    confidence = float(boxes.conf[best_index].item()) if boxes is not None and boxes.conf is not None else None
    points = results[0].keypoints.xy[best_index].cpu().tolist()
    return [[float(x), float(y)] for x, y in points], confidence


def predict_mediapipe(model, image_path: Path) -> tuple[list[list[float]] | None, float | None]:
    try:
        cv2 = importlib.import_module("cv2")
    except ImportError as exc:
        raise SystemExit("Install opencv-python to run MediaPipe COCO benchmarks.") from exc

    image = cv2.imread(str(image_path))
    if image is None:
        return None, None
    height, width = image.shape[:2]
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    result = model.process(rgb)
    if not result.pose_landmarks:
        return None, None
    points = [
        [landmark.x * width, landmark.y * height]
        for landmark in result.pose_landmarks.landmark[:17]
    ]
    confidence = sum(landmark.visibility for landmark in result.pose_landmarks.landmark[:17]) / 17
    return points, float(confidence)


def load_model(name: str, model_path: str | None):
    if name == "yolo":
        try:
            ultralytics = importlib.import_module("ultralytics")
        except ImportError as exc:
            raise SystemExit("Install ultralytics to run YOLO COCO benchmarks.") from exc
        return ultralytics.YOLO(model_path or "yolov8n-pose.pt")
    if name == "mediapipe":
        try:
            mediapipe = importlib.import_module("mediapipe")
        except ImportError as exc:
            raise SystemExit("Install mediapipe to run BlazePose COCO benchmarks.") from exc
        return mediapipe.solutions.pose.Pose(static_image_mode=True, model_complexity=2)
    raise ValueError(name)


def run(args: argparse.Namespace) -> dict:
    people = load_coco_people(args.annotations, args.limit)
    model = load_model(args.model, args.model_path)
    latencies: list[float] = []
    confidences: list[float] = []
    oks_scores: list[float] = []
    detections = 0

    for person in people:
        image_path = args.images / person["image_path"]
        with Timer() as timer:
            if args.model == "yolo":
                predicted, confidence = predict_yolo(model, image_path)
            else:
                predicted, confidence = predict_mediapipe(model, image_path)
        latencies.append(timer.elapsed_ms)
        if confidence is not None:
            confidences.append(confidence)
        if predicted is None:
            oks_scores.append(0.0)
            continue
        detections += 1
        oks_scores.append(coco_oks(predicted, person["keypoints"], person["area"]))

    thresholds = [round(value / 100, 2) for value in range(50, 100, 5)]
    ap_by_threshold = {
        f"AP@OKS={threshold:.2f}": sum(score >= threshold for score in oks_scores) / len(oks_scores)
        if oks_scores
        else 0.0
        for threshold in thresholds
    }
    payload = {
        "model": args.model,
        "samples": len(people),
        "detection_rate": detections / len(people) if people else 0.0,
        "mean_oks": sum(oks_scores) / len(oks_scores) if oks_scores else 0.0,
        "ap": ap_by_threshold,
        "latency": stats_to_dict(summarize_latency(latencies, confidences)),
    }
    write_json(args.output / f"pose_coco_{args.model}.json", payload)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark pose accuracy on a COCO-Pose subset.")
    parser.add_argument("--model", choices=("yolo", "mediapipe"), required=True)
    parser.add_argument("--model-path", help="YOLO pose model path. Defaults to yolov8n-pose.pt.")
    parser.add_argument("--images", type=Path, required=True, help="Directory containing COCO images.")
    parser.add_argument("--annotations", type=Path, required=True, help="COCO person_keypoints JSON file.")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--output", type=Path, default=Path("benchmark_results"))
    return parser.parse_args()


if __name__ == "__main__":
    print(run(parse_args()))
