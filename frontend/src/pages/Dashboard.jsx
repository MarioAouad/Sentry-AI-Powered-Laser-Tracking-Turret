import { useEffect, useState } from "react";
import LiveFeed from "../components/LiveFeed";
import StatusCards from "../components/StatusCards";
import ControlPanel from "../components/ControlPanel";
import ServoPanel from "../components/ServoPanel";
import { useSystemState } from "../hooks/useSystemstate";

export default function Dashboard() {
  const { systemState } = useSystemState();
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

        <div style={styles.headerBadge}>
          <span style={styles.dot}></span>
          {systemState.systemState}
        </div>
      </header>

      <div
        style={{
          ...styles.mainGrid,
          gridTemplateColumns: isTablet ? "1fr" : "minmax(340px, 0.85fr) minmax(520px, 1.35fr)",
          gap: isMobile ? "14px" : "18px",
        }}
      >
        <div style={styles.leftColumn}>
          <ControlPanel systemState={systemState} isMobile={isMobile} />
        </div>

        <div style={styles.rightColumn}>
          <LiveFeed systemState={systemState} isMobile={isMobile} />
          <StatusCards systemState={systemState} isMobile={isMobile} />
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
    fontFamily: "Arial, sans-serif",
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
  subtitle: {
    margin: "6px 0 0 0",
    color: "#94a3b8",
    fontSize: "14px",
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
    gridTemplateRows: "minmax(420px, 1fr) auto auto",
    minHeight: 0,
  },
};
