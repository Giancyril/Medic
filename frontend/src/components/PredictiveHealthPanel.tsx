import React, { useState, useEffect } from "react";
import {
  TrendingUp,
  Clock,
    Layers,
  PhoneCall,
  CheckCircle,
  RefreshCw,
} from "lucide-react";
import { api } from "../api/client";
import type {
  ClusterPredictionSummary,
  IncidentCluster,
  NoiseReductionStats,
  OnCallRosterStatus,
} from "../types/day3";

interface Props {
  incidentId?: string;
  service?: string;
}

export const PredictiveHealthPanel: React.FC<Props> = ({ incidentId }) => {
  const [predictionSummary, setPredictionSummary] = useState<ClusterPredictionSummary | null>(null);
  const [clusters, setClusters] = useState<IncidentCluster[]>([]);
  const [stats, setStats] = useState<NoiseReductionStats | null>(null);
  const [oncall, setOnCall] = useState<OnCallRosterStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [pagingInProgress, setPagingInProgress] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<"forecasts" | "grouping" | "oncall">("forecasts");

  const loadData = async () => {
    setLoading(true);
    try {
      const [predData, clusterData, statsData, oncallData] = await Promise.all([
        api.prediction.getForecasts(),
        api.grouping.getClusters(),
        api.grouping.getStats(),
        api.oncall.getStatus(),
      ]);
      setPredictionSummary(predData);
      setClusters(clusterData.clusters);
      setStats(statsData);
      setOnCall(oncallData);
    } catch (err) {
      console.error("Failed to load predictive health data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handlePageDispatch = async () => {
    if (!incidentId) return;
    setPagingInProgress(true);
    try {
      await api.oncall.page(incidentId, 1, "Dispatched from Predictive Health Console");
      const updated = await api.oncall.getStatus();
      setOnCall(updated);
    } catch (err) {
      console.error("Failed to dispatch page:", err);
    } finally {
      setPagingInProgress(false);
    }
  };

  const handleAcknowledge = async (pageId: string) => {
    try {
      await api.oncall.acknowledge(pageId);
      const updated = await api.oncall.getStatus();
      setOnCall(updated);
    } catch (err) {
      console.error("Failed to ack page:", err);
    }
  };

  return (
    <div className="card" style={{ padding: "18px", marginTop: "16px" }}>
      {/* Top Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <TrendingUp size={18} color="var(--accent-purple, #a855f7)" />
          <h3 style={{ margin: 0, fontSize: "14px", fontWeight: 600 }}>
            Predictive Anomaly, Alert Grouping & On-Call Health
          </h3>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          {/* Sub-tab navigation */}
          <div style={{ display: "flex", background: "rgba(0,0,0,0.3)", borderRadius: "6px", padding: "2px", border: "1px solid var(--border)" }}>
            <button
              onClick={() => setActiveTab("forecasts")}
              style={{
                background: activeTab === "forecasts" ? "var(--bg-card)" : "transparent",
                border: "none",
                color: activeTab === "forecasts" ? "var(--text-primary)" : "var(--text-muted)",
                padding: "4px 10px",
                fontSize: "11px",
                fontWeight: 600,
                borderRadius: "4px",
                cursor: "pointer",
              }}
            >
              Failure Forecasts (TTF)
            </button>
            <button
              onClick={() => setActiveTab("grouping")}
              style={{
                background: activeTab === "grouping" ? "var(--bg-card)" : "transparent",
                border: "none",
                color: activeTab === "grouping" ? "var(--text-primary)" : "var(--text-muted)",
                padding: "4px 10px",
                fontSize: "11px",
                fontWeight: 600,
                borderRadius: "4px",
                cursor: "pointer",
              }}
            >
              Alert Deduplication ({stats?.noise_reduction_pct || 0}%)
            </button>
            <button
              onClick={() => setActiveTab("oncall")}
              style={{
                background: activeTab === "oncall" ? "var(--bg-card)" : "transparent",
                border: "none",
                color: activeTab === "oncall" ? "var(--text-primary)" : "var(--text-muted)",
                padding: "4px 10px",
                fontSize: "11px",
                fontWeight: 600,
                borderRadius: "4px",
                cursor: "pointer",
              }}
            >
              On-Call Roster
            </button>
          </div>

          <button className="btn btn-ghost btn-sm" onClick={loadData} disabled={loading} title="Refresh Predictions">
            <RefreshCw size={12} className={loading ? "spin" : ""} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Tab 1: Predictive Failure Forecasts & Time-to-Failure (TTF) */}
      {activeTab === "forecasts" && (
        <div>
          {predictionSummary && (
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px", padding: "10px 14px", background: "rgba(0,0,0,0.25)", borderRadius: "6px", border: "1px solid var(--border)" }}>
              <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                Cluster Systemic Risk Index:{" "}
                <strong style={{ color: predictionSummary.systemic_risk_index > 0.5 ? "#ef4444" : "#10b981", fontSize: "13px" }}>
                  {(predictionSummary.systemic_risk_index * 100).toFixed(0)}%
                </strong>{" "}
                · {predictionSummary.imminent_breach_count} Imminent Outages Predicted
              </div>
              <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                Model: Linear/Exponential Trend Extrapolation (95% CI)
              </div>
            </div>
          )}

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
            {predictionSummary?.forecasts.map((f, i) => {
              const isCrit = f.urgency === "critical";
              const isElev = f.urgency === "elevated";
              const borderColor = isCrit ? "#ef4444" : isElev ? "#f59e0b" : "var(--border)";
              const bg = isCrit ? "rgba(239, 68, 68, 0.08)" : isElev ? "rgba(245, 158, 11, 0.06)" : "var(--bg-card)";

              return (
                <div
                  key={i}
                  style={{
                    padding: "12px 14px",
                    borderRadius: "6px",
                    border: `1px solid ${borderColor}`,
                    background: bg,
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "6px" }}>
                    <div>
                      <div style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-primary)" }}>
                        {f.service} // {f.metric_name}
                      </div>
                      <div style={{ fontSize: "11px", color: "var(--text-muted)", marginTop: "2px" }}>
                        Slope: {f.slope_per_second > 0 ? `+${f.slope_per_second}` : f.slope_per_second} {f.unit}/sec
                      </div>
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <div
                        style={{
                          fontSize: "12px",
                          fontWeight: 700,
                          color: isCrit ? "#ef4444" : isElev ? "#f59e0b" : "#10b981",
                          display: "flex",
                          alignItems: "center",
                          gap: "4px",
                          justifyContent: "flex-end",
                        }}
                      >
                        <Clock size={12} />
                        TTF: {f.ttf_human}
                      </div>
                      <div style={{ fontSize: "10px", color: "var(--text-muted)", marginTop: "2px" }}>
                        Confidence: {(f.confidence_score * 100).toFixed(0)}%
                      </div>
                    </div>
                  </div>

                  <div style={{ display: "flex", gap: "8px", margin: "10px 0", fontSize: "11px" }}>
                    <div style={{ flex: 1, padding: "4px 8px", background: "rgba(0,0,0,0.3)", borderRadius: "4px" }}>
                      <div style={{ color: "var(--text-muted)", fontSize: "9px" }}>CURRENT</div>
                      <div style={{ fontWeight: 600 }}>{f.current_value} {f.unit}</div>
                    </div>
                    <div style={{ flex: 1, padding: "4px 8px", background: "rgba(0,0,0,0.3)", borderRadius: "4px" }}>
                      <div style={{ color: "var(--text-muted)", fontSize: "9px" }}>PREDICTED +5M</div>
                      <div style={{ fontWeight: 600, color: isCrit ? "#ef4444" : "inherit" }}>
                        {f.predicted_value_5m} {f.unit}
                      </div>
                    </div>
                    <div style={{ flex: 1, padding: "4px 8px", background: "rgba(0,0,0,0.3)", borderRadius: "4px" }}>
                      <div style={{ color: "var(--text-muted)", fontSize: "9px" }}>CRITICAL THRESHOLD</div>
                      <div style={{ fontWeight: 600, color: "var(--text-secondary)" }}>
                        {f.threshold_critical} {f.unit}
                      </div>
                    </div>
                  </div>

                  <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>
                    {f.summary}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Tab 2: Intelligent Alert Grouping & Deduplication */}
      {activeTab === "grouping" && (
        <div>
          {stats && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "10px", marginBottom: "14px" }}>
              <div style={{ padding: "10px", background: "rgba(0,0,0,0.25)", borderRadius: "6px", border: "1px solid var(--border)" }}>
                <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>TOTAL RAW ALERTS</div>
                <div style={{ fontSize: "16px", fontWeight: 700, marginTop: "2px" }}>{stats.total_raw_alerts}</div>
              </div>
              <div style={{ padding: "10px", background: "rgba(0,0,0,0.25)", borderRadius: "6px", border: "1px solid var(--border)" }}>
                <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>CORRELATED CLUSTERS</div>
                <div style={{ fontSize: "16px", fontWeight: 700, marginTop: "2px", color: "var(--accent-cyan)" }}>
                  {stats.grouped_incidents}
                </div>
              </div>
              <div style={{ padding: "10px", background: "rgba(0,0,0,0.25)", borderRadius: "6px", border: "1px solid var(--border)" }}>
                <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>SUPPRESSED DUPLICATES</div>
                <div style={{ fontSize: "16px", fontWeight: 700, marginTop: "2px", color: "var(--accent-amber)" }}>
                  {stats.duplicate_alerts_suppressed}
                </div>
              </div>
              <div style={{ padding: "10px", background: "rgba(16, 185, 129, 0.1)", borderRadius: "6px", border: "1px solid rgba(16, 185, 129, 0.3)" }}>
                <div style={{ fontSize: "10px", color: "#10b981", fontWeight: 600 }}>NOISE REDUCTION</div>
                <div style={{ fontSize: "16px", fontWeight: 700, marginTop: "2px", color: "#10b981" }}>
                  {stats.noise_reduction_pct}%
                </div>
              </div>
            </div>
          )}

          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {clusters.map((c) => (
              <div key={c.cluster_id} style={{ padding: "12px 14px", background: "rgba(0,0,0,0.25)", borderRadius: "6px", border: "1px solid var(--border)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <Layers size={14} color="var(--accent-cyan)" />
                    <span style={{ fontSize: "13px", fontWeight: 600 }}>{c.title}</span>
                  </div>
                  <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                    <span className="status-pill" style={{ fontSize: "10px" }}>
                      {c.alerts_count} Alerts Clustered
                    </span>
                    <span style={{ fontSize: "11px", color: "#10b981", fontWeight: 600 }}>
                      {c.noise_reduction_pct}% Noise Cut
                    </span>
                  </div>
                </div>

                <div style={{ fontSize: "11px", color: "var(--text-muted)", marginBottom: "8px" }}>
                  Root Cause Candidate: <strong style={{ color: "var(--text-secondary)" }}>{c.root_cause_candidate}</strong> · Primary: <code>{c.primary_service}</code>
                </div>

                {/* Sub-alerts pills */}
                <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                  {c.alerts.map((alt) => (
                    <div
                      key={alt.alert_id}
                      style={{
                        padding: "3px 8px",
                        borderRadius: "4px",
                        background: alt.is_duplicate ? "rgba(245, 158, 11, 0.15)" : "var(--bg-card)",
                        border: `1px solid ${alt.is_duplicate ? "rgba(245, 158, 11, 0.4)" : "var(--border)"}`,
                        fontSize: "10px",
                        color: alt.is_duplicate ? "#f59e0b" : "var(--text-secondary)",
                      }}
                    >
                      {alt.alert_name} {alt.is_duplicate && "(Suppressed Dup)"}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 3: On-Call Roster & Escalation Ladder */}
      {activeTab === "oncall" && (
        <div>
          {oncall && (
            <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: "14px" }}>
              {/* Roster Information */}
              <div style={{ padding: "14px", background: "rgba(0,0,0,0.25)", borderRadius: "6px", border: "1px solid var(--border)" }}>
                <div style={{ fontSize: "11px", textTransform: "uppercase", color: "var(--text-muted)", letterSpacing: "0.05em", marginBottom: "8px" }}>
                  Active Shift: {oncall.current_shift.rotation_name}
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 10px", background: "var(--bg-card)", borderRadius: "4px", border: "1px solid var(--border)" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                      <div style={{ width: "28px", height: "28px", borderRadius: "50%", background: "#06b6d4", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "11px", fontWeight: 700 }}>
                        {oncall.current_shift.primary_responder.avatar_initials}
                      </div>
                      <div>
                        <div style={{ fontSize: "12px", fontWeight: 600 }}>{oncall.current_shift.primary_responder.name}</div>
                        <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>Tier 1 Primary SRE · {oncall.current_shift.primary_responder.email}</div>
                      </div>
                    </div>
                    <span className="status-pill" style={{ color: "#10b981", borderColor: "rgba(16,185,129,0.4)" }}>ON DUTY</span>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 10px", background: "var(--bg-card)", borderRadius: "4px", border: "1px solid var(--border)" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                      <div style={{ width: "28px", height: "28px", borderRadius: "50%", background: "#a855f7", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "11px", fontWeight: 700 }}>
                        {oncall.current_shift.secondary_responder.avatar_initials}
                      </div>
                      <div>
                        <div style={{ fontSize: "12px", fontWeight: 600 }}>{oncall.current_shift.secondary_responder.name}</div>
                        <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>Tier 2 Secondary SRE · {oncall.current_shift.secondary_responder.email}</div>
                      </div>
                    </div>
                    <span className="status-pill" style={{ color: "var(--text-muted)" }}>STANDBY</span>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 10px", background: "var(--bg-card)", borderRadius: "4px", border: "1px solid var(--border)" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                      <div style={{ width: "28px", height: "28px", borderRadius: "50%", background: "#f59e0b", color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "11px", fontWeight: 700 }}>
                        {oncall.current_shift.escalation_lead.avatar_initials}
                      </div>
                      <div>
                        <div style={{ fontSize: "12px", fontWeight: 600 }}>{oncall.current_shift.escalation_lead.name}</div>
                        <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>Tier 3 Incident Commander</div>
                      </div>
                    </div>
                    <span className="status-pill" style={{ color: "var(--text-muted)" }}>ESCALATION</span>
                  </div>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", marginTop: "12px", fontSize: "11px", color: "var(--text-secondary)" }}>
                  <span>Shift Window: 08:00 - 08:00 UTC</span>
                  <span>Mean Time to Acknowledge (MTTA): <strong>{oncall.mtta_seconds_avg}s</strong></span>
                </div>
              </div>

              {/* Page Dispatch & Active Escalations */}
              <div style={{ padding: "14px", background: "rgba(0,0,0,0.25)", borderRadius: "6px", border: "1px solid var(--border)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
                  <div style={{ fontSize: "11px", textTransform: "uppercase", color: "var(--text-muted)", letterSpacing: "0.05em" }}>
                    Active Dispatches & Escalations
                  </div>
                  {incidentId && (
                    <button
                      className="btn btn-primary btn-sm"
                      onClick={handlePageDispatch}
                      disabled={pagingInProgress}
                    >
                      <PhoneCall size={11} className={pagingInProgress ? "spin" : ""} />
                      <span>Dispatch Page</span>
                    </button>
                  )}
                </div>

                {oncall.active_pages.length === 0 ? (
                  <div style={{ fontSize: "12px", color: "var(--text-muted)", padding: "20px 0", textAlign: "center" }}>
                    No active unacknowledged pages. Roster is clear.
                  </div>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                    {oncall.active_pages.map((p) => (
                      <div key={p.page_id} style={{ padding: "8px 10px", background: "rgba(239, 68, 68, 0.1)", border: "1px solid #ef4444", borderRadius: "4px" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <span style={{ fontSize: "11px", fontWeight: 700, color: "#fca5a5" }}>
                            Tier {p.tier_level} Page // {p.responder.name}
                          </span>
                          <button
                            className="btn btn-ghost btn-sm"
                            style={{ fontSize: "10px", padding: "2px 6px" }}
                            onClick={() => handleAcknowledge(p.page_id)}
                          >
                            <CheckCircle size={10} />
                            <span>Ack</span>
                          </button>
                        </div>
                        <div style={{ fontSize: "10px", color: "var(--text-secondary)", marginTop: "4px" }}>
                          {p.notes || "Awaiting responder acknowledgment"}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Recent Resolved Pages */}
                {oncall.recent_resolved_pages.length > 0 && (
                  <div style={{ marginTop: "12px", borderTop: "1px solid var(--border)", paddingTop: "8px" }}>
                    <div style={{ fontSize: "10px", color: "var(--text-muted)", marginBottom: "4px" }}>RECENTLY ACKNOWLEDGED</div>
                    {oncall.recent_resolved_pages.slice(0, 2).map((p) => (
                      <div key={p.page_id} style={{ fontSize: "11px", color: "var(--text-secondary)", display: "flex", justifyContent: "space-between", padding: "2px 0" }}>
                        <span>{p.responder.name} (Tier {p.tier_level})</span>
                        <span style={{ color: "#10b981" }}>✓ Acked</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

