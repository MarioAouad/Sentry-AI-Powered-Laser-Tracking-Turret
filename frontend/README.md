# Frontend Dashboard

Vite + React dashboard for monitoring and controlling the Sentry turret.

## Responsibilities

- Connect to the Python backend WebSocket at `/ws/telemetry`.
- Display system state, FPS, confidence, servo angles, and target mode.
- Show the MJPEG live camera stream from `/video-feed`.
- Draw the green virtual laser overlay directly over the live feed using telemetry `debug.vlaserPx`.
- Let the operator switch target mode between `head` and `chest`.

## Setup

```powershell
npm install
```

## Development

```powershell
npm run dev
```

Open `http://localhost:5173`.

By default the dashboard expects the backend at `http://localhost:8000`. To override it, create a local `.env` file:

```text
VITE_API_URL=http://localhost:8000
```

## Validation

```powershell
npm run lint
npm run build
```

## Main Files

- `src/pages/Dashboard.jsx`: page layout.
- `src/components/LiveFeed.jsx`: MJPEG stream and virtual laser overlay.
- `src/components/ControlPanel.jsx`: body target selector.
- `src/components/StatusCards.jsx`: telemetry summary.
- `src/components/ServoPanel.jsx`: pan/tilt readout.
- `src/hooks/useSystemstate.js`: backend API and WebSocket state hook.
