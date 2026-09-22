import { useRef, useEffect } from "react";
import { Activity, Clock, ArrowUpRight } from "lucide-react";
import type { GoldenSignalsData, SignalTimeline } from "../types/incident";

interface Props {
  data: GoldenSignalsData;
}

function getValueClass(val: number, warn: number, crit: number): string {
  if (val >= crit) return "crit";
  if (val >= warn) return "warn";
  return "ok";
}

function Sparkline({ data, color, height = 40 }: { data: number[]; color: string; height?: number }) {
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

    // Gradient fill
    const grad = ctx.createLinearGradient(0, 0, 0, h);
    grad.addColorStop(0, color + "33");
    grad.addColorStop(1, color + "00");

    const pts = data.map((v, i) => ({
      x: (i / (data.length - 1)) * w,
      y: h - ((v - min) / range) * (h - 6) - 3,
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

    // Line stroke
    ctx.beginPath();
    ctx.moveTo(pts[0].x, pts[0].y);
    for (let i = 1; i < pts.length; i++) {
      const cpx = (pts[i - 1].x + pts[i].x) / 2;
      ctx.bezierCurveTo(cpx, pts[i - 1].y, cpx, pts[i].y, pts[i].x, pts[i].y);
    }
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.75;
    ctx.stroke();
  }, [data, color, height]);

  return (
    <canvas
      ref={canvasRef}
      width={200}
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
      { data: timeline.error_rate, color: "#ef4444" },
      { data: timeline.latency_p99, color: "#f59e0b" },
      { data: timeline.memory_saturation, color: "#8b5cf6" },
    ];

    series.forEach(({ data, color }) => {
      if (data.length < 2) return;
      const max = Math.max(...data) || 1;
      const min = Math.min(...data);
      const range = max - min || 1;
      const pts = data.map((v, i) => ({
        x: (i / (data.length - 1)) * w,
        y: h - ((v - min) / range) * (h - 10) - 5,
      }));

      ctx.beginPath();
      ctx.moveTo(pts[0].x, pts[0].y);
      for (let i = 1; i < pts.length; i++) {
        const cpx = (pts[i - 1].x + pts[i].x) / 2;
        ctx.bezierCurveTo(cpx, pts[i - 1].y, cpx, pts[i].y, pts[i].x, pts[i].y);
      }
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.75;
      ctx.stroke();
    });
  }, [timeline]);

  return (
    <canvas
      ref={canvasRef}
      width={600}
      height={76}
      style={{ width: "100%", height: "76px", display: "block" }}
    />
  );
}

export function GoldenSignals({ data }: Props) {
  const s = data.signals;

  return (
    <div className="card">
      <div className="card-title">
        <Activity size={14} strokeWidth={2} style={{ color: "var(--accent-primary)" }} />
        <span>Golden Signals Telemetry — {data.service}/{data.namespace}</span>
      </div>

      <div className="signal-grid">
        <div className="signal-card">
          <div className="signal-label">Throughput</div>
          <div className="signal-value ok">
            {s.request_rate_rps.toFixed(1)}
            <span style={{ fontSize: "11px", fontWeight: 400, marginLeft: "4px", color: "var(--text-muted)" }}>rps</span>
          </div>
          <Sparkline data={[s.request_rate_rps * 0.85, s.request_rate_rps * 0.95, s.request_rate_rps * 1.05, s.request_rate_rps]} color="#10b981" />
        </div>

        <div className="signal-card">
          <div className="signal-label">Error Rate</div>
          <div className={`signal-value ${getValueClass(s.error_rate_pct, 5, 15)}`}>
            {s.error_rate_pct.toFixed(1)}
            <span style={{ fontSize: "11px", fontWeight: 400, marginLeft: "4px", color: "var(--text-muted)" }}>%</span>
          </div>
          <Sparkline data={data.timeline.error_rate} color="#ef4444" />
        </div>

        <div className="signal-card">
          <div className="signal-label">Latency P99</div>
          <div className={`signal-value ${getValueClass(s.latency_p99_ms, 500, 1000)}`}>
            {s.latency_p99_ms}
            <span style={{ fontSize: "11px", fontWeight: 400, marginLeft: "4px", color: "var(--text-muted)" }}>ms</span>
          </div>
          <Sparkline data={data.timeline.latency_p99} color="#f59e0b" />
          <div className="signal-sub">P50: {s.latency_p50_ms}ms · P95: {s.latency_p95_ms}ms</div>
        </div>

        <div className="signal-card">
          <div className="signal-label">Saturation</div>
          <div className={`signal-value ${getValueClass(s.memory_saturation_pct, 75, 90)}`}>
            {s.memory_saturation_pct.toFixed(0)}
            <span style={{ fontSize: "11px", fontWeight: 400, marginLeft: "4px", color: "var(--text-muted)" }}>% mem</span>
          </div>
          <Sparkline data={data.timeline.memory_saturation} color="#8b5cf6" />
          <div className="signal-sub">CPU load: {s.cpu_saturation_pct.toFixed(0)}%</div>
        </div>
      </div>

      <div style={{ marginTop: "18px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
          <div style={{ fontSize: "11px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.5px", color: "var(--text-muted)", display: "flex", alignItems: "center", gap: "6px" }}>
            <Clock size={12} strokeWidth={2} />
            <span>Correlated 15m Metric Series</span>
          </div>
          <div style={{ display: "flex", gap: "12px", fontSize: "11px", fontFamily: "var(--font-mono)" }}>
            <span style={{ color: "#ef4444" }}>● Error %</span>
            <span style={{ color: "#f59e0b" }}>● P99 ms</span>
            <span style={{ color: "#8b5cf6" }}>● Memory %</span>
          </div>
        </div>

        <div style={{ background: "var(--bg-elevated)", borderRadius: "var(--radius)", padding: "10px 12px 6px", border: "1px solid var(--border)" }}>
          <MultiSparkline timeline={data.timeline} />
        </div>

        <div style={{ display: "flex", justifyContent: "space-between", marginTop: "6px", fontSize: "10px", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
          {data.timeline.timestamps
            .filter((_, i, a) => i === 0 || i === Math.floor(a.length / 2) || i === a.length - 1)
            .map((ts, i) => (
              <span key={i}>
                {new Date(ts).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false })}
              </span>
            ))}
        </div>

        {data.deployment_marker && (
          <div style={{ marginTop: "8px", display: "flex", alignItems: "center", gap: "8px", fontSize: "11px", background: "rgba(6, 182, 212, 0.08)", border: "1px solid rgba(6, 182, 212, 0.25)", padding: "6px 10px", borderRadius: "var(--radius-sm)" }}>
            <ArrowUpRight size={13} strokeWidth={2} style={{ color: "var(--accent-cyan)" }} />
            <span style={{ color: "var(--accent-cyan)", fontWeight: 600 }}>Deployment Rollout: {data.deployment_marker.revision}</span>
            <span style={{ color: "var(--text-secondary)" }}>— {data.deployment_marker.message}</span>
          </div>
        )}
      </div>
    </div>
  );
}
