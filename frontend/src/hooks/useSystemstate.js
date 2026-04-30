import { useEffect, useState } from "react";
import { mockSystemData } from "../mocks/mockSystemData";

const STATES = ["Scanning", "Target Detected", "Tracking Locked", "Reacquiring"];

const LOGS_BY_STATE = {
  Scanning: [
    "Idle scan active",
    "Searching for subject",
    "No lock established",
  ],
  "Target Detected": [
    "Subject detected",
    "Pose estimation warming up",
    "Preparing tracking pipeline",
  ],
  "Tracking Locked": [
    "Tracking lock established",
    "Motion stable",
    "Visual indicator active",
  ],
  Reacquiring: [
    "Target temporarily lost",
    "Re-identification in progress",
    "Tracker attempting recovery",
  ],
};

function randomBetween(min, max) {
  return Math.random() * (max - min) + min;
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

export function useSystemState() {
  const [systemState, setSystemState] = useState(mockSystemData);

  useEffect(() => {
    const interval = setInterval(() => {
      setSystemState((prev) => {
        const nextMode =
          Math.random() < 0.18
            ? STATES[Math.floor(Math.random() * STATES.length)]
            : prev.systemState;

        const nextFps = Math.round(clamp(prev.fps + randomBetween(-2, 2), 24, 32));
        const nextConfidence = Number(
          clamp(prev.confidence + randomBetween(-0.06, 0.06), 0.58, 0.98).toFixed(2)
        );

        const nextYaw = Math.round(clamp(prev.yaw + randomBetween(-6, 6), 45, 135));
        const nextPitch = Math.round(clamp(prev.pitch + randomBetween(-4, 4), 30, 100));

        const nextIndicator =
          nextMode === "Tracking Locked"
            ? "Active"
            : nextMode === "Target Detected"
            ? "Armed"
            : "Standby";

        const baseLogs = LOGS_BY_STATE[nextMode];
        const randomLog = baseLogs[Math.floor(Math.random() * baseLogs.length)];

        const nextLogs = [randomLog, ...prev.logs].slice(0, 6);

        return {
          ...prev,
          systemState: nextMode,
          fps: nextFps,
          confidence: nextConfidence,
          yaw: nextYaw,
          pitch: nextPitch,
          indicator: nextIndicator,
          logs: nextLogs,
        };
      });
    }, 1500);

    return () => clearInterval(interval);
  }, []);

  return { systemState, setSystemState };
}