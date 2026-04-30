export default function LiveFeed({ systemState, isMobile }) {
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
        <span style={{ ...statusBadge, background: badgeColor }}>
          {systemState.systemState}
        </span>
      </div>

      <div
        style={{
          ...feed,
          height: isMobile ? "260px" : "420px",
        }}
      >
        <div style={crosshairVertical}></div>
        <div style={crosshairHorizontal}></div>
        <div
          style={{
            ...feedCenterText,
            fontSize: isMobile ? "15px" : "18px",
          }}
        >
          Camera Stream
        </div>
      </div>
    </div>
  );
}

const card = {
  background: "#0f172a",
  border: "1px solid #1e293b",
  borderRadius: "16px",
  padding: "18px",
  boxShadow: "0 10px 30px rgba(0,0,0,0.25)",
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
  borderRadius: "14px",
  border: "1px solid #334155",
  position: "relative",
  overflow: "hidden",
  display: "flex",
  justifyContent: "center",
  alignItems: "center",
};

const feedCenterText = {
  color: "#94a3b8",
  letterSpacing: "0.5px",
};

const crosshairVertical = {
  position: "absolute",
  top: 0,
  left: "50%",
  transform: "translateX(-50%)",
  width: "2px",
  height: "100%",
  background: "rgba(255,255,255,0.15)",
};

const crosshairHorizontal = {
  position: "absolute",
  left: 0,
  top: "50%",
  transform: "translateY(-50%)",
  width: "100%",
  height: "2px",
  background: "rgba(255,255,255,0.15)",
};