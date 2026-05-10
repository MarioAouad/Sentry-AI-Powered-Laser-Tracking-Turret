from __future__ import annotations

import argparse
import csv
import importlib
import json
import statistics
import time
from pathlib import Path
from typing import Any

from config import (
    DEFAULT_CONF_THRESHOLD,
    DEFAULT_DEVICE,
    DEFAULT_IMAGES_DIR,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_SAMPLE_RATE,
    DEFAULT_YOLO_MODEL,
    YOLO_POSE_MODELS,
)


def require_module(module_name: str, install_hint: str):
    try:
        return importlib.import_module(module_name)
    except ImportError as exc:
        raise SystemExit(f"Missing dependency '{module_name}'. Install it with: {install_hint}") from exc


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


def mean(values: list[float]) -> float:
    filtered = [value for value in values if value is not None]
    return statistics.fmean(filtered) if filtered else 0.0


def median(values: list[float]) -> float:
    filtered = [value for value in values if value is not None]
    return statistics.median(filtered) if filtered else 0.0


def safe_min(values: list[float]) -> float:
    filtered = [value for value in values if value is not None]
    return min(filtered) if filtered else 0.0


def safe_max(values: list[float]) -> float:
    filtered = [value for value in values if value is not None]
    return max(filtered) if filtered else 0.0


def resolve_device(requested: str) -> str:
    if requested != "auto":
        return requested
    try:
        torch = importlib.import_module("torch")
        return "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:
        return "cpu"


def gpu_vram_used_mb() -> float | None:
    try:
        torch = importlib.import_module("torch")
        if torch.cuda.is_available():
            return float(torch.cuda.memory_allocated() / (1024 * 1024))
    except ImportError:
        pass
    try:
        GPUtil = importlib.import_module("GPUtil")
        gpus = GPUtil.getGPUs()
        return float(gpus[0].memoryUsed) if gpus else None
    except ImportError:
        return None


def cpu_ram_used_mb() -> float:
    psutil = require_module("psutil", "pip install psutil")
    process = psutil.Process()
    return float(process.memory_info().rss / (1024 * 1024))


def frame_brightness(cv2, frame) -> float:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return float(gray.mean())


def collect_frames(args: argparse.Namespace) -> tuple[list[tuple[int, float, Any]], str]:
    cv2 = require_module("cv2", "pip install opencv-python")
    images_dir = Path(args.images_dir)
    if not images_dir.exists() or not images_dir.is_dir():
        raise SystemExit(f"Images folder not found or is not a directory: {images_dir}")

    frames: list[tuple[int, float, Any]] = []
    image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    image_paths = sorted([p for p in images_dir.iterdir() if p.suffix.lower() in image_extensions])

    if not image_paths:
        raise SystemExit(f"No images found in: {images_dir}")

    source_fps = 30.0
    for frame_index, img_path in enumerate(image_paths):
        if frame_index % args.sample_rate == 0:
            frame = cv2.imread(str(img_path))
            if frame is not None:
                timestamp = frame_index / source_fps
                frames.append((frame_index, timestamp, frame))
            else:
                print(f"Warning: Could not read {img_path}")
                
    return frames, str(images_dir)


def benchmark_yolo(
    args: argparse.Namespace,
    frames: list[tuple[int, float, Any]],
    device: str,
    model_key: str,
    model_path: str,
) -> tuple[list[dict], dict[str, Any]]:
    ultralytics = require_module("ultralytics", "pip install ultralytics")
    cv2 = require_module("cv2", "pip install opencv-python")
    model = ultralytics.YOLO(model_path)
    rows: list[dict[str, Any]] = []

    for frame_index, timestamp, frame in frames:
        start = time.perf_counter()
        results = model.predict(frame, conf=args.conf_threshold, device=device, verbose=False)
        total_ms = (time.perf_counter() - start) * 1000.0
        result = results[0] if results else None
        speed = getattr(result, "speed", {}) if result is not None else {}
        preprocess_ms = float(speed.get("preprocess", 0.0) or 0.0)
        inference_ms = float(speed.get("inference", 0.0) or 0.0)
        postprocess_ms = float(speed.get("postprocess", 0.0) or 0.0)

        confidences = []
        if result is not None and result.boxes is not None and result.boxes.conf is not None:
            confidences = [float(value) for value in result.boxes.conf.cpu().tolist()]

        rows.append(
            {
                "frame_index": frame_index,
                "timestamp_sec": round(timestamp, 4),
                "model_name": model_key,
                "total_latency_ms": total_ms,
                "preprocess_ms": preprocess_ms,
                "inference_ms": inference_ms,
                "postprocess_ms": postprocess_ms,
                "fps": 1000.0 / total_ms if total_ms > 0 else 0.0,
                "num_people_detected": len(confidences),
                "mean_confidence": mean(confidences),
                "max_confidence": safe_max(confidences),
                "frame_brightness": frame_brightness(cv2, frame),
                "gpu_vram_used_mb": gpu_vram_used_mb(),
                "cpu_ram_used_mb": cpu_ram_used_mb(),
            }
        )

    return rows, summarize_hardware_rows(rows, model_path, device, memory_key="gpu_vram_used_mb")


