from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

from common import iou_xywh, write_json


def read_tracks(path: Path) -> dict[int, list[dict]]:
    frames: dict[int, list[dict]] = defaultdict(list)
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"frame", "track_id", "x", "y", "w", "h"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise SystemExit(f"{path} is missing required columns: {sorted(missing)}")
        for row in reader:
            frames[int(row["frame"])].append(
                {
                    "track_id": str(row["track_id"]),
                    "bbox": [float(row["x"]), float(row["y"]), float(row["w"]), float(row["h"])],
                }
            )
    return frames


def greedy_match(gt_items: list[dict], pred_items: list[dict], threshold: float) -> list[tuple[dict, dict, float]]:
    candidates = []
    for gt in gt_items:
        for pred in pred_items:
            score = iou_xywh(gt["bbox"], pred["bbox"])
            if score >= threshold:
                candidates.append((score, gt, pred))
    matches = []
    used_gt: set[str] = set()
    used_pred: set[str] = set()
    for score, gt, pred in sorted(candidates, key=lambda item: item[0], reverse=True):
        if gt["track_id"] in used_gt or pred["track_id"] in used_pred:
            continue
        used_gt.add(gt["track_id"])
        used_pred.add(pred["track_id"])
        matches.append((gt, pred, score))
    return matches


def evaluate(ground_truth: dict[int, list[dict]], predictions: dict[int, list[dict]], iou_threshold: float) -> dict:
    total_gt = 0
    matches_count = 0
    false_positives = 0
    misses = 0
    id_switches = 0
    ious: list[float] = []
    gt_to_pred_history: dict[str, str] = {}

    for frame in sorted(set(ground_truth) | set(predictions)):
        gt_items = ground_truth.get(frame, [])
        pred_items = predictions.get(frame, [])
        total_gt += len(gt_items)
        matches = greedy_match(gt_items, pred_items, iou_threshold)
        matches_count += len(matches)
        false_positives += len(pred_items) - len(matches)
        misses += len(gt_items) - len(matches)
        for gt, pred, score in matches:
            previous_pred_id = gt_to_pred_history.get(gt["track_id"])
            if previous_pred_id is not None and previous_pred_id != pred["track_id"]:
                id_switches += 1
            gt_to_pred_history[gt["track_id"]] = pred["track_id"]
            ious.append(score)

    mota = 1.0 - ((misses + false_positives + id_switches) / total_gt) if total_gt else 0.0
    precision = matches_count / (matches_count + false_positives) if matches_count + false_positives else 0.0
    recall = matches_count / total_gt if total_gt else 0.0
    return {
        "frames": len(set(ground_truth) | set(predictions)),
        "ground_truth_objects": total_gt,
        "matches": matches_count,
        "false_positives": false_positives,
        "misses": misses,
        "id_switches": id_switches,
        "mota": mota,
        "precision": precision,
        "recall": recall,
        "mean_iou": sum(ious) / len(ious) if ious else 0.0,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate tracker output against ground-truth boxes.")
    parser.add_argument("--ground-truth", type=Path, required=True, help="CSV: frame,track_id,x,y,w,h")
    parser.add_argument("--predictions", type=Path, required=True, help="CSV: frame,track_id,x,y,w,h")
    parser.add_argument("--tracker-name", default="tracker")
    parser.add_argument("--iou", type=float, default=0.5)
    parser.add_argument("--output", type=Path, default=Path("benchmark_results"))
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    result = evaluate(read_tracks(args.ground_truth), read_tracks(args.predictions), args.iou)
    payload = {"tracker": args.tracker_name, "iou_threshold": args.iou, "metrics": result}
    write_json(args.output / f"tracking_{args.tracker_name}.json", payload)
    print(payload)

