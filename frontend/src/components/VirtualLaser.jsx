import { useRef, useEffect } from "react";

/**
 * VirtualLaser — Camera-view turret aim visualization
 *
 * Shows a miniature representation of the camera's field of view with:
 * - Red crosshair = target pixel position (where YOLO says the body part is)
 * - Green laser dot = where the math says the laser is actually hitting (reverse-projected)
 * - Yellow line = error between target and laser
 * - Fading trail of recent laser positions
 * - Numerical readout of angles, depth, and pixel positions
 *
 * This lets you see EXACTLY where the laser should hit relative to the target.
 */
export default function VirtualLaser({ systemState }) {
  const canvasRef = useRef(null);
  const trailRef = useRef([]); // {lx, ly} recent virtual laser positions
  const animRef = useRef(null);

  const debug = systemState.debug || {};
  const targetX = debug.targetPx?.[0] || 0;
  const targetY = debug.targetPx?.[1] || 0;
  const vlaserX = debug.vlaserPx?.[0] || 0;
  const vlaserY = debug.vlaserPx?.[1] || 0;
  const frameW = debug.frameW || 640;
  const frameH = debug.frameH || 480;
  const yaw = systemState.yaw ?? 90;
  const pitch = systemState.pitch ?? 90;
  const depthCm = debug.depthCm || 0;

  // Update trail with virtual laser position
  useEffect(() => {
    if (vlaserX > 0 || vlaserY > 0) {
      const trail = trailRef.current;
      trail.push({ x: vlaserX, y: vlaserY });
      if (trail.length > 40) trail.shift();
    }
  }, [vlaserX, vlaserY]);

  // Canvas rendering
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    const dpr = window.devicePixelRatio || 1;

    function draw() {
      const rect = canvas.getBoundingClientRect();
      const w = rect.width;
      const h = rect.height;

      canvas.width = w * dpr;
      canvas.height = h * dpr;
      ctx.scale(dpr, dpr);

      // Clear
      ctx.fillStyle = "#080d17";
      ctx.fillRect(0, 0, w, h);

      // Margins
      const mx = 8, my = 8;
      const fw = w - mx * 2;
      const fh = h - my * 2;

      // Scale from camera pixels to canvas pixels
      const scaleX = fw / frameW;
      const scaleY = fh / frameH;
      const scale = Math.min(scaleX, scaleY);

      // Center the view
      const viewW = frameW * scale;
      const viewH = frameH * scale;
      const ox = mx + (fw - viewW) / 2; // origin x
      const oy = my + (fh - viewH) / 2; // origin y

      const toX = (px) => ox + px * scale;
      const toY = (py) => oy + py * scale;

      // ── Camera frame border ──────────────────────────────
      ctx.strokeStyle = "#1e293b";
      ctx.lineWidth = 1;
      ctx.strokeRect(ox, oy, viewW, viewH);

      // ── Grid (4×3 divisions) ─────────────────────────────
      ctx.strokeStyle = "#111827";
      ctx.lineWidth = 0.5;
      for (let i = 1; i < 4; i++) {
        const gx = ox + (viewW * i) / 4;
        ctx.beginPath();
        ctx.moveTo(gx, oy);
        ctx.lineTo(gx, oy + viewH);
        ctx.stroke();
      }
      for (let i = 1; i < 3; i++) {
        const gy = oy + (viewH * i) / 3;
        ctx.beginPath();
        ctx.moveTo(ox, gy);
        ctx.lineTo(ox + viewW, gy);
        ctx.stroke();
      }

      // ── Center crosshair (frame center) ──────────────────
      const ccx = toX(frameW / 2);
      const ccy = toY(frameH / 2);
      ctx.strokeStyle = "#334155";
      ctx.lineWidth = 1;
      ctx.setLineDash([3, 3]);
      ctx.beginPath();
      ctx.moveTo(ccx, oy);
      ctx.lineTo(ccx, oy + viewH);
      ctx.moveTo(ox, ccy);
      ctx.lineTo(ox + viewW, ccy);
      ctx.stroke();
      ctx.setLineDash([]);

      // ── Trail (fading green dots) ─────────────────────────
      const trail = trailRef.current;
      for (let i = 0; i < trail.length; i++) {
        const t = trail[i];
        const alpha = ((i + 1) / trail.length) * 0.35;
        const tx = toX(t.x);
        const ty = toY(t.y);

        if (tx >= ox && tx <= ox + viewW && ty >= oy && ty <= oy + viewH) {
          ctx.beginPath();
          ctx.arc(tx, ty, 2, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(34, 197, 94, ${alpha})`;
          ctx.fill();
        }
      }

      // ── Target position (red crosshair — where we WANT to hit) ──
      const txp = toX(targetX);
      const typ = toY(targetY);

      if (targetX > 0 || targetY > 0) {
        // Crosshair arms
        ctx.strokeStyle = "rgba(239, 68, 68, 0.8)";
        ctx.lineWidth = 1.5;
        const arm = 12;
        ctx.beginPath();
        ctx.moveTo(txp - arm, typ);
        ctx.lineTo(txp + arm, typ);
        ctx.moveTo(txp, typ - arm);
        ctx.lineTo(txp, typ + arm);
        ctx.stroke();
        // Circle
        ctx.beginPath();
        ctx.arc(txp, typ, 8, 0, Math.PI * 2);
        ctx.strokeStyle = "rgba(239, 68, 68, 0.5)";
        ctx.lineWidth = 1;
        ctx.stroke();
      }

      // ── Virtual laser position (green dot — where laser ACTUALLY hits) ──
      const vlx = toX(vlaserX);
      const vly = toY(vlaserY);

      if (vlaserX > 0 || vlaserY > 0) {
        // Error line (yellow) connecting target to laser
        if (targetX > 0) {
          ctx.beginPath();
          ctx.moveTo(txp, typ);
          ctx.lineTo(vlx, vly);
          ctx.strokeStyle = "rgba(250, 204, 21, 0.4)";
          ctx.lineWidth = 1;
          ctx.setLineDash([4, 3]);
          ctx.stroke();
          ctx.setLineDash([]);
        }

        // Glow
        const glow = ctx.createRadialGradient(vlx, vly, 0, vlx, vly, 16);
        glow.addColorStop(0, "rgba(34, 197, 94, 0.5)");
        glow.addColorStop(1, "rgba(34, 197, 94, 0)");
        ctx.fillStyle = glow;
        ctx.fillRect(vlx - 16, vly - 16, 32, 32);

        // Green dot
        ctx.beginPath();
        ctx.arc(vlx, vly, 4, 0, Math.PI * 2);
        ctx.fillStyle = "#22c55e";
        ctx.fill();
        ctx.strokeStyle = "#86efac";
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }

      // ── Labels ──────────────────────────────────────────────
      ctx.font = "10px 'JetBrains Mono', monospace";
      ctx.textAlign = "left";

      // Top-left: servo angles
      const lx = ox + 6, ly = oy + 14;
      ctx.fillStyle = "#64748b";
      ctx.fillText(`Pan: ${yaw}°  Tilt: ${pitch}°`, lx, ly);
      if (depthCm > 0) {
        ctx.fillText(`Depth: ${depthCm}cm`, lx, ly + 13);
      }

      // Bottom-left: pixel error
      if (targetX > 0 && vlaserX > 0) {
        const errX = Math.round(vlaserX - targetX);
        const errY = Math.round(vlaserY - targetY);
        const errDist = Math.round(
          Math.sqrt(errX * errX + errY * errY)
        );
        ctx.fillStyle = errDist > 50 ? "#f97316" : errDist > 20 ? "#eab308" : "#22c55e";
        ctx.fillText(
          `Error: ${errDist}px (${errX > 0 ? "+" : ""}${errX}, ${errY > 0 ? "+" : ""}${errY})`,
          ox + 6,
          oy + viewH - 6
        );
      }

      // Top-right: target mode
      ctx.textAlign = "right";
      ctx.fillStyle = "#94a3b8";
      ctx.fillText(
        `${(systemState.targetMode || "chest").toUpperCase()}`,
        ox + viewW - 6,
        oy + 14
      );

      animRef.current = requestAnimationFrame(draw);
    }

    draw();

    return () => {
      if (animRef.current) cancelAnimationFrame(animRef.current);
    };
  }, [yaw, pitch, targetX, targetY, vlaserX, vlaserY, frameW, frameH, depthCm, systemState.targetMode]);

  return (
    <div style={card}>
      <div style={headerRow}>
        <h3 style={title}>Virtual Laser</h3>
        <div style={legendRow}>
          <span style={legendItem}>
            <span style={{ ...dot, background: "transparent", border: "1.5px solid #ef4444", boxSizing: "border-box" }} />
            Target
          </span>
          <span style={legendItem}>
            <span style={{ ...dot, background: "#22c55e" }} />
            Laser
          </span>
          <span style={legendItem}>
            <span style={{ ...dot, background: "#facc15", width: "12px", height: "2px", borderRadius: "1px" }} />
            Error
          </span>
        </div>
      </div>
      <canvas
        ref={canvasRef}
        style={{
          width: "100%",
          height: "220px",
          borderRadius: "6px",
          border: "1px solid #1e293b",
        }}
      />
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
  margin: 0,
  fontSize: "18px",
  color: "#f8fafc",
};

const headerRow = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  marginBottom: "12px",
};

const legendRow = {
  display: "flex",
  gap: "14px",
  fontSize: "11px",
  color: "#94a3b8",
};

const legendItem = {
  display: "flex",
  alignItems: "center",
  gap: "5px",
};

const dot = {
  width: "8px",
  height: "8px",
  borderRadius: "50%",
  display: "inline-block",
};
