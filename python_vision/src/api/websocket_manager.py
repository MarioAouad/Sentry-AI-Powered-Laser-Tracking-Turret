"""
websocket_manager.py — Thread-Safe WebSocket Client Manager
============================================================
Manages all connected WebSocket clients and provides a broadcast
method to push telemetry data to every dashboard simultaneously.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger("sentry.api.ws")


class WebSocketManager:
    """
    Manages active WebSocket connections for real-time telemetry.

    Thread-safe: the orchestrator can call ``set_telemetry()`` from any
    thread, and the async broadcast loop will pick it up.
    """

    def __init__(self) -> None:
        self._clients: list[WebSocket] = []
        self._lock = asyncio.Lock()

        # Latest telemetry snapshot (set from the vision loop thread)
        self._telemetry: dict[str, Any] = {}
        self._telemetry_lock = asyncio.Lock()

        logger.info("[WebSocketManager] Initialised")

    async def connect(self, ws: WebSocket) -> None:
        """Accept and register a new WebSocket client."""
        await ws.accept()
        async with self._lock:
            self._clients.append(ws)
        logger.info("[WebSocketManager] Client connected — total=%d", len(self._clients))

    async def disconnect(self, ws: WebSocket) -> None:
        """Remove a disconnected client."""
        async with self._lock:
            if ws in self._clients:
                self._clients.remove(ws)
        logger.info("[WebSocketManager] Client disconnected — total=%d", len(self._clients))

    async def set_telemetry(self, data: dict[str, Any]) -> None:
        """Update the latest telemetry snapshot."""
        async with self._telemetry_lock:
            self._telemetry = data

    async def broadcast(self) -> None:
        """Send the current telemetry to all connected clients."""
        async with self._telemetry_lock:
            payload = self._telemetry.copy()

        if not payload:
            return

        async with self._lock:
            dead: list[WebSocket] = []
            for ws in self._clients:
                try:
                    await ws.send_json(payload)
                except Exception:
                    dead.append(ws)

            for ws in dead:
                self._clients.remove(ws)
                logger.debug("[WebSocketManager] Removed dead client — total=%d", len(self._clients))

    @property
    def client_count(self) -> int:
        return len(self._clients)
