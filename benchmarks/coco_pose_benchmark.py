import argparse
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
from pycocotools.coco import COCO
from pycocotools.cocoeval import COCOeval


def load_predictions(prediction_path):
    """
    Expected prediction format:
    [
        {
            "image_id": 123,
            "category_id": 1,
            "keypoints": [x1, y1, v1, x2, y2, v2, ...],
            "score": 0.91
        }
    ]

    COCO-Pose uses 17 keypoints.
    Each prediction must have 17 * 3 = 51 keypoint values.
    """
    with open(prediction_path, "r") as f:
        predictions = json.load(f)

    if not isinstance(predictions, list):
        raise ValueError("Predictions file must contain a list of prediction dictionaries.")

    for pred in predictions:
        required_keys = ["image_id", "category_id", "keypoints", "score"]
        for key in required_keys:
            if key not in pred:
                raise ValueError(f"Missing key '{key}' in prediction: {pred}")

        if pred["category_id"] != 1:
            raise ValueError("For COCO-Pose, category_id should be 1 for person.")

        if len(pred["keypoints"]) != 51:
            raise ValueError(
                f"Each prediction must contain 51 keypoint values, got {len(pred['keypoints'])}."
            )

    return predictions


def evaluate_coco_pose(annotation_path, prediction_path, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    coco_gt = COCO(annotation_path)
    predictions = load_predictions(prediction_path)

    coco_dt = coco_gt.loadRes(predictions)

    coco_eval = COCOeval(coco_gt, coco_dt, iouType="keypoints")
    coco_eval.evaluate()
    coco_eval.accumulate()
    coco_eval.summarize()

    stats = coco_eval.stats

    results = {
        "mAP": float(stats[0]),
        "mAP_50": float(stats[1]),
        "mAP_75": float(stats[2]),
        "mAP_medium": float(stats[3]),
        "mAP_large": float(stats[4]),
        "mAR": float(stats[5]),
        "mAR_50": float(stats[6]),
        "mAR_75": float(stats[7]),
        "mAR_medium": float(stats[8]),
        "mAR_large": float(stats[9]),
    }

    precision, recall, f1_score = approximate_precision_recall_f1(coco_eval)

    results["precision"] = precision
    results["recall"] = recall
    results["f1_score"] = f1_score

    json_path = output_dir / "coco_pose_results.json"
    csv_path = output_dir / "coco_pose_results.csv"

    with open(json_path, "w") as f:
        json.dump(results, f, indent=4)

    pd.DataFrame([results]).to_csv(csv_path, index=False)

    print("\nFinal Benchmark Results")
    print("-----------------------")
    for key, value in results.items():
        print(f"{key}: {value:.4f}")

    print(f"\nSaved JSON results to: {json_path}")
    print(f"Saved CSV results to: {csv_path}")

    return results


def approximate_precision_recall_f1(coco_eval):
    """
    COCO officially reports AP and AR, not simple Precision/Recall/F1.

    This function extracts an approximate overall precision and recall
    from COCOeval tensors so the benchmark can still report:
    Precision, Recall, F1-Score, and mAP.

    precision tensor shape:
    [IoU thresholds, recall thresholds, categories, area ranges, max detections]

    recall tensor shape:
    [IoU thresholds, categories, area ranges, max detections]
    """

    precision_tensor = coco_eval.eval["precision"]
    recall_tensor = coco_eval.eval["recall"]

    valid_precision = precision_tensor[precision_tensor > -1]
    valid_recall = recall_tensor[recall_tensor > -1]

    precision = float(np.mean(valid_precision)) if valid_precision.size > 0 else 0.0
    recall = float(np.mean(valid_recall)) if valid_recall.size > 0 else 0.0

    if precision + recall == 0:
        f1_score = 0.0
    else:
        f1_score = 2 * (precision * recall) / (precision + recall)

    return precision, recall, f1_score


def main():
    parser = argparse.ArgumentParser(
        description="Phase 1 COCO-Pose benchmark for pose-estimation model accuracy."
    )

    parser.add_argument(
        "--annotations",
        required=True,
        help="Path to COCO keypoints annotation JSON file."
    )

    parser.add_argument(
        "--predictions",
        required=True,
        help="Path to model predictions in COCO keypoints JSON format."
    )

    parser.add_argument(
        "--output-dir",
        default="benchmark_results/coco_pose_phase1",
        help="Directory where benchmark results will be saved."
    )

    args = parser.parse_args()

    evaluate_coco_pose(
        annotation_path=args.annotations,
        prediction_path=args.predictions,
        output_dir=args.output_dir
    )


if __name__ == "__main__":
    main()