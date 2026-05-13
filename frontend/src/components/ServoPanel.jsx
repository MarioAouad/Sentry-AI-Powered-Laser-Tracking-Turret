export default function ServoPanel({ systemState }) {
  const yaw = systemState.yaw ?? 90;
  const pitch = systemState.pitch ?? 90;

  // Map 0-180 to percentage for visual bar
  const yawPct = ((yaw / 180) * 100).toFixed(1);
  const pitchPct = ((pitch / 180) * 100).toFixed(1);

  return (
    <div style={card}>
      <h3 style={title}>Actuator Panel</h3>

      {/* Yaw / Pan */}
      <div style={row}>
        <div style={labelRow}>
          <span style={label}>Yaw (Pan)</span>
          <span style={value}>{yaw}°</span>
        </div>
        <div style={barTrack}>
          <div
            style={{
              ...barFill,
              width: `${yawPct}%`,
              background:
                "linear-gradient(90deg, #0ea5e9 0%, #38bdf8 50%, #7dd3fc 100%)",
            }}
          />
          {/* Center marker */}
          <div style={centerMark} />
        </div>
        <div style={rangeLabels}>
          <span>0°</span>
          <span style={{ color: "#64748b" }}>90°</span>
          <span>180°</span>
        </div>
      </div>

      {/* Pitch / Tilt */}
      <div style={{ ...row, borderBottom: "none" }}>
        <div style={labelRow}>
          <span style={label}>Pitch (Tilt)</span>
          <span style={value}>{pitch}°</span>
        </div>
        <div style={barTrack}>
          <div
            style={{
              ...barFill,
              width: `${pitchPct}%`,
              background:
                "linear-gradient(90deg, #f97316 0%, #fb923c 50%, #fdba74 100%)",
            }}
          />
          {/* Center marker */}
          <div style={centerMark} />
        </div>
        <div style={rangeLabels}>
          <span>0°</span>
          <span style={{ color: "#64748b" }}>90°</span>
          <span>180°</span>
        </div>
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
};

const title = {
  margin: "0 0 16px 0",
  fontSize: "18px",
  color: "#f8fafc",
};

const row = {
  padding: "12px 0",
  borderBottom: "1px solid #1e293b",
};

const labelRow = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  marginBottom: "8px",
};

const label = {
  color: "#94a3b8",
  fontSize: "13px",
};

const value = {
  color: "#f8fafc",
  fontWeight: "700",
  fontSize: "16px",
  fontFamily: "'JetBrains Mono', 'Consolas', monospace",
};

const barTrack = {
  position: "relative",
  width: "100%",
  height: "8px",
  background: "#1e293b",
  borderRadius: "4px",
  overflow: "visible",
};

const barFill = {
  height: "100%",
  borderRadius: "4px",
  transition: "width 0.15s ease-out",
  boxShadow: "0 0 8px rgba(14, 165, 233, 0.3)",
};

const centerMark = {
  position: "absolute",
  left: "50%",
  top: "-2px",
  width: "2px",
  height: "12px",
  background: "#475569",
  transform: "translateX(-50%)",
  borderRadius: "1px",
};

const rangeLabels = {
  display: "flex",
  justifyContent: "space-between",
  marginTop: "4px",
  fontSize: "10px",
  color: "#475569",
  fontFamily: "'JetBrains Mono', 'Consolas', monospace",
};