def benchmark_mediapipe(args: argparse.Namespace, frames: list[tuple[int, float, Any]]) -> tuple[list[dict], dict[str, Any]]:
    cv2 = require_module("cv2", "pip install opencv-python")
    mediapipe = require_module("mediapipe", "pip install mediapipe")
    pose = mediapipe.solutions.pose.Pose(model_complexity=1, min_detection_confidence=args.conf_threshold)
    rows: list[dict[str, Any]] = []

    for frame_index, timestamp, frame in frames:
        preprocess_start = time.perf_counter()
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        preprocess_ms = (time.perf_counter() - preprocess_start) * 1000.0

        inference_start = time.perf_counter()
        result = pose.process(rgb)
        inference_ms = (time.perf_counter() - inference_start) * 1000.0

        post_start = time.perf_counter()
        confidences: list[float] = []
        num_people = 0
        if result.pose_landmarks:
            num_people = 1
            confidences = [float(landmark.visibility) for landmark in result.pose_landmarks.landmark]
        postprocess_ms = (time.perf_counter() - post_start) * 1000.0
        total_ms = preprocess_ms + inference_ms + postprocess_ms

        rows.append(
            {
                "frame_index": frame_index,
                "timestamp_sec": round(timestamp, 4),
                "model_name": "mediapipe",
                "total_latency_ms": total_ms,
                "preprocess_ms": preprocess_ms,
                "inference_ms": inference_ms,
                "postprocess_ms": postprocess_ms,
                "fps": 1000.0 / total_ms if total_ms > 0 else 0.0,
                "num_people_detected": num_people,
                "mean_confidence": mean(confidences),
                "max_confidence": safe_max(confidences),
                "frame_brightness": frame_brightness(cv2, frame),
                "gpu_vram_used_mb": None,
                "cpu_ram_used_mb": cpu_ram_used_mb(),
            }
        )

    pose.close()
    return rows, summarize_hardware_rows(rows, "MediaPipe BlazePose", "CPU", memory_key="cpu_ram_used_mb")


def summarize_hardware_rows(rows: list[dict[str, Any]], model_name: str, device: str, memory_key: str) -> dict[str, Any]:
    confidences = [float(row["mean_confidence"]) for row in rows if row["mean_confidence"] is not None]
    memory_values = [float(row[memory_key]) for row in rows if row.get(memory_key) is not None]
    report = {
        "model_name": model_name,
        "device": device,
        "fps_mean": mean([float(row["fps"]) for row in rows]),
        "fps_median": median([float(row["fps"]) for row in rows]),
        "latency_ms_mean": mean([float(row["total_latency_ms"]) for row in rows]),
        "preprocess_ms_mean": mean([float(row["preprocess_ms"]) for row in rows]),
        "inference_ms_mean": mean([float(row["inference_ms"]) for row in rows]),
        "postprocess_ms_mean": mean([float(row["postprocess_ms"]) for row in rows]),
        "confidence_mean": mean(confidences),
        "confidence_min": safe_min(confidences),
        "confidence_max": safe_max(confidences),
    }
    if memory_key == "gpu_vram_used_mb":
        report["vram_mb_mean"] = mean(memory_values)
        report["vram_mb_max"] = safe_max(memory_values)
    else:
        report["cpu_ram_mb_mean"] = mean(memory_values)
        report["cpu_ram_mb_max"] = safe_max(memory_values)
    return report


