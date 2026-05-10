"""
serial_tether.py — PySerial USB-to-TTL Communication Bridge
============================================================
This module manages the real-time data link between the Python AI
pipeline (running on the GPU compute node) and the ESP32-CAM edge
motor controller.

The ESP32 firmware (SerialParser.cpp) expects commands in the format:

    PAN,TILT,STATE\\n

at 115200 baud, where:
    - PAN   = integer [0, 180], center = 90
    - TILT  = integer [0, 180], center = 90
    - STATE = 0 (SCANNING), 1 (LOCKED), 2 (OFF)

Key design decisions:
    - Non-blocking writes via a background thread and a thread-safe queue
    - Automatic reconnection with exponential backoff on USB disconnect
    - Auto-detection of ESP32 COM port via ``serial.tools.list_ports``
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from typing import Literal

import serial
import serial.tools.list_ports

logger = logging.getLogger("sentry.comms.serial")

# System states matching Config.h on the ESP32
STATE_SCANNING = 0
STATE_LOCKED = 1
STATE_OFF = 2

SystemState = Literal[0, 1, 2]


class SerialTether:
    """
    Non-blocking serial bridge to the ESP32 edge motor controller.

    Parameters
    ----------
    port : str
        COM port (e.g., ``"COM5"`` on Windows).
    baud_rate : int
        Must match ``BAUD_RATE`` in the ESP32's Config.h.
    reconnect_timeout : float
        Seconds to wait between reconnection attempts.
    auto_detect : bool
        If True and the specified port fails, attempt to auto-detect
        the ESP32's COM port.
    """

    def __init__(
        self,
        port: str = "COM5",
        baud_rate: int = 115200,
        reconnect_timeout: float = 5.0,
        auto_detect: bool = True,
    ) -> None:
        self._port = port
        self._baud_rate = baud_rate
        self._reconnect_timeout = reconnect_timeout
        self._auto_detect = auto_detect

        self._serial: serial.Serial | None = None
        self._connected = False

        # Thread-safe command queue (newest command wins — old ones are discarded)
        self._cmd_queue: queue.Queue[str] = queue.Queue(maxsize=1)
        self._stop_event = threading.Event()
        self._write_thread: threading.Thread | None = None

        logger.info(
            "[SerialTether] Initialised — port=%s, baud=%d, auto_detect=%s",
            port, baud_rate, auto_detect,
        )

    # ── Connection Management ────────────────────────────────────────
    def connect(self) -> bool:
        """Attempt to open the serial port. Returns True on success."""
        # Try the specified port first
        if self._try_open(self._port):
            return True

        # Fallback: auto-detect
        if self._auto_detect:
            detected = self._detect_esp32_port()
            if detected and self._try_open(detected):
                return True

        logger.error("[SerialTether] Failed to connect to any serial port")
        return False

    def _try_open(self, port: str) -> bool:
        """Try opening a specific COM port."""
        try:
            self._serial = serial.Serial(
                port=port,
                baudrate=self._baud_rate,
                timeout=1.0,
                write_timeout=1.0,
            )
            # Give the ESP32 time to reset after serial connection
            time.sleep(2.0)
            self._connected = True
            self._port = port
            logger.info("[SerialTether] ✓ Connected to %s @ %d baud", port, self._baud_rate)
            return True
        except (serial.SerialException, OSError) as exc:
            logger.warning("[SerialTether] Cannot open %s: %s", port, exc)
            self._connected = False
            return False

    def _detect_esp32_port(self) -> str | None:
        """Scan available COM ports for an ESP32 or FTDI device."""
        ports = serial.tools.list_ports.comports()
        for port_info in ports:
            desc = (port_info.description or "").lower()
            hwid = (port_info.hwid or "").lower()
            # Common ESP32 / FTDI identifiers
            if any(kw in desc for kw in ("cp210x", "ch340", "ftdi", "esp32", "usb-serial")):
                logger.info("[SerialTether] Auto-detected ESP32 on %s (%s)", port_info.device, desc)
                return port_info.device
            if any(kw in hwid for kw in ("10c4:ea60", "1a86:7523", "0403:6001")):
                logger.info("[SerialTether] Auto-detected ESP32 on %s (HWID)", port_info.device)
                return port_info.device
        logger.warning("[SerialTether] Auto-detect found no ESP32 devices")
        return None

    # ── Non-Blocking Write Engine ────────────────────────────────────
    def start(self) -> None:
        """Start the background write thread."""
        if self._write_thread is not None and self._write_thread.is_alive():
            return
        self._stop_event.clear()
        self._write_thread = threading.Thread(target=self._write_loop, daemon=True, name="serial-tx")
        self._write_thread.start()
        logger.info("[SerialTether] Write thread started")

    def stop(self) -> None:
        """Stop the background write thread and close the port."""
        self._stop_event.set()
        if self._write_thread is not None:
            self._write_thread.join(timeout=3.0)
        if self._serial is not None and self._serial.is_open:
            self._serial.close()
            logger.info("[SerialTether] Port closed")
        self._connected = False

    def _write_loop(self) -> None:
        """Background loop: dequeue and transmit commands."""
        while not self._stop_event.is_set():
            try:
                cmd = self._cmd_queue.get(timeout=0.05)
            except queue.Empty:
                continue

            if not self._connected or self._serial is None or not self._serial.is_open:
                logger.warning("[SerialTether] Not connected — attempting reconnect")
                if not self.connect():
                    time.sleep(self._reconnect_timeout)
                    continue

            try:
                self._serial.write(cmd.encode("ascii"))
                self._serial.flush()
                logger.debug("[SerialTether] TX → %s", cmd.strip())
            except (serial.SerialException, OSError) as exc:
                logger.error("[SerialTether] Write failed: %s — reconnecting", exc)
                self._connected = False

    # ── Public API ───────────────────────────────────────────────────
    def send_command(self, pan: int, tilt: int, state: int) -> None:
        """
        Queue a servo command for transmission.

        Format: ``"PAN,TILT,STATE\\n"`` — matching the ESP32's
        SerialParser.cpp expectations.

        If the queue already has a pending command, it is replaced
        (newest-wins policy to prevent latency buildup).
        """
        # Clamp to hardware bounds (defence-in-depth)
        pan = max(0, min(180, int(pan)))
        tilt = max(0, min(180, int(tilt)))
        state = max(0, min(2, int(state)))

        cmd = f"{pan},{tilt},{state}\n"

        # Clear stale command and enqueue the fresh one (newest-wins)
        try:
            while not self._cmd_queue.empty():
                self._cmd_queue.get_nowait()
        except queue.Empty:
            pass
        self._cmd_queue.put(cmd)

    @property
    def is_connected(self) -> bool:
        return self._connected
