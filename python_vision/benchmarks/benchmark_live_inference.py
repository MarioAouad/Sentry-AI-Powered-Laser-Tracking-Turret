from __future__ import annotations

import argparse
import importlib
from pathlib import Path

from common import (
    YOLO_POSE_MODELS,
    Timer,
    resolve_yolo_model_path,
    stats_to_dict,
    summarize_latency,
    write_csv,
    write_json,
)


def benchmark_name(args: argparse.Namespace) -> str:
    return args.yolo_variant if args.model == "yolo" else args.model


def load_model(model_name: str, yolo_variant: str, model_path: str | None):
    if model_name == "yolo":
        try:
            ultralytics = importlib.import_module("ultralytics")
        except ImportError as exc:
            raise SystemExit("Install ultralytics to run YOLO live benchmarks: pip install ultralytics") from exc
        return ultralytics.YOLO(resolve_yolo_model_path(yolo_variant, model_path))
    if model_name == "mediapipe":
        try:
            mediapipe = importlib.import_module("mediapipe")
        except ImportError as exc:
            raise SystemExit("Install mediapipe to run BlazePose benchmarks: pip install mediapipe") from exc
        return mediapipe.solutions.pose.Pose(model_complexity=1, min_detection_confidence=0.5)
    raise ValueError(f"Unsupported model: {model_name}")


def infer(model_name: str, model, frame):
    if model_name == "yolo":
        results = model.predict(frame, verbose=False)
        if not results or results[0].keypoints is None:
            return None
        boxes = results[0].boxes
        if boxes is None or boxes.conf is None or len(boxes.conf) == 0:
            return None
        return float(boxes.conf.max().item())

    cv2 = importlib.import_module("cv2")

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = model.process(rgb)
    if not result.pose_landmarks:
        return None
    confidences = [lm.visibility for lm in result.pose_landmarks.landmark]
    return float(sum(confidences) / len(confidences))


def run(args: argparse.Namespace) -> dict:
    try:
        cv2 = importlib.import_module("cv2")
    except ImportError as exc:
        raise SystemExit("Install opencv-python to run live benchmarks: pip install opencv-python") from exc

    source: int | str = args.source
    if isinstance(source, str) and source.isdigit():
        source = int(source)
    capture = cv2.VideoCapture(source)
    if not capture.isOpened():
        raise SystemExit(f"Could not open video source: {args.source}")

    model = load_model(args.model, args.yolo_variant, args.model_path)
    latencies: list[float] = []
    confidences: list[float] = []
    rows: list[dict] = []
    frame_index = 0

    while frame_index < args.frames:
        ok, frame = capture.read()
        if not ok:
            break
        if frame_index < args.warmup:
            infer(args.model, model, frame)
            frame_index += 1
            continue

        with Timer() as timer:
            confidence = infer(args.model, model, frame)
        latencies.append(timer.elapsed_ms)
        if confidence is not None:
            confidences.append(confidence)
        rows.append(
            {
                "frame": frame_index,
                "latency_ms": round(timer.elapsed_ms, 4),
                "confidence": None if confidence is None else round(confidence, 6),
            }
        )
        frame_index += 1

    capture.release()
    stats = summarize_latency(latencies, confidences)
    name = benchmark_name(args)
    payload = {
        "model": name,
        "model_type": args.model,
        "model_path": resolve_yolo_model_path(args.yolo_variant, args.model_path)
        if args.model == "yolo"
        else None,
        "source": str(args.source),
        "stats": stats_to_dict(stats),
    }
    write_json(args.output / f"live_{name}_summary.json", payload)
    write_csv(args.output / f"live_{name}_frames.csv", rows)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark live webcam/video inference FPS, latency, and confidence.")
    parser.add_argument("--model", choices=("yolo", "mediapipe"), required=True)
    parser.add_argument(
        "--yolo-variant",
        choices=tuple(YOLO_POSE_MODELS.keys()),
        default="yolov8n",
        help="Named YOLO pose model to use when --model yolo.",
    )
    parser.add_argument("--model-path", help="Custom YOLO pose model path. Overrides --yolo-variant.")
    parser.add_argument("--source", default="0", help="Webcam index, video file, or stream URL.")
    parser.add_argument("--frames", type=int, default=300)
    parser.add_argument("--warmup", type=int, default=20)
    parser.add_argument("--output", type=Path, default=Path("benchmark_results"))
    return parser.parse_args()


if __name__ == "__main__":
    print(run(parse_args()))
