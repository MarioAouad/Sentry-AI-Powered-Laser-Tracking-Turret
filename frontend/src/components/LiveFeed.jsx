import { useState } from "react";

export default function LiveFeed({ systemState, isMobile, apiBase, connected }) {
  const [streamError, setStreamError] = useState(false);
  const streamUrl = `${apiBase || "http://localhost:8000"}/video-feed`;

  const badgeColor =
    systemState.systemState === "Tracking Locked"
      ? "#22c55e"
      : systemState.systemState === "Target Detected"
      ? "#eab308"
      : systemState.systemState === "Reacquiring"
      ? "#f97316"
      : "#38bdf8";

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
          {/* FPS badge */}
          <span style={fpsBadge}>{systemState.fps} FPS</span>
          <span style={{ ...statusBadge, background: badgeColor }}>
            {systemState.systemState}
          </span>
        </div>
      </div>

      <div
        style={{
          ...feed,
          height: isMobile ? "300px" : "100%",
          minHeight: isMobile ? "300px" : "420px",
        }}
      >
        {connected && !streamError ? (
          /* Real MJPEG stream from the backend */
          <img
            src={streamUrl}
            alt="Live camera feed"
            style={streamImg}
            onError={() => setStreamError(true)}
          />
        ) : (
          /* Offline / error fallback */
          <>
            <div style={crosshairVertical} />
            <div style={crosshairHorizontal} />
            <div
              style={{
                ...feedCenterContent,
                fontSize: isMobile ? "15px" : "18px",
              }}
            >
              <div style={offlineIcon}>⦿</div>
              <div style={{ color: "#94a3b8", letterSpacing: "0.5px" }}>
                {streamError
                  ? "Stream connection lost"
                  : "Waiting for backend..."}
              </div>
              <div style={{ color: "#475569", fontSize: "12px", marginTop: "4px" }}>
                {apiBase}/video-feed
              </div>
            </div>
          </>
        )}

        {/* Overlay: target mode indicator */}
        {connected && !streamError && (
          <div style={targetOverlay}>
            <span style={targetBadge}>
              🎯 {(systemState.targetMode || "chest").toUpperCase()}
            </span>
          </div>
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
  background:
    "linear-gradient(180deg, rgba(15,23,42,1) 0%, rgba(0,0,0,1) 100%)",
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

const feedCenterContent = {
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  gap: "8px",
};

const offlineIcon = {
  fontSize: "36px",
  color: "#334155",
  animation: "pulse 2s ease-in-out infinite",
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
