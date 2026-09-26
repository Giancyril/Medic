import React, { useState, useEffect, useCallback } from "react";
import {
  Cpu,
  RefreshCw,
  Play,
  PowerOff,
  CheckCircle,
  XCircle,
  ShieldCheck,
  AlertOctagon,
  ToggleLeft,
  ToggleRight,
} from "lucide-react";
import { api } from "../api/client";
import type { SelfHealingPolicy, ClosedLoopExecution, GuardrailStatus } from "../types/day5";

const RISK_COLOR: Record<string, string> = {
  low: "#10b981",
  medium: "#f59e0b",
  high: "#ef4444",
};

const STATUS_COLOR: Record<string, string> = {
  verified_resolved: "#10b981",
  verification_failed_reverted: "#ef4444",
  verifying: "#6366f1",
  pending: "#6b7280",
};

interface Props {
  incidentId?: string;
  service?: string;
}

export const SelfHealingPanel: React.FC<Props> = ({ incidentId }) => {
  const [policies, setPolicies] = useState<SelfHealingPolicy[]>([]);
  const [executions, setExecutions] = useState<ClosedLoopExecution[]>([]);
  const [guardrails, setGuardrails] = useState<GuardrailStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [executingId, setExecutingId] = useState<string | null>(null);
  const [togglingId, setTogglingId] = useState<string | null>(null);

  const fetchAll = useCallback(async () => {
    try {
      const [policiesRes, executionsRes, guardrailRes] = await Promise.all([
        api.selfhealing.listPolicies(),
        api.selfhealing.listExecutions(),
        api.selfhealing.getGuardrails(),
      ]);
      setPolicies(policiesRes.policies);
      setExecutions(executionsRes.executions);
      setGuardrails(guardrailRes);
    } catch { /* ignore */ } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
    const t = setInterval(fetchAll, 10000);
    return () => clearInterval(t);
  }, [fetchAll]);

  const handleToggle = async (policy: SelfHealingPolicy) => {
    setTogglingId(policy.policy_id);
    try {
      const updated = await api.selfhealing.togglePolicy(policy.policy_id, !policy.enabled);
      setPolicies((prev) => prev.map((p) => (p.policy_id === updated.policy_id ? updated : p)));
    } catch { /* ignore */ } finally {
      setTogglingId(null);
    }
  };

  const handleExecute = async (policy: SelfHealingPolicy) => {
    if (!incidentId && !policy.target_service) return;
    setExecutingId(policy.policy_id);
    try {
      const execution = await api.selfhealing.executePolicy(
        policy.policy_id,
        incidentId || `inc-manual-${policy.target_service}`,
      );
      setExecutions((prev) => [execution, ...prev]);
      setPolicies((prev) => prev.map((p) => p.policy_id === policy.policy_id
        ? { ...p, execution_count: p.execution_count + 1, success_count: p.success_count + 1, last_triggered_at: new Date().toISOString() }
        : p
      ));
    } catch { /* ignore */ } finally {
      setExecutingId(null);
    }
  };

  if (loading) {
    return (
      <div style={{ display: "flex", alignItems: "center", gap: "8px", padding: "32px", color: "var(--text-muted)" }}>
        <RefreshCw size={16} />
        <span>Loading self-healing policies…</span>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <Cpu size={18} color="#10b981" />
          <div>
            <h2 style={{ margin: 0, fontSize: "15px", fontWeight: 700, color: "var(--text-primary)" }}>
              Autonomous Self-Healing Engine
            </h2>
            <p style={{ margin: 0, fontSize: "11px", color: "var(--text-muted)", marginTop: "2px" }}>
              Closed-loop remediation with watchdog verification &amp; velocity guardrails
            </p>
          </div>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={fetchAll}>
          <RefreshCw size={12} />
        </button>
      </div>

      {/* Guardrail Status Bar */}
      {guardrails && (
        <div style={{
          background: guardrails.rate_limit_exceeded ? "#ef444415" : "#10b98115",
          border: `1px solid ${guardrails.rate_limit_exceeded ? "#ef4444" : "#10b981"}30`,
          borderRadius: "8px",
          padding: "10px 14px",
          display: "flex",
          alignItems: "center",
          gap: "12px",
          flexWrap: "wrap",
        }}>
          {guardrails.rate_limit_exceeded
            ? <AlertOctagon size={14} color="#ef4444" />
            : <ShieldCheck size={14} color="#10b981" />
          }
          <span style={{ fontSize: "11px", fontWeight: 700, color: guardrails.rate_limit_exceeded ? "#ef4444" : "#10b981" }}>
            {guardrails.rate_limit_exceeded ? "VELOCITY LIMIT EXCEEDED — Human Review Required" : "Guardrails Active — Safe Operation Window"}
          </span>
          <div style={{ marginLeft: "auto", display: "flex", gap: "16px" }}>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: "16px", fontWeight: 700, color: "var(--text-primary)" }}>
                {guardrails.actions_in_current_window}/{guardrails.velocity_limit_per_15m}
              </div>
              <div style={{ fontSize: "9px", color: "var(--text-muted)" }}>Actions / 15m</div>
            </div>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: "16px", fontWeight: 700, color: "#6366f1" }}>
                {guardrails.blast_radius_cap}%
              </div>
              <div style={{ fontSize: "9px", color: "var(--text-muted)" }}>Blast Radius Cap</div>
            </div>
          </div>
        </div>
      )}

      {/* Policy Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: "12px" }}>
        {policies.map((p) => {
          const riskColor = RISK_COLOR[p.risk_level] ?? "#6b7280";
          const isExecuting = executingId === p.policy_id;
          const isToggling = togglingId === p.policy_id;
          const successRate = p.execution_count > 0 ? Math.round((p.success_count / p.execution_count) * 100) : 100;
          return (
            <div key={p.policy_id} style={{
              background: "var(--surface-elevated)",
              border: `1px solid ${p.enabled ? riskColor + "33" : "var(--border)"}`,
              borderRadius: "10px",
              padding: "16px",
              display: "flex",
              flexDirection: "column",
              gap: "10px",
              opacity: p.enabled ? 1 : 0.6,
            }}>
              {/* Policy Header */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-primary)", marginBottom: "2px" }}>
                    {p.name}
                  </div>
                  <div style={{ fontSize: "10px", color: "#6366f1", fontFamily: "monospace" }}>{p.target_service}</div>
                </div>
                <button
                  id={`toggle-${p.policy_id}`}
                  onClick={() => handleToggle(p)}
                  disabled={isToggling}
                  style={{ background: "none", border: "none", cursor: "pointer", padding: "4px", color: p.enabled ? "#10b981" : "#6b7280" }}
                >
                  {p.enabled ? <ToggleRight size={22} /> : <ToggleLeft size={22} />}
                </button>
              </div>

              {/* Trigger Condition */}
              <div style={{ background: "var(--surface)", borderRadius: "6px", padding: "8px 10px", fontSize: "10px", color: "var(--text-muted)", fontFamily: "monospace", lineHeight: "1.5" }}>
                TRIGGER: {p.trigger_condition}
              </div>

              {/* Stats Row */}
              <div style={{ display: "flex", gap: "10px" }}>
                {[
                  { label: "Executions", value: `${p.execution_count}` },
                  { label: "Success Rate", value: `${successRate}%`, color: successRate >= 90 ? "#10b981" : "#f59e0b" },
                  { label: "Cooldown", value: `${p.cooldown_minutes}m` },
                  { label: "Risk", value: p.risk_level.toUpperCase(), color: riskColor },
                ].map((s) => (
                  <div key={s.label} style={{ flex: 1, background: "var(--surface)", borderRadius: "6px", padding: "6px", textAlign: "center" }}>
                    <div style={{ fontSize: "12px", fontWeight: 700, color: s.color || "var(--text-primary)" }}>{s.value}</div>
                    <div style={{ fontSize: "9px", color: "var(--text-muted)" }}>{s.label}</div>
                  </div>
                ))}
              </div>

              {/* Execute Button */}
              <button
                id={`execute-${p.policy_id}`}
                className="btn btn-sm"
                style={{
                  background: p.enabled ? "#10b98115" : "#6b728015",
                  color: p.enabled ? "#10b981" : "#6b7280",
                  border: `1px solid ${p.enabled ? "#10b98130" : "#6b728030"}`,
                  fontSize: "11px",
                }}
                onClick={() => handleExecute(p)}
                disabled={!p.enabled || isExecuting}
              >
                {isExecuting ? <RefreshCw size={11} /> : <Play size={11} />}
                {isExecuting ? "Executing Closed-Loop…" : "Execute Now"}
              </button>
            </div>
          );
        })}
      </div>

      {/* Execution History */}
      <div style={{ background: "var(--surface-elevated)", border: "1px solid var(--border)", borderRadius: "10px", padding: "16px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "12px" }}>
          <ShieldCheck size={14} color="#10b981" />
          <span style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-primary)" }}>Closed-Loop Execution History</span>
          <span style={{ marginLeft: "auto", fontSize: "10px", color: "var(--text-muted)" }}>{executions.length} executions</span>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          {executions.slice(0, 6).map((ex) => {
            const statusColor = STATUS_COLOR[ex.status] ?? "#6b7280";
            return (
              <div key={ex.execution_id} style={{
                background: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: "8px",
                padding: "12px",
                display: "flex",
                flexDirection: "column",
                gap: "6px",
              }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    {ex.status === "verified_resolved"
                      ? <CheckCircle size={13} color="#10b981" />
                      : ex.status === "verification_failed_reverted"
                      ? <XCircle size={13} color="#ef4444" />
                      : <PowerOff size={13} color="#6b7280" />
                    }
                    <span style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-primary)" }}>{ex.policy_name}</span>
                  </div>
                  <span style={{ fontSize: "10px", fontWeight: 700, color: statusColor }}>
                    {ex.status.replace(/_/g, " ").toUpperCase()}
                  </span>
                </div>
                <div style={{ fontSize: "11px", color: "var(--text-muted)", fontFamily: "monospace" }}>{ex.action_taken}</div>
                <div style={{ fontSize: "11px", color: "#10b981", background: "#10b98110", borderRadius: "4px", padding: "4px 8px" }}>
                  {ex.watchdog_verdict}
                </div>
                {Object.keys(ex.initial_metrics).length > 0 && (
                  <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                    {Object.entries(ex.initial_metrics).map(([k, v]) => (
                      <div key={k} style={{ fontSize: "10px", color: "var(--text-muted)" }}>
                        {k}: <span style={{ color: "#ef4444" }}>{typeof v === "number" ? v.toFixed(2) : v}</span>
                        {" → "}
                        <span style={{ color: "#10b981" }}>
                          {typeof ex.post_mitigation_metrics[k] === "number"
                            ? (ex.post_mitigation_metrics[k] as number).toFixed(2)
                            : ex.post_mitigation_metrics[k]}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default SelfHealingPanel;

