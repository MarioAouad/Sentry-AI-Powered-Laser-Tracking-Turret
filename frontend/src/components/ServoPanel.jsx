export default function ServoPanel({ systemState }) {
  return (
    <div style={card}>
      <h3 style={title}>Actuator Panel</h3>

      <div style={row}>
        <span style={label}>Yaw</span>
        <span style={value}>{systemState.yaw}°</span>
      </div>

      <div style={{ ...row, borderBottom: "none" }}>
        <span style={label}>Pitch</span>
        <span style={value}>{systemState.pitch}°</span>
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

const row = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: "12px",
  padding: "12px 0",
  borderBottom: "1px solid #1e293b",
};

const label = {
  color: "#94a3b8",
};

const value = {
  color: "#f8fafc",
  fontWeight: "700",
  textAlign: "right",
};