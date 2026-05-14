import { useEffect, useRef, useState } from "react";

export default function LiveFeed({ systemState, isMobile, apiBase, connected }) {
  const [streamError, setStreamError] = useState(false);
  const canvasRef = useRef(null);
  const feedRef = useRef(null);
  const trailRef = useRef([]);
  const [feedSize, setFeedSize] = useState({ width: 0, height: 0 });
  const streamUrl = `${apiBase || "http://localhost:8000"}/video-feed`;
  const debug = systemState.debug || {};
  const vlaserX = debug.vlaserPx?.[0] || 0;
  const vlaserY = debug.vlaserPx?.[1] || 0;
  const frameW = debug.frameW || 640;
  const frameH = debug.frameH || 480;
  const depthCm = debug.depthCm || 0;

  const badgeColor =
    systemState.systemState === "Tracking Locked"
      ? "#22c55e"
      : systemState.systemState === "Target Detected"
      ? "#eab308"
      : systemState.systemState === "Reacquiring"
      ? "#f97316"
      : "#38bdf8";

  useEffect(() => {
    if (vlaserX > 0 || vlaserY > 0) {
      const trail = trailRef.current;
      trail.push({ x: vlaserX, y: vlaserY });
      if (trail.length > 40) trail.shift();
    }
  }, [vlaserX, vlaserY]);

  useEffect(() => {
    const feedEl = feedRef.current;
    if (!feedEl) return undefined;

    const updateSize = () => {
      const rect = feedEl.getBoundingClientRect();
      setFeedSize({
        width: Math.round(rect.width),
        height: Math.round(rect.height),
      });
    };

    updateSize();
    const resizeObserver = new ResizeObserver(updateSize);
    resizeObserver.observe(feedEl);

    return () => resizeObserver.disconnect();
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !connected || streamError || feedSize.width <= 0 || feedSize.height <= 0) {
      return undefined;
    }

    const ctx = canvas.getContext("2d");
    const dpr = window.devicePixelRatio || 1;
    const w = feedSize.width;
    const h = feedSize.height;

    canvas.width = w * dpr;
    canvas.height = h * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    const scale = Math.min(w / frameW, h / frameH);
    const viewW = frameW * scale;
    const viewH = frameH * scale;
    const ox = (w - viewW) / 2;
    const oy = (h - viewH) / 2;
    const toX = (px) => ox + px * scale;
    const toY = (py) => oy + py * scale;

    ctx.save();
    ctx.beginPath();
    ctx.rect(ox, oy, viewW, viewH);
    ctx.clip();

    const trail = trailRef.current;
    for (let i = 0; i < trail.length; i += 1) {
      const t = trail[i];
      const alpha = ((i + 1) / trail.length) * 0.35;
      ctx.beginPath();
      ctx.arc(toX(t.x), toY(t.y), 2.5, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(34, 197, 94, ${alpha})`;
      ctx.fill();
    }

    if (vlaserX > 0 || vlaserY > 0) {
      const lx = toX(vlaserX);
      const ly = toY(vlaserY);
      const glow = ctx.createRadialGradient(lx, ly, 0, lx, ly, 22);
      glow.addColorStop(0, "rgba(34, 197, 94, 0.55)");
      glow.addColorStop(1, "rgba(34, 197, 94, 0)");
      ctx.fillStyle = glow;
      ctx.fillRect(lx - 22, ly - 22, 44, 44);

      ctx.beginPath();
      ctx.arc(lx, ly, 5, 0, Math.PI * 2);
      ctx.fillStyle = "#22c55e";
      ctx.fill();
      ctx.strokeStyle = "#bbf7d0";
      ctx.lineWidth = 2;
      ctx.stroke();
    }

    ctx.restore();

    if (depthCm > 0) {
      const depthLabel = `${Math.round(depthCm)}cm`;
      ctx.font = "11px 'JetBrains Mono', 'Consolas', monospace";
      ctx.textAlign = "right";
      ctx.textBaseline = "top";
      ctx.fillStyle = "rgba(15, 23, 42, 0.82)";
      ctx.fillRect(ox + viewW - 70, oy + 10, 60, 22);
      ctx.fillStyle = "#cbd5e1";
      ctx.fillText(depthLabel, ox + viewW - 18, oy + 15);
    }

    return undefined;
  }, [connected, streamError, feedSize, vlaserX, vlaserY, frameW, frameH, depthCm]);

  return (
    <div style={card}>
      <div
        style={{
          ...cardHeader,
          flexDirection: isMobile ? "column" : "row",
          alignItems: isMobile ? "flex-start" : "center",
          gap: isMobile ? "10px" : "0",
        }}
      >
        <h3 style={title}>Live Feed</h3>
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <span style={fpsBadge}>{systemState.fps} FPS</span>
          <span style={{ ...statusBadge, background: badgeColor }}>
            {systemState.systemState}
          </span>
        </div>
      </div>

      <div
        ref={feedRef}
        style={{
          ...feed,
          height: isMobile ? "340px" : "100%",
          minHeight: isMobile ? "340px" : "500px",
        }}
      >
        {connected && !streamError ? (
          <>
            <img
              src={streamUrl}
              alt="Live camera feed"
              style={streamImg}
              onError={() => setStreamError(true)}
            />
            <canvas ref={canvasRef} style={laserOverlayCanvas} />
          </>
        ) : (
          <>
            <div style={crosshairVertical} />
            <div style={crosshairHorizontal} />
            <div
              style={{
                ...feedCenterContent,
                fontSize: isMobile ? "15px" : "18px",
              }}
            >
              <div style={offlineIcon}>OFF</div>
              <div style={{ color: "#94a3b8", letterSpacing: "0.5px" }}>
                {streamError ? "Stream connection lost" : "Waiting for backend..."}
              </div>
              <div style={{ color: "#475569", fontSize: "12px", marginTop: "4px" }}>
                {apiBase}/video-feed
              </div>
            </div>
          </>
        )}

        {connected && !streamError && (
          <>
            <div style={targetOverlay}>
              <span style={targetBadge}>
                {(systemState.targetMode || "chest").toUpperCase()}
              </span>
            </div>
            <div style={legendOverlay}>
              <span style={legendItem}>
                <span style={{ ...legendDot, background: "#22c55e" }} />
                Virtual laser
              </span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

const card = {
  background: "#0f172a",
  border: "1px solid #1e293b",
  borderRadius: "8px",
  padding: "18px",
  boxShadow: "0 10px 30px rgba(0,0,0,0.25)",
  minHeight: "100%",
  display: "grid",
  gridTemplateRows: "auto 1fr",
  boxSizing: "border-box",
};

const cardHeader = {
  display: "flex",
  justifyContent: "space-between",
  marginBottom: "14px",
};

const title = {
  margin: 0,
  fontSize: "18px",
  color: "#f8fafc",
};

const fpsBadge = {
  padding: "5px 10px",
  borderRadius: "999px",
  background: "#111827",
  border: "1px solid #334155",
  color: "#a5f3fc",
  fontWeight: "700",
  fontSize: "12px",
  fontFamily: "'JetBrains Mono', 'Consolas', monospace",
};

const statusBadge = {
  padding: "6px 10px",
  borderRadius: "999px",
  color: "#0f172a",
  fontWeight: "700",
  fontSize: "12px",
};

const feed = {
  background: "linear-gradient(180deg, rgba(15,23,42,1) 0%, rgba(0,0,0,1) 100%)",
  borderRadius: "8px",
  border: "1px solid #334155",
  position: "relative",
  overflow: "hidden",
  display: "flex",
  justifyContent: "center",
  alignItems: "center",
};

const streamImg = {
  width: "100%",
  height: "100%",
  objectFit: "contain",
  display: "block",
};

const laserOverlayCanvas = {
  position: "absolute",
  inset: 0,
  width: "100%",
  height: "100%",
  pointerEvents: "none",
};

const feedCenterContent = {
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  gap: "8px",
};

const offlineIcon = {
  fontSize: "13px",
  color: "#64748b",
  border: "1px solid #334155",
  borderRadius: "999px",
  padding: "7px 9px",
  fontWeight: "800",
  letterSpacing: "0.8px",
};

const crosshairVertical = {
  position: "absolute",
  top: 0,
  left: "50%",
  transform: "translateX(-50%)",
  width: "2px",
  height: "100%",
  background: "rgba(255,255,255,0.08)",
};

const crosshairHorizontal = {
  position: "absolute",
  left: 0,
  top: "50%",
  transform: "translateY(-50%)",
  width: "100%",
  height: "2px",
  background: "rgba(255,255,255,0.08)",
};

const targetOverlay = {
  position: "absolute",
  top: "12px",
  left: "12px",
};

const targetBadge = {
  padding: "5px 10px",
  borderRadius: "6px",
  background: "rgba(15, 23, 42, 0.85)",
  border: "1px solid #334155",
  color: "#f8fafc",
  fontSize: "11px",
  fontWeight: "700",
  letterSpacing: "0.5px",
  backdropFilter: "blur(8px)",
};

const legendOverlay = {
  position: "absolute",
  right: "12px",
  bottom: "12px",
  display: "flex",
  gap: "12px",
  alignItems: "center",
  padding: "6px 10px",
  borderRadius: "6px",
  background: "rgba(15, 23, 42, 0.78)",
  border: "1px solid rgba(51, 65, 85, 0.9)",
  color: "#cbd5e1",
  fontSize: "11px",
  fontWeight: "700",
  backdropFilter: "blur(8px)",
};

const legendItem = {
  display: "flex",
  alignItems: "center",
  gap: "5px",
};

const legendDot = {
  width: "8px",
  height: "8px",
  borderRadius: "50%",
  boxSizing: "border-box",
  display: "inline-block",
};
