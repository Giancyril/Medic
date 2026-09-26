import React, { useState, useEffect } from "react";
import {
  GitFork,
  CheckCircle,
  AlertTriangle,
  RotateCcw,
  FastForward,
  Activity,
  RefreshCw,
  Sliders,
} from "lucide-react";
import { api } from "../api/client";
import type {
  CanaryDeployment,
  CanaryAnalysisReport,
} from "../types/day4";

interface Props {
  service?: string;
}

export const CanaryAnalysisPanel: React.FC<Props> = () => {
  const [deployments, setDeployments] = useState<CanaryDeployment[]>([]);
  const [selectedId, setSelectedId] = useState<string>("");
  const [activeReport, setActiveReport] = useState<CanaryAnalysisReport | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);

  const fetchDeployments = async () => {
    setLoading(true);
    try {
      const data = await api.canary.list();
      setDeployments(data.deployments);
      if (data.deployments.length > 0) {
        const current = selectedId
          ? data.deployments.find((d) => d.deployment_id === selectedId) || data.deployments[0]
          : data.deployments[0];
        setSelectedId(current.deployment_id);
        setActiveReport(current.last_report || null);
      }
    } catch (err) {
      console.error("Failed to load canary deployments:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDeployments();
  }, []);

  const currentDeployment = deployments.find((d) => d.deployment_id === selectedId);

  const handleEvaluate = async () => {
    if (!selectedId) return;
    setActionInProgress("evaluating");
    try {
      const res = await api.canary.evaluate(selectedId);
      setActiveReport(res.report);
      await fetchDeployments();
    } catch (err) {
      console.error("Evaluation error:", err);
    } finally {
      setActionInProgress(null);
    }
  };

  const handleAdvance = async () => {
    if (!selectedId) return;
    setActionInProgress("advancing");
    try {
      const res = await api.canary.advance(selectedId);
      setActiveReport(res.report);
      await fetchDeployments();
    } catch (err) {
      console.error("Advance error:", err);
    } finally {
      setActionInProgress(null);
    }
  };

  const handlePromote = async () => {
    if (!selectedId) return;
    setActionInProgress("promoting");
    try {
      await api.canary.promote(selectedId);
      await fetchDeployments();
    } catch (err) {
      console.error("Promote error:", err);
    } finally {
      setActionInProgress(null);
    }
  };

  const handleRollback = async () => {
    if (!selectedId) return;
    setActionInProgress("rolling_back");
    try {
      await api.canary.rollback(selectedId, "Operator triggered emergency rollback from UI");
      await fetchDeployments();
    } catch (err) {
      console.error("Rollback error:", err);
    } finally {
      setActionInProgress(null);
    }
  };

  const getPhaseBadge = (phase: string) => {
    switch (phase) {
      case "promoted":
        return <span className="status-pill" style={{ color: "#10b981", borderColor: "rgba(16,185,129,0.4)" }}>PROMOTED (100%)</span>;
      case "rolled_back":
      case "aborted":
        return <span className="status-pill" style={{ color: "#ef4444", borderColor: "rgba(239,68,68,0.4)" }}>ROLLED BACK (0%)</span>;
      default:
        return <span className="status-pill" style={{ color: "#06b6d4", borderColor: "rgba(6,182,212,0.4)" }}>RUNNING CANARY</span>;
    }
  };

  return (
    <div className="card" style={{ padding: "18px", marginTop: "16px" }}>
      {/* Top Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <GitFork size={18} color="var(--accent-cyan)" />
          <h3 style={{ margin: 0, fontSize: "14px", fontWeight: 600 }}>
            Automated Canary Analysis & Progressive Traffic Rollback
          </h3>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          {currentDeployment && getPhaseBadge(currentDeployment.phase)}
          <button className="btn btn-ghost btn-sm" onClick={fetchDeployments} disabled={loading} title="Refresh Canary">
            <RefreshCw size={12} className={loading ? "spin" : ""} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {currentDeployment && (
        <div>
          {/* Deployment Context & Traffic Bar */}
          <div style={{ padding: "12px 14px", background: "rgba(0,0,0,0.25)", borderRadius: "6px", border: "1px solid var(--border)", marginBottom: "14px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
              <div>
                <span style={{ fontSize: "13px", fontWeight: 600 }}>{currentDeployment.service}</span>
                <span style={{ fontSize: "11px", color: "var(--text-muted)", marginLeft: "8px" }}>
                  Baseline: <code>{currentDeployment.baseline_version}</code> ➔ Canary: <code>{currentDeployment.canary_version}</code>
                </span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "12px" }}>
                <Sliders size={13} color="var(--accent-cyan)" />
                <span>Traffic Allocation: <strong style={{ color: "var(--accent-cyan)" }}>{currentDeployment.current_weight_pct}%</strong> Canary / {100 - currentDeployment.current_weight_pct}% Baseline</span>
              </div>
            </div>

            {/* Stepped Traffic Bar */}
            <div style={{ display: "flex", gap: "6px", marginTop: "8px" }}>
              {currentDeployment.steps.map((st, i) => {
                const isPassed = currentDeployment.current_weight_pct >= st;
                const isCurrent = currentDeployment.current_weight_pct === st;
                return (
                  <div
                    key={i}
                    style={{
                      flex: 1,
                      padding: "6px 8px",
                      borderRadius: "4px",
                      background: isPassed ? "rgba(6, 182, 212, 0.2)" : "rgba(255,255,255,0.05)",
                      border: `1px solid ${isCurrent ? "var(--accent-cyan)" : isPassed ? "rgba(6, 182, 212, 0.4)" : "var(--border)"}`,
                      textAlign: "center",
                      fontSize: "11px",
                      fontWeight: isCurrent ? 700 : 500,
                      color: isPassed ? "var(--text-primary)" : "var(--text-muted)",
                      transition: "all 0.2s ease",
                    }}
                  >
                    Step {i + 1}: {st}%
                  </div>
                );
              })}
            </div>
          </div>

          {/* Analysis Report & Scoring Banner */}
          {activeReport && (
            <div
              style={{
                padding: "12px 14px",
                borderRadius: "6px",
                border: `1px solid ${activeReport.verdict === "fail" ? "#ef4444" : activeReport.verdict === "warn" ? "#f59e0b" : "#10b981"}`,
                background: activeReport.verdict === "fail" ? "rgba(239, 68, 68, 0.1)" : activeReport.verdict === "warn" ? "rgba(245, 158, 11, 0.08)" : "rgba(16, 185, 129, 0.08)",
                marginBottom: "14px",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  {activeReport.verdict === "pass" ? (
                    <CheckCircle size={16} color="#10b981" />
                  ) : (
                    <AlertTriangle size={16} color={activeReport.verdict === "fail" ? "#ef4444" : "#f59e0b"} />
                  )}
                  <span style={{ fontSize: "13px", fontWeight: 700 }}>
                    Kayenta Canary Composite Score: {activeReport.overall_score} / 100
                  </span>
                </div>
                <span
                  style={{
                    fontSize: "11px",
                    fontWeight: 700,
                    textTransform: "uppercase",
                    padding: "2px 8px",
                    borderRadius: "4px",
                    background: activeReport.verdict === "fail" ? "#ef4444" : activeReport.verdict === "warn" ? "#f59e0b" : "#10b981",
                    color: "#fff",
                  }}
                >
                  Verdict: {activeReport.verdict}
                </span>
              </div>
              <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                {activeReport.message}
              </div>
            </div>
          )}

          {/* Statistical Metric Comparisons Grid */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "10px", marginBottom: "14px" }}>
            {activeReport?.metrics.map((m, idx) => {
              const isFail = m.status === "fail";
              const isWarn = m.status === "warn";
              const borderColor = isFail ? "#ef4444" : isWarn ? "#f59e0b" : "var(--border)";
              return (
                <div
                  key={idx}
                  style={{
                    padding: "10px 12px",
                    borderRadius: "6px",
                    background: "rgba(0,0,0,0.25)",
                    border: `1px solid ${borderColor}`,
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", fontWeight: 600, marginBottom: "4px" }}>
                    <span>{m.metric_name}</span>
                    <span style={{ color: isFail ? "#ef4444" : isWarn ? "#f59e0b" : "#10b981", textTransform: "uppercase" }}>
                      {m.status}
                    </span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", marginTop: "6px" }}>
                    <span style={{ color: "var(--text-muted)" }}>Baseline: {m.baseline_value} {m.unit}</span>
                    <span style={{ fontWeight: 600 }}>Canary: {m.canary_value} {m.unit}</span>
                  </div>
                  <div style={{ fontSize: "11px", marginTop: "4px", color: m.delta_pct > 0 ? "#fca5a5" : "#6ee7b7" }}>
                    Delta: {m.delta_pct > 0 ? `+${m.delta_pct}%` : `${m.delta_pct}%`}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Action Buttons Toolbar */}
          <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end" }}>
            <button
              className="btn btn-ghost btn-sm"
              onClick={handleEvaluate}
              disabled={actionInProgress !== null}
            >
              <Activity size={12} className={actionInProgress === "evaluating" ? "spin" : ""} />
              <span>Evaluate Telemetry</span>
            </button>
            <button
              className="btn btn-ghost btn-sm"
              onClick={handleAdvance}
              disabled={actionInProgress !== null || currentDeployment.current_weight_pct >= 100 || currentDeployment.phase === "rolled_back"}
            >
              <FastForward size={12} />
              <span>Advance Traffic Tier</span>
            </button>
            <button
              className="btn btn-ghost btn-sm"
              style={{ color: "#10b981" }}
              onClick={handlePromote}
              disabled={actionInProgress !== null || currentDeployment.current_weight_pct >= 100 || currentDeployment.phase === "rolled_back"}
            >
              <CheckCircle size={12} />
              <span>Promote to 100%</span>
            </button>
            <button
              className="btn btn-sm"
              style={{ background: "#ef4444", color: "#fff", borderColor: "#dc2626" }}
              onClick={handleRollback}
              disabled={actionInProgress !== null || currentDeployment.current_weight_pct === 0}
            >
              <RotateCcw size={12} />
              <span>Emergency Rollback</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

