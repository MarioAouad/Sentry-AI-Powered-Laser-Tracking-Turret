# Benchmarks

Offline evaluation scripts used to compare pose models, live inference behavior, and tracker consistency.

Install benchmark dependencies from `python_vision`:

```powershell
pip install -r requirements-benchmark.txt
```

## Folders

- `live_inference_performance/`: webcam/video runtime FPS and confidence testing.
- `multi_object_tracking/`: ByteTrack and DeepSORT identity consistency evaluation.
- `pose_estimation_coco/`: COCO pose estimation accuracy evaluation.
- `custom_datasets/`: placeholder folders for local benchmark images and labels.

Generated outputs are ignored except for `.gitkeep` placeholders.
