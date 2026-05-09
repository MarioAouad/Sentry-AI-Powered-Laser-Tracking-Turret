from __future__ import annotations

import argparse
import csv
import importlib
import json
from pathlib import Path
from typing import Any


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
    results = model.track(
        source=str(args.video),
        tracker="bytetrack.yaml",
        conf=args.conf_threshold,
        device=resolve_device(args.device),
        persist=True,
        stream=True,
        verbose=False,
    )
    for frame_index, result in enumerate(results, start=1):
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
    capture = cv2.VideoCapture(str(args.video))
    rows: list[dict[str, Any]] = []
    frame_index = 1

    while True:
        ok, frame = capture.read()
        if not ok:
            break
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
        frame_index += 1

    capture.release()
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
    parser.add_argument("--video", type=Path, required=True, help="Path to custom tracking video.")
    parser.add_argument("--ground-truth", type=Path, required=True, help="MOTChallenge-style ground-truth CSV/TXT.")
    parser.add_argument("--output", type=Path, default=Path("benchmark_results"))
    parser.add_argument("--detector", default="yolov8n-pose.pt")
    parser.add_argument("--trackers", default="bytetrack,deepsort")
    parser.add_argument("--conf-threshold", type=float, default=0.25)
    parser.add_argument("--device", default="auto")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = ensure_output_dir(args.output)
    if not args.video.exists():
        raise SystemExit(f"Video file not found: {args.video}")
    if not args.ground_truth.exists():
        raise SystemExit(f"Ground-truth file not found: {args.ground_truth}")

    ground_truth = parse_mot_file(args.ground_truth)
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
        "video": str(args.video),
        "ground_truth": str(args.ground_truth),
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
