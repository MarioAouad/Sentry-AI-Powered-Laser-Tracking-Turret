"""
api_server.py — FastAPI Server for Frontend Integration
========================================================
Exposes a REST + WebSocket API that bridges the Python vision pipeline
to the React Vite frontend dashboard.

Endpoints:
    GET  /health           → Health check
    GET  /video-feed       → MJPEG live camera stream
    POST /target-mode      → Change targeting body part (head/chest/hand)
    POST /system-control   → Start / Stop / Calibrate the system
    WS   /ws/telemetry     → Real-time telemetry broadcast

The WebSocket telemetry payload matches the exact shape expected by
the frontend's ``mockSystemData.js``:

    {
        "systemState":  "Scanning" | "Target Detected" | "Tracking Locked" | "Reacquiring",
        "fps":          29,
        "confidence":   0.82,
        "tracker":      "ByteTrack",
        "model":        "YOLO11m-Pose",
        "yaw":          90,
        "pitch":        60,
        "indicator":    "Standby" | "Armed" | "Active",
        "targetMode":   "chest",
        "logs":         ["System initialized", ...]
    }
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from src.api.websocket_manager import WebSocketManager

logger = logging.getLogger("sentry.api.server")


# ── Request Models ───────────────────────────────────────────────────
class TargetModeRequest(BaseModel):
    mode: str  # "head", "chest", or "hand"


class SystemControlRequest(BaseModel):
    command: str  # "start", "stop", or "calibrate"


# ── Shared State (set by the orchestrator) ───────────────────────────
class APISharedState:
    """
    Thread-safe container for data that the vision loop pushes
    and the API endpoints read.  Set by the orchestrator.
    """

    def __init__(self) -> None:
        self.target_mode: str = "chest"
        self.system_running: bool = False
        self.latest_frame_jpeg: bytes | None = None
        self.on_target_mode_change: Any = None   # callback
        self.on_system_command: Any = None        # callback


# ── App Factory ──────────────────────────────────────────────────────
def create_app(
    ws_manager: WebSocketManager,
    shared_state: APISharedState,
) -> FastAPI:
    """
    Build and return the FastAPI application instance.

    Parameters
    ----------
    ws_manager : WebSocketManager
        The telemetry WebSocket broadcaster.
    shared_state : APISharedState
        Shared mutable state between the orchestrator and the API.
    """
    app = FastAPI(
        title="Sentry AI Turret API",
        version="1.0.0",
        description="Real-time vision pipeline control and telemetry",
    )

    # Allow the React frontend (Vite dev server on :5173) to connect
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Health Check ─────────────────────────────────────────────────
    @app.get("/health")
    async def health() -> JSONResponse:
        return JSONResponse({
            "status": "online",
            "system_running": shared_state.system_running,
            "target_mode": shared_state.target_mode,
            "ws_clients": ws_manager.client_count,
            "timestamp": time.time(),
        })

    # ── Target Mode ──────────────────────────────────────────────────
    @app.post("/target-mode")
    async def set_target_mode(req: TargetModeRequest) -> JSONResponse:
        if req.mode not in ("head", "chest", "hand"):
            return JSONResponse(
                {"error": f"Invalid mode '{req.mode}'. Use head, chest, or hand."},
                status_code=400,
            )
        shared_state.target_mode = req.mode
        if shared_state.on_target_mode_change:
            shared_state.on_target_mode_change(req.mode)
        logger.info("[API] Target mode changed → %s", req.mode)
        return JSONResponse({"target_mode": req.mode})

    # Quick-switch shortcuts — just visit in browser:
    #   http://localhost:8000/target/head
    #   http://localhost:8000/target/chest
    @app.get("/target/{mode}")
    async def quick_target(mode: str) -> JSONResponse:
        if mode not in ("head", "chest", "hand"):
            return JSONResponse(
                {"error": f"Invalid mode '{mode}'. Use head, chest, or hand."},
                status_code=400,
            )
        shared_state.target_mode = mode
        if shared_state.on_target_mode_change:
            shared_state.on_target_mode_change(mode)
        logger.info("[API] Target mode quick-switched → %s", mode)
        return JSONResponse({"target_mode": mode, "message": f"Now targeting {mode}"})

    # ── System Control ───────────────────────────────────────────────
    @app.post("/system-control")
    async def system_control(req: SystemControlRequest) -> JSONResponse:
        if req.command not in ("start", "stop", "calibrate"):
            return JSONResponse(
                {"error": f"Invalid command '{req.command}'. Use start, stop, or calibrate."},
                status_code=400,
            )
        if shared_state.on_system_command:
            shared_state.on_system_command(req.command)
        logger.info("[API] System command received → %s", req.command)
        return JSONResponse({"command": req.command, "accepted": True})

    # ── MJPEG Video Feed ─────────────────────────────────────────────
    @app.get("/video-feed")
    async def video_feed() -> StreamingResponse:
        """
        Streams the live annotated camera feed as an MJPEG stream.
        The frontend can display this with: <img src="http://localhost:8000/video-feed" />
        """
        async def frame_generator():
            while True:
                frame_bytes = shared_state.latest_frame_jpeg
                if frame_bytes is not None:
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n\r\n" +
                        frame_bytes +
                        b"\r\n"
                    )
                await asyncio.sleep(0.016)  # ~60 FPS cap — actual rate is limited by vision loop

        return StreamingResponse(
            frame_generator(),
            media_type="multipart/x-mixed-replace; boundary=frame",
        )

    # ── WebSocket Telemetry ──────────────────────────────────────────
    @app.websocket("/ws/telemetry")
    async def telemetry_endpoint(ws: WebSocket) -> None:
        await ws_manager.connect(ws)
        logger.info("[API] WebSocket client connected")
        try:
            while True:
                # Keep the connection alive — client doesn't send data
                await ws.receive_text()
        except WebSocketDisconnect:
            await ws_manager.disconnect(ws)
            logger.info("[API] WebSocket client disconnected")

    return app
