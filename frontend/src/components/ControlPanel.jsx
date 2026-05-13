import { useState } from "react";
import bodyImg from "../assets/body.png";

export default function ControlPanel({
  systemState,
  isMobile,
  setTargetMode,
  sendSystemCommand,
  connected,
}) {
  const [hoveredPoint, setHoveredPoint] = useState(null);
  const activeMode = (systemState.targetMode || "chest").toLowerCase();

  const handleTarget = (mode) => {
    if (setTargetMode) setTargetMode(mode);
  };

  const handleSystemCmd = (cmd) => {
    if (sendSystemCommand) sendSystemCommand(cmd);
  };

  const isActive = (mode) => activeMode === mode;

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
            height: isMobile
              ? "min(92vw, 430px)"
              : "min(calc(100vh - 360px), 520px)",
          }}
        >
          <img src={bodyImg} alt="body" style={imgStyle} />

          {/* HEAD target point — clickable */}
          <div
            style={{
              ...point,
              ...headPoint,
              borderColor: isActive("head")
                ? "rgba(239, 68, 68, 0.95)"
                : hoveredPoint === "head"
                ? "rgba(56, 189, 248, 1)"
                : "rgba(56, 189, 248, 0.6)",
              boxShadow: isActive("head")
                ? "0 0 24px rgba(239, 68, 68, 0.9), 0 0 48px rgba(239, 68, 68, 0.3)"
                : hoveredPoint === "head"
                ? "0 0 24px rgba(56, 189, 248, 0.9)"
                : "0 0 16px rgba(56, 189, 248, 0.5)",
              cursor: "pointer",
              pointerEvents: "auto",
              transform: `translate(-50%, -50%) scale(${
                isActive("head") || hoveredPoint === "head" ? 1.2 : 1
              })`,
              transition: "all 0.2s ease",
            }}
            onClick={() => handleTarget("head")}
            onMouseEnter={() => setHoveredPoint("head")}
            onMouseLeave={() => setHoveredPoint(null)}
            title="Target: Head"
          >
            <span
              style={{
                ...pointCore,
                background: isActive("head") ? "#ef4444" : "#e0f2fe",
              }}
            />
          </div>

          {/* CHEST target point — clickable */}
          <div
            style={{
              ...point,
              ...chestPoint,
              borderColor: isActive("chest")
                ? "rgba(239, 68, 68, 0.95)"
                : hoveredPoint === "chest"
                ? "rgba(56, 189, 248, 1)"
                : "rgba(56, 189, 248, 0.6)",
              boxShadow: isActive("chest")
                ? "0 0 24px rgba(239, 68, 68, 0.9), 0 0 48px rgba(239, 68, 68, 0.3)"
                : hoveredPoint === "chest"
                ? "0 0 24px rgba(56, 189, 248, 0.9)"
                : "0 0 16px rgba(56, 189, 248, 0.5)",
              cursor: "pointer",
              pointerEvents: "auto",
              transform: `translate(-50%, -50%) scale(${
                isActive("chest") || hoveredPoint === "chest" ? 1.2 : 1
              })`,
              transition: "all 0.2s ease",
            }}
            onClick={() => handleTarget("chest")}
            onMouseEnter={() => setHoveredPoint("chest")}
            onMouseLeave={() => setHoveredPoint(null)}
            title="Target: Chest"
          >
            <span
              style={{
                ...pointCore,
                background: isActive("chest") ? "#ef4444" : "#e0f2fe",
              }}
            />
          </div>

          {/* HAND target point — clickable */}
          <div
            style={{
              ...point,
              ...handPoint,
              borderColor: isActive("hand")
                ? "rgba(239, 68, 68, 0.95)"
                : hoveredPoint === "hand"
                ? "rgba(56, 189, 248, 1)"
                : "rgba(56, 189, 248, 0.6)",
              boxShadow: isActive("hand")
                ? "0 0 24px rgba(239, 68, 68, 0.9), 0 0 48px rgba(239, 68, 68, 0.3)"
                : hoveredPoint === "hand"
                ? "0 0 24px rgba(56, 189, 248, 0.9)"
                : "0 0 16px rgba(56, 189, 248, 0.5)",
              cursor: "pointer",
              pointerEvents: "auto",
              transform: `translate(-50%, -50%) scale(${
                isActive("hand") || hoveredPoint === "hand" ? 1.2 : 1
              })`,
              transition: "all 0.2s ease",
            }}
            onClick={() => handleTarget("hand")}
            onMouseEnter={() => setHoveredPoint("hand")}
            onMouseLeave={() => setHoveredPoint(null)}
            title="Target: Hand"
          >
            <span
              style={{
                ...pointCore,
                background: isActive("hand") ? "#ef4444" : "#e0f2fe",
              }}
            />
          </div>
        </div>

        {/* Legend */}
        <div style={legend}>
          {[
            { mode: "head", label: "Head" },
            { mode: "chest", label: "Chest" },
            { mode: "hand", label: "Hand" },
          ].map(({ mode, label }) => (
            <div
              key={mode}
              style={{
                ...legendItem,
                cursor: "pointer",
                opacity: isActive(mode) ? 1 : 0.6,
                fontWeight: isActive(mode) ? "700" : "400",
              }}
              onClick={() => handleTarget(mode)}
            >
              <span
                style={{
                  ...legendDot,
                  background: isActive(mode) ? "#ef4444" : "#38bdf8",
                  boxShadow: isActive(mode)
                    ? "0 0 8px rgba(239,68,68,0.6)"
                    : "none",
                }}
              />
              {label}
            </div>
          ))}
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
  width: "28px",
  height: "28px",
  borderRadius: "50%",
  border: "2.5px solid rgba(56,189,248,0.95)",
  display: "grid",
  placeItems: "center",
  zIndex: 10,
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

const handPoint = {
  top: "47%",
  left: "30%",
  transform: "translate(-50%, -50%)",
};

const pointCore = {
  width: "8px",
  height: "8px",
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
  transition: "opacity 0.2s ease",
};

const legendDot = {
  width: "10px",
  height: "10px",
  borderRadius: "50%",
  background: "#38bdf8",
  transition: "all 0.2s ease",
};
