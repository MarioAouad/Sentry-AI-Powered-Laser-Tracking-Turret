from __future__ import annotations

import argparse
import csv
import importlib
import json
import math
import statistics
import time
from pathlib import Path
from typing import Any

from config import (
    COCO_OKS_SIGMAS,
    DEFAULT_ANNOTATIONS,
    DEFAULT_CONF_THRESHOLD,
    DEFAULT_DEVICE,
    DEFAULT_IMAGE_LIMIT,
    DEFAULT_IMAGES_DIR,
    DEFAULT_OKS_THRESHOLD,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_PCK_THRESHOLD,
    DEFAULT_YOLO_MODEL,
    MEDIAPIPE_TO_COCO,
    YOLO_POSE_MODELS,
)

COCO_KEYPOINTS = 17


def require_module(module_name: str, install_hint: str):
    try:
        return importlib.import_module(module_name)
    except ImportError as exc:
        raise SystemExit(f"Missing dependency '{module_name}'. Install it with: {install_hint}") from exc


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


def selected_yolo_models(model_arg: str) -> dict[str, str]:
    if model_arg == "all":
        return YOLO_POSE_MODELS
    if model_arg in YOLO_POSE_MODELS:
        return {model_arg: YOLO_POSE_MODELS[model_arg]}
    model_key = Path(model_arg).stem.replace("-pose", "")
    return {model_key: model_arg}


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


def flatten_keypoints(keypoints: list[list[float]]) -> list[float]:
    flat: list[float] = []
    for point in keypoints[:COCO_KEYPOINTS]:
        x, y, visibility = point
        flat.extend([float(x), float(y), float(visibility)])
    while len(flat) < COCO_KEYPOINTS * 3:
        flat.extend([0.0, 0.0, 0.0])
    return flat


def unflatten_keypoints(flat: list[float]) -> list[list[float]]:
    return [flat[idx : idx + 3] for idx in range(0, min(len(flat), COCO_KEYPOINTS * 3), 3)]


def load_selected_coco_data(annotation_path: Path, limit: int) -> tuple[dict[str, Any], list[dict], dict[int, list[dict]]]:
    data = json.loads(annotation_path.read_text(encoding="utf-8"))
    selected_images = data["images"][:limit]
    selected_image_ids = {int(image["id"]) for image in selected_images}

    grouped_annotations: dict[int, list[dict]] = {int(image["id"]): [] for image in selected_images}
    selected_annotations = []
    for ann in data["annotations"]:
        if int(ann["image_id"]) not in selected_image_ids:
            continue
        if ann.get("iscrowd", 0) or ann.get("num_keypoints", 0) <= 0:
            continue
        grouped_annotations[int(ann["image_id"])].append(ann)
        selected_annotations.append(ann)

    subset = {
        "info": data.get("info", {}),
        "licenses": data.get("licenses", []),
        "images": selected_images,
        "annotations": selected_annotations,
        "categories": data["categories"],
    }
    return subset, selected_images, grouped_annotations


def coco_oks(pred_keypoints: list[list[float]], gt_keypoints: list[list[float]], area: float) -> float:
    if area <= 0:
        return 0.0
    scores: list[float] = []
    for idx in range(COCO_KEYPOINTS):
        gx, gy, gv = gt_keypoints[idx]
        if gv <= 0:
            continue
        px, py, pv = pred_keypoints[idx]
        if pv <= 0:
            continue
        dx = px - gx
        dy = py - gy
        sigma = COCO_OKS_SIGMAS[idx] / 10.0
        scores.append(math.exp(-((dx * dx + dy * dy) / (2 * area * sigma * sigma))))
    return statistics.fmean(scores) if scores else 0.0


def pck_score(pred_keypoints: list[list[float]], gt_keypoints: list[list[float]], bbox: list[float], threshold: float) -> float:
    # PCK is the fraction of visible ground-truth keypoints predicted within a
    # normalized distance. Here the normalization reference is person bbox size.
    _, _, width, height = bbox
    reference = max(width, height, 1.0)
    correct = 0
    total = 0
    for idx in range(COCO_KEYPOINTS):
        gx, gy, gv = gt_keypoints[idx]
        if gv <= 0:
            continue
        px, py, pv = pred_keypoints[idx]
        if pv <= 0:
            total += 1
            continue
        distance = math.hypot(px - gx, py - gy)
        total += 1
        if distance <= threshold * reference:
            correct += 1
    return correct / total if total else 0.0


