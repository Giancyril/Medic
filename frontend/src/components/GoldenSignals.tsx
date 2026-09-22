import { useRef, useEffect } from "react";
import type { GoldenSignalsData, SignalTimeline } from "../types/incident";

interface Props {
  data: GoldenSignalsData;
}

function getValueClass(val: number, warn: number, crit: number): string {
  if (val >= crit) return "crit";
  if (val >= warn) return "warn";
  return "ok";
}

function Sparkline({ data, color, height = 44 }: { data: number[]; color: string; height?: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || data.length < 2) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const w = canvas.width;
    const h = canvas.height;
    const max = Math.max(...data) || 1;
    const min = Math.min(...data);
    const range = max - min || 1;

    ctx.clearRect(0, 0, w, h);

    // gradient fill
    const grad = ctx.createLinearGradient(0, 0, 0, h);
    grad.addColorStop(0, color + "44");
    grad.addColorStop(1, color + "00");

    const pts = data.map((v, i) => ({
      x: (i / (data.length - 1)) * w,
      y: h - ((v - min) / range) * (h - 4) - 2,
    }));

    ctx.beginPath();
    ctx.moveTo(pts[0].x, pts[0].y);
    for (let i = 1; i < pts.length; i++) {
      const cpx = (pts[i - 1].x + pts[i].x) / 2;
      ctx.bezierCurveTo(cpx, pts[i - 1].y, cpx, pts[i].y, pts[i].x, pts[i].y);
    }
    ctx.lineTo(w, h);
    ctx.lineTo(0, h);
    ctx.closePath();
    ctx.fillStyle = grad;
    ctx.fill();

    // line
    ctx.beginPath();
    ctx.moveTo(pts[0].x, pts[0].y);
    for (let i = 1; i < pts.length; i++) {
      const cpx = (pts[i - 1].x + pts[i].x) / 2;
      ctx.bezierCurveTo(cpx, pts[i - 1].y, cpx, pts[i].y, pts[i].x, pts[i].y);
    }
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.stroke();
  }, [data, color, height]);

  return (
    <canvas
      ref={canvasRef}
      width={180}
      height={height}
      style={{ width: "100%", height: `${height}px`, display: "block" }}
    />
  );
}

function MultiSparkline({ timeline }: { timeline: SignalTimeline }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    const series = [
      { data: timeline.error_rate,       color: "#ff4757", label: "Error %" },
      { data: timeline.latency_p99,      color: "#f59e0b", label: "P99 ms" },
      { data: timeline.memory_saturation, color: "#8b5cf6", label: "Mem %" },
    ];

    series.forEach(({ data, color }) => {
      if (data.length < 2) return;
      const max = Math.max(...data) || 1;
      const min = Math.min(...data);
      const range = max - min || 1;
      const pts = data.map((v, i) => ({
        x: (i / (data.length - 1)) * w,
        y: h - ((v - min) / range) * (h - 8) - 4,
      }));

      ctx.beginPath();
      ctx.moveTo(pts[0].x, pts[0].y);
      for (let i = 1; i < pts.length; i++) {
        const cpx = (pts[i - 1].x + pts[i].x) / 2;
        ctx.bezierCurveTo(cpx, pts[i - 1].y, cpx, pts[i].y, pts[i].x, pts[i].y);
      }
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5;
      ctx.stroke();
    });
  }, [timeline]);

  return (
    <canvas
      ref={canvasRef}
      width={600}
      height={80}
      style={{ width: "100%", height: "80px", display: "block" }}
    />
  );
}

export function GoldenSignals({ data }: Props) {
  const s = data.signals;

  return (
    <div className="card">
      <div className="card-title">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
        Golden Signals — {data.service}/{data.namespace}
      </div>

      <div className="signal-grid">
        <div className="signal-card">
          <div className="signal-label">Request Rate</div>
          <div className="signal-value ok">{s.request_rate_rps.toFixed(1)}<span style={{ fontSize: "12px", fontWeight: 400, marginLeft: "3px" }}>rps</span></div>
          <Sparkline data={[s.request_rate_rps * 0.8, s.request_rate_rps * 0.9, s.request_rate_rps * 1.1, s.request_rate_rps]} color="#10b981" />
        </div>

        <div className="signal-card">
          <div className="signal-label">Error Rate</div>
          <div className={`signal-value ${getValueClass(s.error_rate_pct, 5, 15)}`}>
            {s.error_rate_pct.toFixed(1)}<span style={{ fontSize: "12px", fontWeight: 400, marginLeft: "3px" }}>%</span>
          </div>
          <Sparkline data={data.timeline.error_rate} color="#ff4757" />
        </div>

        <div className="signal-card">
          <div className="signal-label">Latency P99</div>
          <div className={`signal-value ${getValueClass(s.latency_p99_ms, 500, 1000)}`}>
            {s.latency_p99_ms}<span style={{ fontSize: "12px", fontWeight: 400, marginLeft: "3px" }}>ms</span>
          </div>
          <Sparkline data={data.timeline.latency_p99} color="#f59e0b" />
          <div className="signal-sub">P50: {s.latency_p50_ms}ms · P95: {s.latency_p95_ms}ms</div>
        </div>

        <div className="signal-card">
          <div className="signal-label">Memory</div>
          <div className={`signal-value ${getValueClass(s.memory_saturation_pct, 75, 90)}`}>
            {s.memory_saturation_pct.toFixed(0)}<span style={{ fontSize: "12px", fontWeight: 400, marginLeft: "3px" }}>%</span>
          </div>
          <Sparkline data={data.timeline.memory_saturation} color="#8b5cf6" />
          <div className="signal-sub">CPU: {s.cpu_saturation_pct.toFixed(0)}%</div>
        </div>
      </div>

      <div style={{ marginTop: "16px" }}>
        <div className="section-title" style={{ marginBottom: "8px", fontSize: "10px" }}>
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
          Correlated Metrics Timeline
          <span style={{ marginLeft: "4px", fontSize: "10px" }}>
            <span style={{ color: "#ff4757" }}>— Error</span>&nbsp;
            <span style={{ color: "#f59e0b" }}>— P99</span>&nbsp;
            <span style={{ color: "#8b5cf6" }}>— Mem</span>
          </span>
        </div>
        <div className="chart-container">
          <div style={{ background: "var(--bg-elevated)", borderRadius: "var(--radius-sm)", padding: "8px 8px 4px", border: "1px solid var(--border)" }}>
            <MultiSparkline timeline={data.timeline} />
          </div>
          <div className="chart-labels">
            {data.timeline.timestamps.filter((_, i, a) => i === 0 || i === Math.floor(a.length / 2) || i === a.length - 1).map((ts, i) => (
              <span key={i}>{new Date(ts).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false })}</span>
            ))}
          </div>
        </div>
        {data.deployment_marker && (
          <div style={{ marginTop: "6px", display: "flex", alignItems: "center", gap: "6px", fontSize: "11px" }}>
            <span style={{ width: "10px", height: "1px", background: "var(--accent-cyan)", display: "inline-block" }} />
            <span style={{ color: "var(--accent-cyan)" }}>Deploy: {data.deployment_marker.revision}</span>
            <span style={{ color: "var(--text-muted)" }}>{data.deployment_marker.message}</span>
          </div>
        )}
      </div>
    </div>
  );
}
