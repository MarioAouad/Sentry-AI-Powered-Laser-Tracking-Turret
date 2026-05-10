from __future__ import annotations

import argparse
import csv
import importlib
import json
import time
from pathlib import Path
from typing import Any

from config import (
    DEFAULT_CONF_THRESHOLD,
    DEFAULT_DETECTOR,
    DEFAULT_DEVICE,
    DEFAULT_TRACKERS,
    IMAGES_DIR,
    LABELS_DIR,
    OUTPUT_FOLDER,
)


def require_module(module_name: str, install_hint: str):
    try:
        return importlib.import_module(module_name)
    except ImportError as exc:
        raise SystemExit(f"Missing dependency '{module_name}'. Install it with: {install_hint}") from exc


def optional_module(module_name: str):
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None


def resolve_device(requested: str) -> str:
    if requested != "auto":
        return requested
    try:
        torch = importlib.import_module("torch")
        return "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:
        return "cpu"


def ensure_output_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def parse_mot_file(path: Path) -> dict[int, list[dict[str, Any]]]:
    # MOTChallenge format:
    # frame, id, x, y, w, h, conf, class, visibility
    tracks: dict[int, list[dict[str, Any]]] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if not row or row[0].strip().startswith("#"):
                continue
            if row[0].strip().lower() == "frame":
                continue
            if len(row) < 6:
                continue
            frame = int(float(row[0]))
            track_id = int(float(row[1]))
            bbox = [float(row[2]), float(row[3]), float(row[4]), float(row[5])]
            visibility = float(row[8]) if len(row) > 8 and row[8] != "" else 1.0
            tracks.setdefault(frame, []).append({"id": track_id, "bbox": bbox, "visibility": visibility})
    return tracks


