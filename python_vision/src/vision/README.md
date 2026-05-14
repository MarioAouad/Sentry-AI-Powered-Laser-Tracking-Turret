# Vision Module

Detection and tracking code used by the runtime pipeline.

## Files

- `target_tracker.py`: YOLO pose tracking, ByteTrack persistence, and target point extraction.
- `cascade_detector.py`: optional HOG/SVM wake-up detector.

## Output

`TargetTracker.track()` returns a `TrackerResult` containing:

- detection state
- track ID
- target pixel
- bounding box
- shoulder points for depth estimation
- full COCO keypoints for annotation

The orchestrator feeds this result into filtering, depth estimation, spatial calibration, and inverse kinematics.