def greedy_match_predictions(
    predictions_by_image: dict[int, list[dict]],
    grouped_annotations: dict[int, list[dict]],
    oks_threshold: float,
    pck_threshold: float,
) -> dict[str, Any]:
    tp = fp = fn = 0
    matched_oks: list[float] = []
    matched_pck: list[float] = []

    for image_id, gt_people in grouped_annotations.items():
        predictions = predictions_by_image.get(image_id, [])
        candidates: list[tuple[float, int, int]] = []

        for pred_idx, pred in enumerate(predictions):
            pred_points = unflatten_keypoints(pred["keypoints"])
            for gt_idx, gt in enumerate(gt_people):
                gt_points = unflatten_keypoints(gt["keypoints"])
                oks = coco_oks(pred_points, gt_points, float(gt.get("area") or gt["bbox"][2] * gt["bbox"][3]))
                candidates.append((oks, pred_idx, gt_idx))

        used_predictions: set[int] = set()
        used_ground_truth: set[int] = set()
        for oks, pred_idx, gt_idx in sorted(candidates, reverse=True):
            if oks < oks_threshold:
                continue
            if pred_idx in used_predictions or gt_idx in used_ground_truth:
                continue
            used_predictions.add(pred_idx)
            used_ground_truth.add(gt_idx)
            gt = gt_people[gt_idx]
            pred_points = unflatten_keypoints(predictions[pred_idx]["keypoints"])
            gt_points = unflatten_keypoints(gt["keypoints"])
            matched_oks.append(oks)
            matched_pck.append(pck_score(pred_points, gt_points, gt["bbox"], pck_threshold))

        tp += len(used_predictions)
        fp += len(predictions) - len(used_predictions)
        fn += len(gt_people) - len(used_ground_truth)

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0
    return {
        "matching": {
            "oks_threshold": oks_threshold,
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        },
        "pose": {
            "mean_oks": statistics.fmean(matched_oks) if matched_oks else 0.0,
            "pck": statistics.fmean(matched_pck) if matched_pck else 0.0,
        },
    }


def run_coco_eval(annotation_subset: dict[str, Any], predictions: list[dict], output_dir: Path, model_name: str) -> dict[str, float]:
    if not predictions:
        return {"mAP": 0.0, "AP50": 0.0, "AP75": 0.0, "AR": 0.0}

    coco_mod = require_module("pycocotools.coco", "pip install pycocotools")
    cocoeval_mod = require_module("pycocotools.cocoeval", "pip install pycocotools")

    subset_path = output_dir / f"_coco_subset_{model_name}.json"
    write_json(subset_path, annotation_subset)

    coco_gt = coco_mod.COCO(str(subset_path))
    coco_dt = coco_gt.loadRes(predictions)
    evaluator = cocoeval_mod.COCOeval(coco_gt, coco_dt, iouType="keypoints")
    evaluator.evaluate()
    evaluator.accumulate()
    evaluator.summarize()

    return {
        "mAP": float(evaluator.stats[0]),
        "AP50": float(evaluator.stats[1]),
        "AP75": float(evaluator.stats[2]),
        "AR": float(evaluator.stats[5]),
    }


def predict_yolo(
    args: argparse.Namespace,
    images: list[dict],
    images_dir: Path,
    model_path: str,
) -> tuple[list[dict], list[float]]:
    ultralytics = require_module("ultralytics", "pip install ultralytics")
    model = ultralytics.YOLO(model_path)
    device = resolve_device(args.device)
    predictions: list[dict] = []
    latencies: list[float] = []

    for image in images:
        image_path = images_dir / image["file_name"]
        if not image_path.exists():
            print(f"Warning: missing image skipped: {image_path}")
            continue

        start = time.perf_counter()
        results = model.predict(str(image_path), conf=args.conf_threshold, device=device, verbose=False)
        latencies.append((time.perf_counter() - start) * 1000.0)
        if not results:
            continue

        result = results[0]
        if result.keypoints is None or result.boxes is None:
            continue

        keypoints_xy = result.keypoints.xy.cpu().tolist()
        boxes_conf = result.boxes.conf.cpu().tolist() if result.boxes.conf is not None else []
        for idx, points in enumerate(keypoints_xy):
            score = float(boxes_conf[idx]) if idx < len(boxes_conf) else 0.0
            coco_points = [[float(x), float(y), 2.0] for x, y in points[:COCO_KEYPOINTS]]
            predictions.append(
                {
                    "image_id": int(image["id"]),
                    "category_id": 1,
                    "keypoints": flatten_keypoints(coco_points),
                    "score": score,
                }
            )
    return predictions, latencies