def maybe_plot(output_dir: Path, rows: list[dict[str, Any]]) -> None:
    try:
        plt = importlib.import_module("matplotlib.pyplot")
    except ImportError:
        return

    by_model: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_model.setdefault(row["model_name"], []).append(row)

    for metric, filename, ylabel in [
        ("mean_confidence", "confidence_plot.png", "Mean confidence"),
        ("total_latency_ms", "latency_plot.png", "Latency ms"),
    ]:
        plt.figure()
        for model_name, model_rows in by_model.items():
            plt.plot([row["frame_index"] for row in model_rows], [row[metric] for row in model_rows], label=model_name)
        plt.xlabel("Frame")
        plt.ylabel(ylabel)
        plt.legend()
        plt.tight_layout()
        plt.savefig(output_dir / filename)
        plt.close()


def print_summary(report: dict[str, Any]) -> None:
    print("\nHardware & Environment Vision Benchmark Summary")
    print("-----------------------------------------------")
    for model_key, model_report in report["models"].items():
        print(
            f"{model_key}: FPS={model_report['fps_mean']:.2f}, "
            f"latency={model_report['latency_ms_mean']:.2f} ms, "
            f"confidence={model_report['confidence_min']:.3f}-{model_report['confidence_max']:.3f}"
        )
        if "vram_mb_mean" in model_report:
            print(f"  VRAM: mean={model_report['vram_mb_mean']:.2f} MB, max={model_report['vram_mb_max']:.2f} MB")
        if "cpu_ram_mb_mean" in model_report:
            print(f"  RAM: mean={model_report['cpu_ram_mb_mean']:.2f} MB, max={model_report['cpu_ram_mb_max']:.2f} MB")
    print(
        f"Winners: FPS={report['domain_shift_summary']['winner_fps']}, "
        f"stability={report['domain_shift_summary']['winner_stability']}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark real image inference performance and robustness.")
    parser.add_argument("--images-dir", type=Path, default=DEFAULT_IMAGES_DIR, help="Path to images directory.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--yolo-model",
        default=DEFAULT_YOLO_MODEL,
        help="Use 'all' for YOLOv8/YOLO11 nano, small, and medium, a named variant like yolov8n, or a .pt path.",
    )
    parser.add_argument("--device", default=DEFAULT_DEVICE)
    parser.add_argument("--conf-threshold", type=float, default=DEFAULT_CONF_THRESHOLD)
    parser.add_argument("--sample-rate", type=int, default=DEFAULT_SAMPLE_RATE, help="Evaluate every N frames.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_dir = ensure_output_dir(args.output / f"run_{timestamp}")
    
    device = resolve_device(args.device)
    frames, source = collect_frames(args)
    if not frames:
        raise SystemExit("No frames were available for benchmarking.")

    all_rows: list[dict[str, Any]] = []
    models: dict[str, dict[str, Any]] = {}
    for model_key, model_path in selected_yolo_models(args.yolo_model).items():
        print(f"\nRunning hardware benchmark for {model_key} ({model_path})")
        yolo_rows, yolo_report = benchmark_yolo(args, frames, device, model_key, model_path)
        all_rows.extend(yolo_rows)
        models[model_key] = yolo_report

    print("\nRunning hardware benchmark for mediapipe")
    mediapipe_rows, mediapipe_report = benchmark_mediapipe(args, frames)
    all_rows.extend(mediapipe_rows)
    models["mediapipe"] = mediapipe_report

    winner_fps = max(models, key=lambda name: models[name]["fps_mean"])
    winner_stability = min(
        models,
        key=lambda name: models[name]["confidence_max"] - models[name]["confidence_min"],
    )

    report = {
        "benchmark": "hardware_environment_custom_video",
        "video": source,
        "models": models,
        "domain_shift_summary": {
            "confidence_degradation_notes": [
                "Per-frame confidence and frame brightness are logged for later lighting/domain-shift analysis."
            ],
            "hardware_bottleneck_notes": [
                "YOLO postprocess_ms uses Ultralytics result.speed values when available.",
                "MediaPipe has no NMS stage; postprocess_ms measures landmark extraction bookkeeping only.",
            ],
            "winner_fps": winner_fps,
            "winner_stability": winner_stability,
        },
    }

    write_csv(output_dir / "benchmark_vision_hardware_per_frame.csv", all_rows)
    write_json(output_dir / "benchmark_vision_hardware_report.json", report)
    maybe_plot(output_dir, all_rows)
    print_summary(report)


if __name__ == "__main__":
    main()
