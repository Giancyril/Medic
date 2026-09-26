import React, { useState, useEffect, useCallback } from "react";
import {
  DollarSign,
  RefreshCw,
  TrendingDown,
  AlertTriangle,
  BarChart3,
  Shield,
  Clock,
  Plus,
} from "lucide-react";
import { api } from "../api/client";
import type { FinOpsSummary } from "../types/day5";

const TIER_LABEL: Record<string, string> = {
  tier_1_mission_critical: "Tier 1 — Mission Critical",
  tier_2_core_business: "Tier 2 — Core Business",
  tier_3_internal_support: "Tier 3 — Internal Support",
};
const TIER_COLOR: Record<string, string> = {
  tier_1_mission_critical: "#ef4444",
  tier_2_core_business: "#f59e0b",
  tier_3_internal_support: "#6366f1",
};

const fmt = (v: number) =>
  v >= 1000 ? `$${(v / 1000).toFixed(1)}k` : `$${v.toFixed(0)}`;

interface Props {
  incidentId?: string;
  service?: string;
}

export const FinOpsPanel: React.FC<Props> = ({ incidentId, service }) => {
  const [summaries, setSummaries] = useState<FinOpsSummary[]>([]);
  const [selected, setSelected] = useState<FinOpsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [calculating, setCalculating] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const res = await api.finops.listSummaries();
      setSummaries(res.summaries);
      if (res.summaries.length > 0) {
        const target = incidentId
          ? (res.summaries.find((s) => s.incident_id === incidentId) ?? res.summaries[0])
          : res.summaries[0];
        setSelected(target);
      }
    } catch { /* ignore */ } finally {
      setLoading(false);
    }
  }, [incidentId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleCalculate = async () => {
    if (!service) return;
    setCalculating(true);
    try {
      const summary = await api.finops.calculate(service, 6.5, 9.0, incidentId);
      setSummaries((prev) => {
        const idx = prev.findIndex((s) => s.incident_id === summary.incident_id);
        if (idx >= 0) { const copy = [...prev]; copy[idx] = summary; return copy; }
        return [summary, ...prev];
      });
      setSelected(summary);
    } catch { /* ignore */ } finally {
      setCalculating(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: "flex", alignItems: "center", gap: "8px", padding: "32px", color: "var(--text-muted)" }}>
        <RefreshCw size={16} />
        <span>Loading financial impact data…</span>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <DollarSign size={18} color="#10b981" />
          <div>
            <h2 style={{ margin: 0, fontSize: "15px", fontWeight: 700, color: "var(--text-primary)" }}>
              FinOps &amp; Business Impact
            </h2>
            <p style={{ margin: 0, fontSize: "11px", color: "var(--text-muted)", marginTop: "2px" }}>
              Revenue loss · SLA penalties · Infra cost deltas
            </p>
          </div>
        </div>
        <div style={{ display: "flex", gap: "8px" }}>
          {service && (
            <button className="btn btn-sm btn-primary" onClick={handleCalculate} disabled={calculating} style={{ fontSize: "11px" }}>
              {calculating ? <RefreshCw size={11} /> : <Plus size={11} />}
              {calculating ? "Calculating…" : "Recalculate"}
            </button>
          )}
          <button className="btn btn-ghost btn-sm" onClick={fetchData}>
            <RefreshCw size={12} />
          </button>
        </div>
      </div>

      {/* Summary selector */}
      {summaries.length > 1 && (
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
          {summaries.map((s) => (
            <button
              key={s.incident_id}
              className={`btn btn-sm ${selected?.incident_id === s.incident_id ? "btn-primary" : "btn-ghost"}`}
              onClick={() => setSelected(s)}
              style={{ fontSize: "11px" }}
            >
              {s.service} / {s.incident_id.split("-").slice(0, 3).join("-")}
            </button>
          ))}
        </div>
      )}

      {selected && (() => {
        const tierColor = TIER_COLOR[selected.impact_tier] ?? "#6b7280";
        const bi = selected.business_impact;
        const slaBreached = bi.actual_availability_pct < bi.sla_target_availability_pct;
        return (
          <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
            {/* Top KPI Cards */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))", gap: "10px" }}>
              {[
                { label: "Total Incident Cost", value: fmt(selected.total_incident_cost_usd), color: "#ef4444", icon: <TrendingDown size={14} /> },
                { label: "Revenue Loss", value: fmt(selected.total_financial_loss_usd), color: "#f59e0b", icon: <BarChart3 size={14} /> },
                { label: "ROI Saved (Fast MTTR)", value: fmt(selected.roi_saved_usd), color: "#10b981", icon: <Shield size={14} /> },
                { label: "Infra Cost Delta", value: `$${selected.total_infra_remediation_cost_usd.toFixed(3)}/hr`, color: "#6366f1", icon: <Clock size={14} /> },
              ].map((kpi) => (
                <div key={kpi.label} style={{ background: "var(--surface-elevated)", border: `1px solid ${kpi.color}22`, borderRadius: "10px", padding: "14px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px", color: kpi.color, marginBottom: "6px" }}>
                    {kpi.icon}
                    <span style={{ fontSize: "10px", fontWeight: 600 }}>{kpi.label}</span>
                  </div>
                  <div style={{ fontSize: "20px", fontWeight: 800, color: kpi.color }}>{kpi.value}</div>
                </div>
              ))}
            </div>

            {/* SLA & Business Metrics */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px" }}>
              {/* SLA Status */}
              <div style={{ background: "var(--surface-elevated)", border: "1px solid var(--border)", borderRadius: "10px", padding: "16px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "14px" }}>
                  <Shield size={14} color={slaBreached ? "#ef4444" : "#10b981"} />
                  <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-primary)" }}>SLA Compliance</span>
                  <span style={{ marginLeft: "auto", fontSize: "10px", fontWeight: 700, color: slaBreached ? "#ef4444" : "#10b981" }}>
                    {slaBreached ? "⚠ BREACHED" : "✓ COMPLIANT"}
                  </span>
                </div>
                {[
                  { label: "SLA Target", value: `${bi.sla_target_availability_pct}%`, color: "var(--text-muted)" },
                  { label: "Actual Availability", value: `${bi.actual_availability_pct.toFixed(2)}%`, color: slaBreached ? "#ef4444" : "#10b981" },
                  { label: "SLA Penalty", value: bi.sla_breach_penalty_usd > 0 ? fmt(bi.sla_breach_penalty_usd) : "None", color: bi.sla_breach_penalty_usd > 0 ? "#ef4444" : "#10b981" },
                  { label: "Incident Duration", value: `${bi.incident_duration_minutes.toFixed(1)} min`, color: "var(--text-primary)" },
                ].map((row) => (
                  <div key={row.label} style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid var(--border)" }}>
                    <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>{row.label}</span>
                    <span style={{ fontSize: "11px", fontWeight: 700, color: row.color }}>{row.value}</span>
                  </div>
                ))}
              </div>

              {/* Business Impact */}
              <div style={{ background: "var(--surface-elevated)", border: "1px solid var(--border)", borderRadius: "10px", padding: "16px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "14px" }}>
                  <AlertTriangle size={14} color={tierColor} />
                  <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-primary)" }}>
                    {TIER_LABEL[selected.impact_tier]}
                  </span>
                </div>
                {[
                  { label: "Loss/min Rate", value: `$${bi.revenue_loss_per_minute_usd.toFixed(0)}/min`, color: "#ef4444" },
                  { label: "Cumulative Loss", value: fmt(bi.cumulative_revenue_loss_usd), color: "#f59e0b" },
                  { label: "Failed Transactions", value: bi.estimated_failed_transactions.toLocaleString(), color: "var(--text-primary)" },
                  { label: "Service", value: selected.service, color: "#6366f1" },
                ].map((row) => (
                  <div key={row.label} style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid var(--border)" }}>
                    <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>{row.label}</span>
                    <span style={{ fontSize: "11px", fontWeight: 700, color: row.color }}>{row.value}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Remediation Cost Deltas */}
            {selected.remediation_costs.length > 0 && (
              <div style={{ background: "var(--surface-elevated)", border: "1px solid var(--border)", borderRadius: "10px", padding: "16px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "12px" }}>
                  <BarChart3 size={14} color="#6366f1" />
                  <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-primary)" }}>Remediation Infrastructure Costs</span>
                </div>
                {selected.remediation_costs.map((rc, i) => (
                  <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 12px", background: "var(--surface)", borderRadius: "6px", marginBottom: "6px" }}>
                    <div>
                      <div style={{ fontSize: "11px", fontWeight: 600, color: "var(--text-primary)" }}>{rc.action_type.replaceAll("_", " ")}</div>
                      <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>{rc.resources_added}</div>
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <div style={{ fontSize: "12px", fontWeight: 700, color: "#6366f1" }}>${rc.hourly_cost_delta_usd.toFixed(3)}/hr</div>
                      <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>${rc.monthly_projected_cost_usd.toFixed(2)}/mo</div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Rightsizing Recommendation */}
            <div style={{ background: "#10b98110", border: "1px solid #10b98130", borderRadius: "8px", padding: "12px 14px" }}>
              <div style={{ fontSize: "10px", fontWeight: 700, color: "#10b981", marginBottom: "4px" }}>💡 RIGHTSIZING RECOMMENDATION</div>
              <div style={{ fontSize: "11px", color: "var(--text-primary)" }}>{selected.rightsizing_recommendation}</div>
            </div>
          </div>
        );
      })()}

      {summaries.length === 0 && (
        <div style={{ color: "var(--text-muted)", textAlign: "center", padding: "40px", fontSize: "13px" }}>
          No financial impact data available. Select an incident to calculate business impact.
        </div>
      )}
    </div>
  );
};

export default FinOpsPanel;