def parse_yolo_labels(labels_dir: Path, images_dir: Path) -> dict[int, list[dict[str, Any]]]:
    cv2 = optional_module("cv2")
    tracks: dict[int, list[dict[str, Any]]] = {}
    label_files = sorted([p for p in labels_dir.iterdir() if p.suffix == ".txt" and p.stem != ".gitkeep"])
    image_files = sorted([p for p in images_dir.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"} and p.stem != ".gitkeep"])
    
    for frame_index, (label_path, img_path) in enumerate(zip(label_files, image_files), start=1):
        if cv2 is not None:
            img = cv2.imread(str(img_path))
            h_img, w_img = img.shape[:2] if img is not None else (640, 640)
        else:
            h_img, w_img = 640, 640

        with label_path.open("r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split()
                if not parts:
                    continue
                coords = [float(p) for p in parts[1:]]
                if len(coords) == 4:
                    x_center, y_center, width, height = coords
                    xmin = (x_center - width / 2) * w_img
                    ymin = (y_center - height / 2) * h_img
                    w_abs = width * w_img
                    h_abs = height * h_img
                else:
                    x_coords = coords[0::2]
                    y_coords = coords[1::2]
                    xmin = min(x_coords) * w_img
                    xmax = max(x_coords) * w_img
                    ymin = min(y_coords) * h_img
                    ymax = max(y_coords) * h_img
                    w_abs = xmax - xmin
                    h_abs = ymax - ymin
                
                tracks.setdefault(frame_index, []).append({
                    "id": 1, 
                    "bbox": [xmin, ymin, w_abs, h_abs], 
                    "visibility": 1.0
                })
    return tracks


def xywh_to_xyxy(bbox: list[float]) -> list[float]:
    x, y, w, h = bbox
    return [x, y, x + w, y + h]


def iou_xywh(a: list[float], b: list[float]) -> float:
    ax1, ay1, ax2, ay2 = xywh_to_xyxy(a)
    bx1, by1, bx2, by2 = xywh_to_xyxy(b)
    inter_w = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    inter_h = max(0.0, min(ay2, by2) - max(ay1, by1))
    inter = inter_w * inter_h
    union = a[2] * a[3] + b[2] * b[3] - inter
    return inter / union if union > 0 else 0.0


def run_bytetrack(args: argparse.Namespace, output_dir: Path) -> Path | None:
    ultralytics = optional_module("ultralytics")
    if ultralytics is None:
        print("Warning: skipping ByteTrack because ultralytics is not installed. Install with: pip install ultralytics")
        return None

    model = ultralytics.YOLO(args.detector)
    rows: list[dict[str, Any]] = []
    
    image_paths = sorted([p for p in args.images_dir.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"} and p.stem != ".gitkeep"])
    
    for frame_index, img_path in enumerate(image_paths, start=1):
        results = model.track(
            source=str(img_path),
            tracker="bytetrack.yaml",
            conf=args.conf_threshold,
            device=resolve_device(args.device),
            persist=True,
            verbose=False,
        )
        for result in results:
            if result.boxes is None or result.boxes.id is None:
                continue
            boxes = result.boxes.xywh.cpu().tolist()
            ids = result.boxes.id.cpu().tolist()
            confs = result.boxes.conf.cpu().tolist() if result.boxes.conf is not None else [1.0] * len(boxes)
            for bbox, track_id, conf in zip(boxes, ids, confs):
                cx, cy, w, h = [float(value) for value in bbox]
                rows.append(
                    {
                        "frame": frame_index,
                        "id": int(track_id),
                        "x": cx - w / 2,
                        "y": cy - h / 2,
                        "w": w,
                        "h": h,
                        "conf": float(conf),
                        "class": 1,
                        "visibility": 1.0,
                    }
                )
    path = output_dir / "bytetrack_predictions.csv"
    write_csv(path, rows)
    return path


def run_deepsort(args: argparse.Namespace, output_dir: Path) -> Path | None:
    deep_sort_mod = optional_module("deep_sort_realtime.deepsort_tracker")
    ultralytics = optional_module("ultralytics")
    cv2 = optional_module("cv2")
    if deep_sort_mod is None:
        print(
            "Warning: skipping DeepSORT because deep_sort_realtime is not installed. "
            "Install with: pip install deep-sort-realtime"
        )
        return None
    if ultralytics is None or cv2 is None:
        print("Warning: skipping DeepSORT because ultralytics/opencv-python is missing.")
        return None

    tracker = deep_sort_mod.DeepSort(max_age=30)
    model = ultralytics.YOLO(args.detector)
    rows: list[dict[str, Any]] = []
    
    image_paths = sorted([p for p in args.images_dir.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"} and p.stem != ".gitkeep"])

    for frame_index, img_path in enumerate(image_paths, start=1):
        frame = cv2.imread(str(img_path))
        if frame is None:
            continue
        detections = []
        result = model.predict(frame, conf=args.conf_threshold, device=resolve_device(args.device), verbose=False)[0]
        if result.boxes is not None:
            boxes = result.boxes.xywh.cpu().tolist()
            confs = result.boxes.conf.cpu().tolist() if result.boxes.conf is not None else [1.0] * len(boxes)
            for bbox, conf in zip(boxes, confs):
                cx, cy, w, h = [float(value) for value in bbox]
                detections.append(([cx - w / 2, cy - h / 2, w, h], float(conf), "person"))
        tracks = tracker.update_tracks(detections, frame=frame)
        for track in tracks:
            if not track.is_confirmed():
                continue
            left, top, right, bottom = track.to_ltrb()
            rows.append(
                {
                    "frame": frame_index,
                    "id": int(track.track_id),
                    "x": float(left),
                    "y": float(top),
                    "w": float(right - left),
                    "h": float(bottom - top),
                    "conf": 1.0,
                    "class": 1,
                    "visibility": 1.0,
                }
            )

    path = output_dir / "deepsort_predictions.csv"
    write_csv(path, rows)
    return path


def evaluate_tracker(ground_truth: dict[int, list[dict[str, Any]]], predictions: dict[int, list[dict[str, Any]]]) -> dict[str, float]:
    motmetrics = require_module("motmetrics", "pip install motmetrics")
    accumulator = motmetrics.MOTAccumulator(auto_id=True)

    for frame in sorted(set(ground_truth) | set(predictions)):
        gt_items = ground_truth.get(frame, [])
        pred_items = predictions.get(frame, [])
        gt_ids = [item["id"] for item in gt_items]
        pred_ids = [item["id"] for item in pred_items]
        distances = []
        for gt in gt_items:
            row = []
            for pred in pred_items:
                overlap = iou_xywh(gt["bbox"], pred["bbox"])
                row.append(1.0 - overlap if overlap >= 0.5 else float("nan"))
            distances.append(row)
        accumulator.update(gt_ids, pred_ids, distances)

    metrics = motmetrics.metrics.create()
    summary = metrics.compute(
        accumulator,
        metrics=[
            "mota",
            "motp",
            "idf1",
            "num_switches",
            "mostly_tracked",
            "mostly_lost",
            "num_fragmentations",
            "precision",
            "recall",
        ],
        name="tracker",
    )
    row = summary.loc["tracker"]
    return {
        "MOTA": float(row["mota"]),
        "MOTP": float(row["motp"]),
        "IDF1": float(row["idf1"]),
        "IDSW": int(row["num_switches"]),
        "MT": int(row["mostly_tracked"]),
        "ML": int(row["mostly_lost"]),
        "Frag": int(row["num_fragmentations"]),
        "precision": float(row["precision"]),
        "recall": float(row["recall"]),
    }


def winner(trackers: dict[str, dict[str, Any]], metric: str, lowest: bool = False) -> str | None:
    if not trackers:
        return None
    return min(trackers, key=lambda name: trackers[name][metric]) if lowest else max(trackers, key=lambda name: trackers[name][metric])


def print_summary(report: dict[str, Any]) -> None:
    print("\nTracking Ablation Summary")
    print("-------------------------")
    for name, metrics in report["trackers"].items():
        print(
            f"{name}: MOTA={metrics['MOTA']:.4f}, IDF1={metrics['IDF1']:.4f}, "
            f"IDSW={metrics['IDSW']}, MOTP={metrics['MOTP']:.4f}, Frag={metrics['Frag']}"
        )
    winners = report["winner_summary"]
    print(
        f"Winners: MOTA={winners['best_MOTA']}, IDF1={winners['best_IDF1']}, "
        f"MOTP={winners['best_MOTP']}, IDSW={winners['lowest_ID_switches']}, Frag={winners['lowest_fragmentations']}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tracking ablation study for temporal identity consistency.")
    parser.add_argument("--images-dir", type=Path, default=IMAGES_DIR, help="Path to custom tracking images.")
    parser.add_argument("--labels-dir", type=Path, default=LABELS_DIR, help="Path to Roboflow YOLO labels.")
    parser.add_argument("--output", type=Path, default=OUTPUT_FOLDER)
    parser.add_argument("--detector", default=DEFAULT_DETECTOR)
    parser.add_argument("--trackers", default=DEFAULT_TRACKERS)
    parser.add_argument("--conf-threshold", type=float, default=DEFAULT_CONF_THRESHOLD)
    parser.add_argument("--device", default=DEFAULT_DEVICE)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_dir = ensure_output_dir(args.output / f"run_{timestamp}")
    
    if not args.images_dir.exists():
        raise SystemExit(f"Images directory not found: {args.images_dir}")
    if not args.labels_dir.exists():
        raise SystemExit(f"Labels directory not found: {args.labels_dir}")

    ground_truth = parse_yolo_labels(args.labels_dir, args.images_dir)
    prediction_paths: dict[str, Path] = {}
    selected_trackers = [item.strip().lower() for item in args.trackers.split(",") if item.strip()]

    if "bytetrack" in selected_trackers:
        path = run_bytetrack(args, output_dir)
        if path:
            prediction_paths["bytetrack"] = path
    if "deepsort" in selected_trackers:
        path = run_deepsort(args, output_dir)
        if path:
            prediction_paths["deepsort"] = path

    tracker_reports: dict[str, dict[str, Any]] = {}
    for tracker_name, prediction_path in prediction_paths.items():
        predictions = parse_mot_file(prediction_path)
        tracker_reports[tracker_name] = evaluate_tracker(ground_truth, predictions)

    report = {
        "benchmark": "tracking_ablation_custom_video",
        "images_dir": str(args.images_dir),
        "labels_dir": str(args.labels_dir),
        "trackers": tracker_reports,
        "winner_summary": {
            "best_MOTA": winner(tracker_reports, "MOTA"),
            "best_IDF1": winner(tracker_reports, "IDF1"),
            "best_MOTP": winner(tracker_reports, "MOTP"),
            "lowest_ID_switches": winner(tracker_reports, "IDSW", lowest=True),
            "lowest_fragmentations": winner(tracker_reports, "Frag", lowest=True),
        },
    }

    summary_rows = [{"tracker": name, **metrics} for name, metrics in tracker_reports.items()]
    write_json(output_dir / "benchmark_tracking_ablation_report.json", report)
    write_csv(output_dir / "benchmark_tracking_ablation_summary.csv", summary_rows)
    write_csv(output_dir / "tracking_metrics_per_tracker.csv", summary_rows)
    print_summary(report)


if __name__ == "__main__":
    main()
