# Sentry AI-Powered Laser Tracking Turret

An AI-assisted pan/tilt turret that detects a human target from a live camera feed, estimates a target body point, converts the pixel location into servo angles, and drives a laser payload through an ESP32-controlled actuator.

The project is split into three main parts:

- `python_vision/`: real-time camera capture, pose tracking, depth estimation, kinematics, telemetry, and MJPEG streaming.
- `frontend/`: React dashboard for the live feed, system telemetry, target mode selection, and virtual laser overlay.
- `arduino_firmware/`: ESP32 firmware for serial command parsing, servo movement, and laser/status LED control.

## Current Flow

1. The Python process captures frames from the configured webcam.
2. YOLO pose tracking selects the configured target point, currently `head` or `chest`.
3. The kinematics pipeline estimates depth, transforms camera pixels into turret-space coordinates, and computes pan/tilt servo angles.
4. The Python API streams annotated MJPEG video and WebSocket telemetry to the frontend.
5. The frontend draws the green virtual laser overlay directly on the live feed.
6. The Python serial tether sends `pan,tilt,state` commands to the ESP32.
7. The ESP32 applies servo commands and toggles the laser/status payload.

## Repository Layout

```text
.
├── arduino_firmware/       ESP32 firmware and hardware pin configuration
├── frontend/               Vite + React dashboard
├── python_vision/          Python vision, API, calibration, and benchmarks
├── Computer_Vision_Pipeline.png
└── AI Lazer Sentry Turret Detaills.pdf
```

## Quick Start

Install and run each part from its own folder:

```powershell
cd python_vision
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python main_orchestrator.py
```

```powershell
cd frontend
npm install
npm run dev
```

Open the dashboard at `http://localhost:5173`.

For the ESP32 firmware, open `arduino_firmware/TurretNode/TurretNode.ino` in the Arduino IDE and flash it after checking `Config.h`.

## Required Local Setup

- Python 3.10 is recommended for the vision stack.
- Node.js 20+ is recommended for the frontend.
- The YOLO pose weights are intentionally ignored by Git. Place `yolo11m-pose.pt` under `python_vision/models/`.
- Update `python_vision/config/hardware_offsets.yaml` for camera index, frame size, servo trim, turret offset, and serial port.
- The ESP32 serial baud rate must match both `python_vision/config/hardware_offsets.yaml` and `arduino_firmware/TurretNode/Config.h`.

## Validation Commands

```powershell
cd frontend
npm run lint
npm run build
```

```powershell
python -m py_compile python_vision\main_orchestrator.py python_vision\pre_deployment_calibration.py python_vision\src\api\api_server.py python_vision\src\vision\target_tracker.py
```

## Documentation

- `python_vision/README.md`: vision/API setup and operating notes.
- `frontend/README.md`: dashboard setup and UI responsibilities.
- `arduino_firmware/README.md`: ESP32 firmware setup and serial command contract.
- `python_vision/benchmarks/*/README.md`: benchmark-specific notes.
