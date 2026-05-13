import { useEffect, useState } from "react";
import LiveFeed from "../components/LiveFeed";
import StatusCards from "../components/StatusCards";
import ControlPanel from "../components/ControlPanel";
import ServoPanel from "../components/ServoPanel";
import VirtualLaser from "../components/VirtualLaser";
import { useSystemState } from "../hooks/useSystemstate";

export default function Dashboard() {
  const { systemState, connected, setTargetMode, sendSystemCommand, apiBase } =
    useSystemState();
  const [windowWidth, setWindowWidth] = useState(window.innerWidth);

  useEffect(() => {
    function handleResize() {
      setWindowWidth(window.innerWidth);
    }

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const isTablet = windowWidth <= 1100;
  const isMobile = windowWidth <= 700;

  return (
    <div
      style={{
        ...styles.page,
        padding: isMobile ? "12px" : isTablet ? "16px" : "20px",
      }}
    >
      <header
        style={{
          ...styles.header,
          flexDirection: isMobile ? "column" : "row",
          alignItems: isMobile ? "flex-start" : "center",
          gap: isMobile ? "14px" : "0",
          padding: isMobile ? "14px" : "16px 20px",
        }}
      >
        <div>
          <h1
            style={{
              ...styles.title,
              fontSize: isMobile ? "22px" : "28px",
            }}
          >
            AI Sentry Turret Dashboard
          </h1>
        </div>

        <div style={styles.headerRight}>
          {/* Connection indicator */}
          <div
            style={{
              ...styles.connectionBadge,
              borderColor: connected ? "#22c55e44" : "#ef444444",
            }}
          >
            <span
              style={{
                ...styles.dot,
                background: connected ? "#22c55e" : "#ef4444",
                boxShadow: connected
                  ? "0 0 8px #22c55e88"
                  : "0 0 8px #ef444488",
              }}
            />
            {connected ? "Live" : "Offline"}
          </div>

          <div style={styles.headerBadge}>
            <span
              style={{
                ...styles.dot,
                background:
                  systemState.systemState === "Tracking Locked"
                    ? "#22c55e"
                    : systemState.systemState === "Reacquiring"
                    ? "#f97316"
                    : "#38bdf8",
              }}
            />
            {systemState.systemState}
          </div>
        </div>
      </header>

      <div
        style={{
          ...styles.mainGrid,
          gridTemplateColumns: isTablet
            ? "1fr"
            : "minmax(340px, 0.85fr) minmax(520px, 1.35fr)",
          gap: isMobile ? "14px" : "18px",
        }}
      >
        <div style={styles.leftColumn}>
          <ControlPanel
            systemState={systemState}
            isMobile={isMobile}
            setTargetMode={setTargetMode}
            sendSystemCommand={sendSystemCommand}
            connected={connected}
          />
        </div>

        <div style={styles.rightColumn}>
          <LiveFeed
            systemState={systemState}
            isMobile={isMobile}
            apiBase={apiBase}
            connected={connected}
          />
          <StatusCards systemState={systemState} isMobile={isMobile} />
          <VirtualLaser systemState={systemState} />
          <ServoPanel systemState={systemState} />
        </div>
      </div>
    </div>
  );
}

const styles = {
  page: {
    minHeight: "100vh",
    background: "#020617",
    color: "#e2e8f0",
    fontFamily: "'Inter', 'Segoe UI', system-ui, sans-serif",
    boxSizing: "border-box",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    marginBottom: "18px",
    background: "#0f172a",
    border: "1px solid #1e293b",
    borderRadius: "8px",
    boxShadow: "0 10px 30px rgba(0,0,0,0.25)",
  },
  title: {
    margin: 0,
    fontWeight: "700",
    color: "#f8fafc",
  },
  headerRight: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
  },
  connectionBadge: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    background: "#111827",
    border: "1px solid #334155",
    padding: "8px 12px",
    borderRadius: "999px",
    fontSize: "12px",
    fontWeight: "700",
    color: "#cbd5e1",
  },
  headerBadge: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
    background: "#111827",
    border: "1px solid #334155",
    padding: "10px 14px",
    borderRadius: "999px",
    fontSize: "14px",
    fontWeight: "600",
    color: "#cbd5e1",
  },
  dot: {
    width: "10px",
    height: "10px",
    borderRadius: "50%",
    background: "#22c55e",
    flexShrink: 0,
  },
  mainGrid: {
    display: "grid",
    alignItems: "stretch",
    minHeight: "calc(100vh - 128px)",
  },
  leftColumn: {
    display: "grid",
    minHeight: 0,
  },
  rightColumn: {
    display: "grid",
    gap: "18px",
    gridTemplateRows: "minmax(500px, 1fr) auto auto auto",
    minHeight: 0,
  },
};
