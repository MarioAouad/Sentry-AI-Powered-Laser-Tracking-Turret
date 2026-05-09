import bodyImg from "../assets/body.png";

export default function ControlPanel({ systemState, isMobile }) {
  return (
    <section style={panel}>
      <div style={header}>
        <h3 style={title}>Target Body Map</h3>
        <span style={stateBadge}>{systemState.indicator}</span>
      </div>

      <div style={bodyPanel}>
        <div
          style={{
            ...bodyFigure,
            width: isMobile ? "min(74vw, 260px)" : "min(30vw, 360px)",
            height: isMobile ? "min(92vw, 430px)" : "min(calc(100vh - 230px), 620px)",
          }}
        >
          <img src={bodyImg} alt="body" style={imgStyle} />

          <div style={{ ...point, ...headPoint }}>
            <span style={pointCore} />
          </div>
          <div style={{ ...point, ...chestPoint }}>
            <span style={pointCore} />
          </div>
        </div>

        <div style={legend}>
          <div style={legendItem}>
            <span style={legendDot}></span> Head
          </div>
          <div style={legendItem}>
            <span style={legendDot}></span> Chest
          </div>
        </div>
      </div>
    </section>
  );
}

const panel = {
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

const header = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  gap: "12px",
  marginBottom: "12px",
};

const title = {
  margin: 0,
  fontSize: "18px",
  color: "#f8fafc",
};

const stateBadge = {
  border: "1px solid #334155",
  borderRadius: "999px",
  color: "#cbd5e1",
  fontSize: "12px",
  fontWeight: "700",
  padding: "6px 10px",
  background: "#111827",
};

const bodyPanel = {
  display: "flex",
  flexDirection: "column",
  justifyContent: "flex-start",
  gap: "14px",
  alignItems: "center",
  minHeight: 0,
  paddingTop: "18px",
};

const bodyFigure = {
  position: "relative",
  background: "transparent",
  overflow: "visible",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
};

const imgStyle = {
  width: "100%",
  height: "100%",
  objectFit: "contain",
  opacity: 0.9,
  mixBlendMode: "screen",
  filter: "drop-shadow(0 18px 36px rgba(0,0,0,0.45))",
};

const point = {
  position: "absolute",
  width: "24px",
  height: "24px",
  borderRadius: "50%",
  border: "2px solid rgba(56,189,248,0.95)",
  boxShadow: "0 0 20px rgba(56,189,248,0.85)",
  display: "grid",
  placeItems: "center",
  pointerEvents: "none",
};

const headPoint = {
  top: "15%",
  left: "50%",
  transform: "translate(-50%, -50%)",
};

const chestPoint = {
  top: "32%",
  left: "50%",
  transform: "translate(-50%, -50%)",
};

const pointCore = {
  width: "7px",
  height: "7px",
  borderRadius: "50%",
  background: "#e0f2fe",
};

const legend = {
  display: "flex",
  justifyContent: "center",
  gap: "18px",
  flexWrap: "wrap",
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
