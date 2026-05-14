# Kinematics Module

Math and filtering layer between vision pixels and servo commands.

## Files

- `signal_filter.py`: median + EMA smoothing for noisy target pixels.
- `depth_estimator.py`: approximate depth from shoulder width or bounding box fallback.
- `spatial_calibrator.py`: pixel-to-camera-space and camera-to-turret-space transforms.
- `inverse_kinematics.py`: pan/tilt angle calculation.

## Coordinate Convention

- Camera X: right.
- Camera Y: down.
- Camera Z: forward.

The turret offset and servo direction values come from `python_vision/config/hardware_offsets.yaml`.
