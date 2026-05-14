# API Module

FastAPI integration layer for the dashboard.

## Files

- `api_server.py`: REST routes, MJPEG streaming, and WebSocket route registration.
- `websocket_manager.py`: connection tracking and telemetry broadcast helper.

## Runtime Endpoints

- `GET /health`: backend status.
- `GET /video-feed`: MJPEG stream of the latest annotated frame.
- `POST /target-mode`: set target mode to `head` or `chest`.
- `POST /system-control`: start, stop, or calibration command hook.
- `WS /ws/telemetry`: dashboard telemetry stream.

The API reads shared state from `APISharedState`, which is updated by `main_orchestrator.py`.