def predict_mediapipe(args: argparse.Namespace, images: list[dict], images_dir: Path) -> tuple[list[dict], list[float]]:
    cv2 = require_module("cv2", "pip install opencv-python")
    mediapipe = require_module("mediapipe", "pip install mediapipe")

    pose = mediapipe.solutions.pose.Pose(static_image_mode=True, model_complexity=2, min_detection_confidence=args.conf_threshold)
    predictions: list[dict] = []
    latencies: list[float] = []

    for image in images:
        image_path = images_dir / image["file_name"]
        if not image_path.exists():
            print(f"Warning: missing image skipped: {image_path}")
            continue
        frame = cv2.imread(str(image_path))
        if frame is None:
            print(f"Warning: unreadable image skipped: {image_path}")
            continue

        height, width = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        start = time.perf_counter()
        result = pose.process(rgb)
        latencies.append((time.perf_counter() - start) * 1000.0)
        if not result.pose_landmarks:
            continue

        landmarks = result.pose_landmarks.landmark
        coco_points = []
        confidences = []
        for mp_index in MEDIAPIPE_TO_COCO:
            landmark = landmarks[mp_index]
            visibility = float(getattr(landmark, "visibility", 1.0))
            confidences.append(visibility)
            coco_visibility = 2.0 if visibility >= args.conf_threshold else 1.0
            coco_points.append([landmark.x * width, landmark.y * height, coco_visibility])

        predictions.append(
            {
                "image_id": int(image["id"]),
                "category_id": 1,
                "keypoints": flatten_keypoints(coco_points),
                "score": statistics.fmean(confidences) if confidences else 0.0,
            }
        )
    pose.close()
    return predictions, latencies


def group_predictions(predictions: list[dict]) -> dict[int, list[dict]]:
    grouped: dict[int, list[dict]] = {}
    for pred in predictions:
        grouped.setdefault(int(pred["image_id"]), []).append(pred)
    return grouped


def latency_mean(latencies: list[float]) -> float:
    return statistics.fmean(latencies) if latencies else 0.0


def latency_median(latencies: list[float]) -> float:
    return statistics.median(latencies) if latencies else 0.0


def build_model_report(
    model_key: str,
    model_name: str,
    device: str,
    annotation_subset: dict[str, Any],
    predictions: list[dict],
    grouped_annotations: dict[int, list[dict]],
    latencies: list[float],
    args: argparse.Namespace,
    output_dir: Path,
) -> dict[str, Any]:
    coco_metrics = run_coco_eval(annotation_subset, predictions, output_dir, model_key)
    matched = greedy_match_predictions(group_predictions(predictions), grouped_annotations, args.oks_threshold, args.pck_threshold)
    return {
        "model_name": model_name,
        "device": device,
        "coco_metrics": coco_metrics,
        "matching_metrics": matched["matching"],
        "pose_metrics": matched["pose"],
        "latency_ms_mean": latency_mean(latencies),
        "latency_ms_median": latency_median(latencies),
    }


def winner(values: dict[str, dict[str, Any]], path: tuple[str, ...]) -> str:
    def read(model_report: dict[str, Any]) -> float:
        current: Any = model_report
        for key in path:
            current = current[key]
        return float(current)

    return max(values, key=lambda name: read(values[name]))


