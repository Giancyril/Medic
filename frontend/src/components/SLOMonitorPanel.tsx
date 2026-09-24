import React, { useState, useEffect } from 'react';
import { ShieldAlert, TrendingDown, CheckCircle, AlertTriangle, Flame, Clock } from 'lucide-react';
import { api } from '../api/client';

interface SLOStatusProps {
  service?: string;
}

export const SLOMonitorPanel: React.FC<SLOStatusProps> = ({ service }) => {
  const [slos, setSlos] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchSLOs = async () => {
    try {
      const res = await api.telemetry.getSLOs(service);
      setSlos(res.slos || []);
    } catch (e) {
      console.error("Failed to load SLOs", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSLOs();
    const interval = setInterval(fetchSLOs, 5000);
    return () => clearInterval(interval);
  }, [service]);

  return (
    <div className="card" style={{ padding: "16px 20px", marginBottom: "20px" }}>
      <div className="card-title" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <ShieldAlert size={16} style={{ color: "var(--accent-primary)" }} />
          <span>Multi-Window SLO & Error Budget Monitor</span>
        </div>
        <span style={{ fontSize: "11px", color: "var(--text-muted)", display: "flex", alignItems: "center", gap: "4px" }}>
          <Clock size={12} /> Auto-evaluating (5s window)
        </span>
      </div>

      {loading ? (
        <div style={{ textAlign: "center", padding: "16px", color: "var(--text-muted)", fontSize: "12px" }}>
          Evaluating SLO compliance and burn rates...
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "12px" }}>
          {slos.map((slo) => {
            const isCritical = slo.status === "critical" || slo.is_breached;
            const isWarning = slo.status === "warning";
            const statusColor = isCritical ? "var(--color-critical)" : isWarning ? "var(--color-warning)" : "var(--color-success)";

            return (
              <div
                key={slo.slo_id}
                style={{
                  background: "var(--bg-surface)",
                  border: `1px solid ${isCritical ? "rgba(239, 68, 68, 0.35)" : "var(--border)"}`,
                  borderRadius: "8px",
                  padding: "14px",
                  display: "flex",
                  flexDirection: "column",
                  gap: "10px",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div>
                    <div style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-primary)" }}>{slo.slo_id}</div>
                    <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>Target: {slo.target_pct}% • Svc: {slo.service}</div>
                  </div>
                  <span
                    style={{
                      fontSize: "10px",
                      fontWeight: 600,
                      padding: "2px 7px",
                      borderRadius: "4px",
                      textTransform: "uppercase",
                      background: isCritical ? "rgba(239, 68, 68, 0.15)" : isWarning ? "rgba(245, 158, 11, 0.15)" : "rgba(16, 185, 129, 0.15)",
                      color: statusColor,
                      border: `1px solid ${statusColor}40`,
                    }}
                  >
                    {slo.status}
                  </span>
                </div>

                {/* Progress bar of current compliance */}
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", marginBottom: "4px" }}>
                    <span style={{ color: "var(--text-secondary)" }}>SLI Attainment:</span>
                    <strong style={{ color: statusColor }}>{slo.current_pct}%</strong>
                  </div>
                  <div style={{ width: "100%", height: "6px", background: "var(--bg-base)", borderRadius: "3px", overflow: "hidden" }}>
                    <div
                      style={{
                        width: `${Math.min(100, Math.max(0, slo.current_pct))}%`,
                        height: "100%",
                        background: statusColor,
                        borderRadius: "3px",
                        transition: "width 0.4s ease",
                      }}
                    />
                  </div>
                </div>

                {/* Burn rate stats */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "11px", paddingTop: "6px", borderTop: "1px solid var(--border-subtle)" }}>
                  <span style={{ display: "flex", alignItems: "center", gap: "4px", color: slo.burn_rate > 1.0 ? "var(--color-warning)" : "var(--text-muted)" }}>
                    <Flame size={12} />
                    Burn Rate: <strong>{slo.burn_rate}x</strong>
                  </span>
                  <span style={{ color: "var(--text-muted)" }}>
                    Budget Left: <strong style={{ color: "var(--text-primary)" }}>{slo.error_budget_remaining_pct}%</strong>
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
