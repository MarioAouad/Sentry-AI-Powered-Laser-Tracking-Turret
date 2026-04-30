import bodyImg from "../assets/body.png";

export default function ControlPanel({ systemState, setSystemState }) {
  function handleStart() {
    setSystemState((prev) => ({
      ...prev,
      systemState: "Target Detected",
    }));
  }

  function handleStop() {
    setSystemState((prev) => ({
      ...prev,
      systemState: "Scanning",
    }));
  }

  return (
    <div style={card}>
      <h3 style={title}>Body Points</h3>

      <div style={buttonRow}>
        <button style={startBtn} onClick={handleStart}>
          Start
        </button>
        <button style={stopBtn} onClick={handleStop}>
          Stop
        </button>
      </div>

      <div style={bodyPanel}>
        <div style={bodyFigure}>
          {/* Human image */}
          <img src={bodyImg} alt="body" style={imgStyle} />

          {/* Points */}
          <div style={{ ...point, ...headPoint }} />
          <div style={{ ...point, ...chestPoint }} />
        </div>

        {/* Legend */}
        <div style={legend}>
          <div style={legendItem}>
            <span style={legendDot}></span> Head
          </div>
          <div style={legendItem}>
            <span style={legendDot}></span> Chest
          </div>
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

const title = {
  margin: "0 0 16px 0",
  fontSize: "18px",
  color: "#f8fafc",
};

const buttonRow = {
  display: "flex",
  gap: "10px",
  marginBottom: "18px",
  flexWrap: "wrap",
};

const startBtn = {
  flex: 1,
  minWidth: "120px",
  padding: "10px 14px",
  background: "#22c55e",
  border: "none",
  borderRadius: "10px",
  color: "white",
  fontWeight: "700",
  cursor: "pointer",
};

const stopBtn = {
  flex: 1,
  minWidth: "120px",
  padding: "10px 14px",
  background: "#ef4444",
  border: "none",
  borderRadius: "10px",
  color: "white",
  fontWeight: "700",
  cursor: "pointer",
};

const bodyPanel = {
  display: "flex",
  flexDirection: "column",
  gap: "16px",
  alignItems: "center",
};

const bodyFigure = {
  position: "relative",
  width: "220px",
  height: "320px",
  background: "#111827",
  border: "1px solid #243041",
  borderRadius: "14px",
  overflow: "hidden",
};

const imgStyle = {
  width: "100%",
  height: "100%",
  objectFit: "contain",
  opacity: 0.85,
};

const point = {
  position: "absolute",
  width: "14px",
  height: "14px",
  borderRadius: "50%",
  background: "#38bdf8",
  boxShadow: "0 0 12px rgba(56,189,248,0.8)",
};

/* 🔥 IMPORTANT: these are percentage-based → works with ANY image */
const headPoint = {
  top: "18%",
  left: "50%",
  transform: "translate(-50%, -50%)",
};

const chestPoint = {
  top: "38%",
  left: "50%",
  transform: "translate(-50%, -50%)",
};

const legend = {
  width: "100%",
  display: "grid",
  gap: "8px",
};

const legendItem = {
  display: "flex",
  alignItems: "center",
  gap: "8px",
  color: "#cbd5e1",
  fontSize: "13px",
};

const legendDot = {
  width: "10px",
  height: "10px",
  borderRadius: "50%",
  background: "#38bdf8",
};