def print_summary(report: dict[str, Any]) -> None:
    print("\nCOCO-Pose Vision Benchmark Summary")
    print("----------------------------------")
    for model_key, model_report in report["models"].items():
        coco = model_report["coco_metrics"]
        matching = model_report["matching_metrics"]
        pose = model_report["pose_metrics"]
        print(
            f"{model_key}: mAP={coco['mAP']:.4f}, Precision={matching['precision']:.4f}, "
            f"Recall={matching['recall']:.4f}, F1={matching['f1']:.4f}, "
            f"OKS={pose['mean_oks']:.4f}, PCK={pose['pck']:.4f}"
        )
    winners = report["winner_summary"]
    print(
        f"Winners: mAP={winners['best_mAP']}, F1={winners['best_f1']}, "
        f"OKS={winners['best_OKS']}, PCK={winners['best_PCK']}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Theoretical pose benchmark on COCO-Pose validation data.")
    parser.add_argument("--images", type=Path, default=DEFAULT_IMAGES_DIR, help="Path to COCO validation images folder.")
    parser.add_argument("--annotations", type=Path, default=DEFAULT_ANNOTATIONS, help="Path to COCO person_keypoints JSON.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--limit", type=int, default=DEFAULT_IMAGE_LIMIT, help="Number of images to evaluate.")
    parser.add_argument(
        "--yolo-model",
        default=DEFAULT_YOLO_MODEL,
        help="Use 'all' for YOLOv8/YOLO11 nano, small, and medium, a named variant like yolov8n, or a .pt path.",
    )
    parser.add_argument("--oks-threshold", type=float, default=DEFAULT_OKS_THRESHOLD)
    parser.add_argument("--pck-threshold", type=float, default=DEFAULT_PCK_THRESHOLD)
    parser.add_argument("--device", default=DEFAULT_DEVICE)
    parser.add_argument("--conf-threshold", type=float, default=DEFAULT_CONF_THRESHOLD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = ensure_output_dir(args.output)
    if not args.images.exists():
        raise SystemExit(f"COCO images folder not found: {args.images}")
    if not args.annotations.exists():
        raise SystemExit(f"COCO annotations file not found: {args.annotations}")

    annotation_subset, images, grouped_annotations = load_selected_coco_data(args.annotations, args.limit)
    num_ground_truth_people = sum(len(items) for items in grouped_annotations.values())

    models: dict[str, dict[str, Any]] = {}
    for model_key, model_path in selected_yolo_models(args.yolo_model).items():
        print(f"\nRunning COCO benchmark for {model_key} ({model_path})")
        yolo_predictions, yolo_latencies = predict_yolo(args, images, args.images, model_path)
        write_json(output_dir / f"coco_predictions_{model_key}.json", yolo_predictions)
        models[model_key] = build_model_report(
            model_key,
            model_path,
            resolve_device(args.device),
            annotation_subset,
            yolo_predictions,
            grouped_annotations,
            yolo_latencies,
            args,
            output_dir,
        )

    print("\nRunning COCO benchmark for mediapipe")
    mediapipe_predictions, mediapipe_latencies = predict_mediapipe(args, images, args.images)
    write_json(output_dir / "coco_predictions_mediapipe.json", mediapipe_predictions)
    models["mediapipe"] = build_model_report(
        "mediapipe",
        "MediaPipe BlazePose",
        "CPU",
        annotation_subset,
        mediapipe_predictions,
        grouped_annotations,
        mediapipe_latencies,
        args,
        output_dir,
    )

    report = {
        "benchmark": "theoretical_accuracy_coco_pose",
        "dataset": {
            "images_dir": str(args.images),
            "annotations": str(args.annotations),
            "num_images": len(images),
            "num_ground_truth_people": num_ground_truth_people,
        },
        "models": models,
        "winner_summary": {
            "best_mAP": winner(models, ("coco_metrics", "mAP")),
            "best_f1": winner(models, ("matching_metrics", "f1")),
            "best_OKS": winner(models, ("pose_metrics", "mean_oks")),
            "best_PCK": winner(models, ("pose_metrics", "pck")),
            "notes": [
                "MediaPipe BlazePose is single-person by design in this script; this limits fairness on multi-person COCO images.",
                "Precision, recall, and F1 are computed with image-local greedy OKS matching.",
            ],
        },
    }

    write_json(output_dir / "benchmark_vision_coco_report.json", report)
    write_csv(
        output_dir / "benchmark_vision_coco_summary.csv",
        [
            {
                "model": name,
                "mAP": data["coco_metrics"]["mAP"],
                "AP50": data["coco_metrics"]["AP50"],
                "AP75": data["coco_metrics"]["AP75"],
                "AR": data["coco_metrics"]["AR"],
                "precision": data["matching_metrics"]["precision"],
                "recall": data["matching_metrics"]["recall"],
                "f1": data["matching_metrics"]["f1"],
                "mean_oks": data["pose_metrics"]["mean_oks"],
                "pck": data["pose_metrics"]["pck"],
                "latency_ms_mean": data["latency_ms_mean"],
            }
            for name, data in models.items()
        ],
    )
    print_summary(report)


if __name__ == "__main__":
    main()
