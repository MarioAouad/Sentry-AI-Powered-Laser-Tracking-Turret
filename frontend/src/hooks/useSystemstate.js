import { useEffect, useState, useRef, useCallback } from "react";
import { mockSystemData } from "../mocks/mockSystemData";

// Backend API base URL — configurable via .env (VITE_API_URL)
const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
const WS_URL = API_BASE.replace(/^http/, "ws") + "/ws/telemetry";

export function useSystemState() {
  const [systemState, setSystemState] = useState(mockSystemData);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);
  const reconnectTimer = useRef(null);
  const reconnectDelay = useRef(1000);

  // ── WebSocket Connection ───────────────────────────────────────
  useEffect(() => {
    let mounted = true;

    function connect() {
      if (!mounted) return;

      try {
        const ws = new WebSocket(WS_URL);
        wsRef.current = ws;

        ws.onopen = () => {
          if (!mounted) return;
          console.log("[Sentry WS] Connected to", WS_URL);
          setConnected(true);
          reconnectDelay.current = 1000; // Reset backoff
        };

        ws.onmessage = (event) => {
          if (!mounted) return;
          try {
            const data = JSON.parse(event.data);
            setSystemState(data);
          } catch (err) {
            console.warn("[Sentry WS] Parse error:", err);
          }
        };

        ws.onclose = () => {
          if (!mounted) return;
          console.log("[Sentry WS] Disconnected — reconnecting in", reconnectDelay.current, "ms");
          setConnected(false);
          wsRef.current = null;

          // Exponential backoff reconnect (max 10s)
          reconnectTimer.current = setTimeout(() => {
            reconnectDelay.current = Math.min(reconnectDelay.current * 1.5, 10000);
            connect();
          }, reconnectDelay.current);
        };

        ws.onerror = (err) => {
          console.warn("[Sentry WS] Error:", err);
          ws.close();
        };
      } catch (err) {
        console.error("[Sentry WS] Failed to create WebSocket:", err);
        reconnectTimer.current = setTimeout(connect, reconnectDelay.current);
      }
    }

    connect();

    return () => {
      mounted = false;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      if (wsRef.current) {
        wsRef.current.onclose = null; // Prevent reconnect on unmount
        wsRef.current.close();
      }
    };
  }, []);

  // ── Target Mode API ────────────────────────────────────────────
  const setTargetMode = useCallback(async (mode) => {
    try {
      const res = await fetch(`${API_BASE}/target-mode`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode }),
      });
      if (res.ok) {
        console.log("[Sentry API] Target mode →", mode);
        // Optimistic update (WS will confirm)
        setSystemState((prev) => ({ ...prev, targetMode: mode }));
      } else {
        console.error("[Sentry API] Target mode failed:", await res.text());
      }
    } catch (err) {
      console.error("[Sentry API] Target mode error:", err);
    }
  }, []);

  // ── System Control API ─────────────────────────────────────────
  const sendSystemCommand = useCallback(async (command) => {
    try {
      const res = await fetch(`${API_BASE}/system-control`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command }),
      });
      if (res.ok) {
        console.log("[Sentry API] System command →", command);
      } else {
        console.error("[Sentry API] System command failed:", await res.text());
      }
    } catch (err) {
      console.error("[Sentry API] System command error:", err);
    }
  }, []);

  return {
    systemState,
    connected,
    setTargetMode,
    sendSystemCommand,
    apiBase: API_BASE,
  };
}