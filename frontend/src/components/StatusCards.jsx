export default function StatusCards({ systemState, isMobile }) {
  const items = [
    {
      label: "FPS",
      value: systemState.fps,
      accent: "#a5f3fc",
    },
    {
      label: "Confidence",
      value:
        typeof systemState.confidence === "number"
          ? (systemState.confidence * 100).toFixed(0) + "%"
          : systemState.confidence,
      accent: systemState.confidence > 0.7 ? "#86efac" : "#fde68a",
    },
    {
      label: "Tracker",
      value: systemState.tracker,
      accent: "#c4b5fd",
    },
    {
      label: "Model",
      value: systemState.model,
      accent: "#c4b5fd",
    },
    {
      label: "Target",
      value: (systemState.targetMode || "chest").toUpperCase(),
      accent: "#fca5a5",
    },
  ];

  return (
    <div style={card}>
      <h3 style={title}>System Status</h3>

      <div
        style={{
          ...grid,
          gridTemplateColumns: isMobile
            ? "1fr 1fr"
            : "repeat(5, minmax(0, 1fr))",
        }}
      >
        {items.map((item) => (
          <div key={item.label} style={miniCard}>
            <p style={label}>{item.label}</p>
            <p style={{ ...value, color: item.accent || "#f8fafc" }}>
              {item.value}
            </p>
          </div>
        ))}
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

const grid = {
  display: "grid",
  gap: "12px",
};

const miniCard = {
  background: "#111827",
  border: "1px solid #243041",
  borderRadius: "8px",
  padding: "12px",
};

const label = {
  margin: 0,
  color: "#94a3b8",
  fontSize: "11px",
  textTransform: "uppercase",
  letterSpacing: "0.5px",
  fontWeight: "600",
};

const value = {
  margin: "8px 0 0 0",
  color: "#f8fafc",
  fontSize: "16px",
  fontWeight: "700",
  wordBreak: "break-word",
  fontFamily: "'JetBrains Mono', 'Consolas', monospace",
};
