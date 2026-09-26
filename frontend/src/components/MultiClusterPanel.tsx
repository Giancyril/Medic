import React, { useState, useEffect, useCallback } from "react";
import {
  Globe,
  RefreshCw,
  AlertTriangle,
  CheckCircle,
  Zap,
  Activity,
  ArrowRightLeft,
  ShieldOff,
} from "lucide-react";
import { api } from "../api/client";
import type { MultiClusterOverview, ClusterRegion } from "../types/day5";

const STATUS_COLOR: Record<string, string> = {
  healthy: "#10b981",
  degraded: "#f59e0b",
  draining: "#6366f1",
  drained: "#6b7280",
  offline: "#ef4444",
};

const STATUS_LABEL: Record<string, string> = {
  healthy: "Healthy",
  degraded: "Degraded",
  draining: "Draining",
  drained: "Drained",
  offline: "Offline",
};

interface Props {
  incidentService?: string;
}

export const MultiClusterPanel: React.FC<Props> = () => {
  const [overview, setOverview] = useState<MultiClusterOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);

  const fetchOverview = useCallback(async () => {
    try {
      const data = await api.multicluster.getOverview();
      setOverview(data);
    } catch { /* fallback */ } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchOverview();
    const t = setInterval(fetchOverview, 8000);
    return () => clearInterval(t);
  }, [fetchOverview]);

  const handleDrain = async (cluster: ClusterRegion) => {
    setActionInProgress(cluster.cluster_id);
    try {
      const res = await api.multicluster.drain(cluster.cluster_id, "Operator-initiated failover");
      setOverview(res.overview);
    } catch { /* ignore */ } finally {
      setActionInProgress(null);
    }
  };

  const handleRestore = async (cluster: ClusterRegion) => {
    setActionInProgress(cluster.cluster_id);
    try {
      const res = await api.multicluster.restore(cluster.cluster_id, 35);
      setOverview(res.overview);
    } catch { /* ignore */ } finally {
      setActionInProgress(null);
    }
  };

  if (loading) {
    return (
      <div style={{ display: "flex", alignItems: "center", gap: "8px", padding: "32px", color: "var(--text-muted)" }}>
        <RefreshCw size={16} />
        <span>Loading multi-cluster topology…</span>
      </div>
    );
  }
  if (!overview) return null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <Globe size={18} color="#6366f1" />
          <div>
            <h2 style={{ margin: 0, fontSize: "15px", fontWeight: 700, color: "var(--text-primary)" }}>
              Multi-Region Cluster Failover
            </h2>
            <p style={{ margin: 0, fontSize: "11px", color: "var(--text-muted)", marginTop: "2px" }}>
              {overview.dns_routing_policy}
            </p>
          </div>
        </div>
        <div style={{ display: "flex", gap: "16px", alignItems: "center" }}>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: "20px", fontWeight: 700, color: "#10b981" }}>{overview.healthy_clusters}/{overview.total_clusters}</div>
            <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>Healthy Regions</div>
          </div>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: "20px", fontWeight: 700, color: "#6366f1" }}>{overview.total_ingress_rps.toLocaleString()}</div>
            <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>Global RPS</div>
          </div>
          <button className="btn btn-ghost btn-sm" onClick={fetchOverview} title="Refresh">
            <RefreshCw size={12} />
          </button>
        </div>
      </div>

      {/* Cluster Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: "14px" }}>
        {overview.clusters.map((c) => {
          const statusColor = STATUS_COLOR[c.status] ?? "#6b7280";
          const inProgress = actionInProgress === c.cluster_id;
          return (
            <div key={c.cluster_id} style={{
              background: "var(--surface-elevated)",
              border: `1px solid ${statusColor}33`,
              borderRadius: "10px",
              padding: "16px",
              display: "flex",
              flexDirection: "column",
              gap: "12px",
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    {c.is_primary && (
                      <span style={{ background: "#6366f120", color: "#6366f1", fontSize: "9px", fontWeight: 700, padding: "2px 6px", borderRadius: "4px" }}>
                        PRIMARY
                      </span>
                    )}
                    <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-primary)" }}>{c.name}</span>
                  </div>
                  <div style={{ fontSize: "10px", color: "var(--text-muted)", marginTop: "2px" }}>{c.cloud_provider}</div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                  <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: statusColor, display: "inline-block" }} />
                  <span style={{ fontSize: "11px", fontWeight: 600, color: statusColor }}>{STATUS_LABEL[c.status]}</span>
                </div>
              </div>

              {/* Traffic Weight Bar */}
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                  <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>Global Traffic Weight</span>
                  <span style={{ fontSize: "12px", fontWeight: 700, color: statusColor }}>{c.traffic_weight_pct}%</span>
                </div>
                <div style={{ background: "var(--surface)", borderRadius: "3px", height: "6px", overflow: "hidden" }}>
                  <div style={{ width: `${c.traffic_weight_pct}%`, height: "6px", borderRadius: "3px", background: statusColor, transition: "width 0.6s ease" }} />
                </div>
              </div>

              {/* Metrics Grid */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
                {[
                  { label: "P99 Latency", value: `${c.p99_latency_ms.toFixed(1)} ms`, color: c.p99_latency_ms > 80 ? "#ef4444" : "#10b981" },
                  { label: "Error Rate", value: `${c.error_rate_pct.toFixed(2)}%`, color: c.error_rate_pct > 1 ? "#ef4444" : "#10b981" },
                  { label: "Active Pods", value: `${c.active_pods}`, color: "var(--text-primary)" },
                  { label: "Ingress RPS", value: c.ingress_rps.toLocaleString(), color: "var(--text-primary)" },
                ].map((m) => (
                  <div key={m.label} style={{ background: "var(--surface)", borderRadius: "6px", padding: "8px" }}>
                    <div style={{ fontSize: "9px", color: "var(--text-muted)", marginBottom: "2px" }}>{m.label}</div>
                    <div style={{ fontSize: "13px", fontWeight: 700, color: m.color }}>{m.value}</div>
                  </div>
                ))}
              </div>

              {/* Actions */}
              <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                {c.status !== "drained" ? (
                  <button
                    id={`drain-${c.cluster_id}`}
                    className="btn btn-sm"
                    style={{ background: "#ef444415", color: "#ef4444", border: "1px solid #ef444430", flex: 1, fontSize: "11px" }}
                    onClick={() => handleDrain(c)}
                    disabled={inProgress || c.traffic_weight_pct === 0}
                  >
                    {inProgress ? <RefreshCw size={11} /> : <ShieldOff size={11} />}
                    {inProgress ? "Draining…" : "Drain Traffic"}
                  </button>
                ) : (
                  <button
                    id={`restore-${c.cluster_id}`}
                    className="btn btn-sm"
                    style={{ background: "#10b98115", color: "#10b981", border: "1px solid #10b98130", flex: 1, fontSize: "11px" }}
                    onClick={() => handleRestore(c)}
                    disabled={inProgress}
                  >
                    {inProgress ? <RefreshCw size={11} /> : <CheckCircle size={11} />}
                    {inProgress ? "Restoring…" : "Restore Traffic"}
                  </button>
                )}
                <div style={{ fontSize: "10px", color: "var(--text-muted)", display: "flex", alignItems: "center", gap: "4px" }}>
                  <Activity size={10} />{c.node_count} nodes
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Recent Failover Events */}
      <div style={{ background: "var(--surface-elevated)", border: "1px solid var(--border)", borderRadius: "10px", padding: "16px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "12px" }}>
          <ArrowRightLeft size={14} color="#6366f1" />
          <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-primary)" }}>Recent Failover Events</span>
          <span style={{ marginLeft: "auto", fontSize: "10px", color: "var(--text-muted)" }}>{overview.recent_events.length} events</span>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          {overview.recent_events.slice(0, 5).map((ev) => (
            <div key={ev.event_id} style={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: "6px",
              padding: "10px 12px",
              display: "flex",
              gap: "10px",
              alignItems: "flex-start",
            }}>
              <div style={{ marginTop: "1px" }}>
                {ev.event_type === "drain_initiated" ? (
                  <AlertTriangle size={13} color="#f59e0b" />
                ) : ev.event_type === "traffic_shifted" ? (
                  <Zap size={13} color="#6366f1" />
                ) : (
                  <CheckCircle size={13} color="#10b981" />
                )}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: "11px", color: "var(--text-primary)", lineHeight: "1.4" }}>{ev.summary}</div>
                <div style={{ fontSize: "10px", color: "var(--text-muted)", marginTop: "2px" }}>
                  {ev.initiator} · {new Date(ev.timestamp).toLocaleTimeString()}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default MultiClusterPanel;
