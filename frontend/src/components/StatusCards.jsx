export default function StatusCards({ systemState, isMobile }) {
  const items = [
    { label: "FPS", value: systemState.fps },
    { label: "Confidence", value: systemState.confidence },
    { label: "Tracker", value: systemState.tracker },
    { label: "Model", value: systemState.model },
    { label: "State", value: systemState.systemState },
  ];

  return (
    <div style={card}>
      <h3 style={title}>System Status</h3>

      <div
        style={{
          ...grid,
          gridTemplateColumns: isMobile ? "1fr" : "1fr 1fr",
        }}
      >
        {items.map((item) => (
          <div key={item.label} style={miniCard}>
            <p style={label}>{item.label}</p>
            <p style={value}>{item.value}</p>
          </div>
        ))}
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
  borderRadius: "12px",
  padding: "12px",
};

const label = {
  margin: 0,
  color: "#94a3b8",
  fontSize: "12px",
};

const value = {
  margin: "8px 0 0 0",
  color: "#f8fafc",
  fontSize: "16px",
  fontWeight: "700",
  wordBreak: "break-word",
};