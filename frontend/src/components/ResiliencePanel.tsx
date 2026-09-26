import React, { useState, useEffect } from "react";
import {
  Zap,
  RefreshCw,
  Play,
  StopCircle,
  CheckCircle,
  XCircle,
  Clock,
} from "lucide-react";
import { api } from "../api/client";
import type { ResilienceScorecard, ChaosExperiment } from "../types/day4";

const FAULT_LABELS: Record<string, string> = {
  latency_spike: "Latency Spike",
  packet_drop: "Packet Drop",
  pod_crash: "Pod Crash",
  cpu_hog: "CPU Hog",
  db_deadlock: "DB Deadlock",
};

export const ResiliencePanel: React.FC = () => {
  const [scorecard, setScorecard] = useState<ResilienceScorecard | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [launchingId, setLaunchingId] = useState<string | null>(null);
  const [stoppingId, setStoppingId] = useState<string | null>(null);

  const loadScorecard = async () => {
    setLoading(true);
    try {
      const data = await api.resilience.getScorecard();
      setScorecard(data);
    } catch (err) {
      console.error("Failed to load resilience scorecard:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadScorecard(); }, []);

  const handleLaunch = async (exp: ChaosExperiment) => {
    setLaunchingId(exp.experiment_id);
    try {
      await api.resilience.launch(exp.experiment_id);
      await loadScorecard();
    } catch (err) { console.error("Launch error:", err); }
    finally { setLaunchingId(null); }
  };

  const handleStop = async (exp: ChaosExperiment) => {
    setStoppingId(exp.experiment_id);
    try {
      await api.resilience.stop(exp.experiment_id);
      await loadScorecard();
    } catch (err) { console.error("Stop error:", err); }
    finally { setStoppingId(null); }
  };

  const getGradeColor = (g: string) => g === "A+" || g === "A" ? "#10b981" : g === "B" ? "#f59e0b" : "#ef4444";

  return (
    <div className="card" style={{ padding: "18px", marginTop: "16px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <Zap size={18} color="#f59e0b" />
          <h3 style={{ margin: 0, fontSize: "14px", fontWeight: 600 }}>Chaos Resilience Studio & Hypothesis Verification</h3>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={loadScorecard} disabled={loading}>
          <RefreshCw size={12} className={loading ? "spin" : ""} /><span>Refresh</span>
        </button>
      </div>

      {scorecard && (
        <div>
          <div style={{ display: "grid", gridTemplateColumns: "auto 1fr 1fr 1fr 1fr", gap: "12px", alignItems: "center", padding: "14px 16px", background: "rgba(0,0,0,0.25)", borderRadius: "8px", border: "1px solid var(--border)", marginBottom: "16px" }}>
            <div style={{ textAlign: "center" }}>
              <div style={{ width: "60px", height: "60px", borderRadius: "50%", background: `${getGradeColor(scorecard.cluster_resilience_grade)}22`, border: `2px solid ${getGradeColor(scorecard.cluster_resilience_grade)}`, display: "flex", alignItems: "center", justifyContent: "center" }}>
                <span style={{ fontSize: "20px", fontWeight: 800, color: getGradeColor(scorecard.cluster_resilience_grade) }}>{scorecard.cluster_resilience_grade}</span>
              </div>
              <div style={{ fontSize: "10px", color: "var(--text-muted)", marginTop: "4px" }}>GRADE</div>
            </div>
            {[
              { label: "RESILIENCE INDEX", value: `${scorecard.resilience_index}%`, color: getGradeColor(scorecard.cluster_resilience_grade) },
              { label: "HYPOTHESES PASSED", value: `${scorecard.hypotheses_validated} / ${scorecard.experiments_run}`, color: "#10b981" },
              { label: "FAILED HYPOTHESES", value: String(scorecard.hypotheses_failed), color: scorecard.hypotheses_failed > 0 ? "#ef4444" : "#10b981" },
              { label: "AVG MTTR", value: `${scorecard.mttr_seconds_avg}s`, color: "var(--text-primary)" },
            ].map((stat) => (
              <div key={stat.label} style={{ padding: "8px 12px", background: "var(--bg-card)", borderRadius: "6px", border: "1px solid var(--border)" }}>
                <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>{stat.label}</div>
                <div style={{ fontSize: "18px", fontWeight: 700, color: stat.color }}>{stat.value}</div>
              </div>
            ))}
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            {scorecard.experiments.map((exp) => {
              const isLaunching = launchingId === exp.experiment_id;
              const isStopping = stoppingId === exp.experiment_id;
              const stateColors: Record<string, string> = { completed: "#10b981", running: "#06b6d4", aborted: "#ef4444", idle: "var(--text-muted)" };
              return (
                <div key={exp.experiment_id} style={{ padding: "14px 16px", background: "rgba(0,0,0,0.2)", borderRadius: "8px", border: `1px solid ${exp.state === "running" ? "#06b6d4" : "var(--border)"}` }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "8px" }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                        <span style={{ fontSize: "13px", fontWeight: 600 }}>{exp.name}</span>
                        <span style={{ padding: "1px 6px", borderRadius: "3px", fontSize: "10px", fontWeight: 600, background: "rgba(245,158,11,0.2)", color: "#f59e0b", border: "1px solid rgba(245,158,11,0.4)" }}>
                          {FAULT_LABELS[exp.fault_type] || exp.fault_type}
                        </span>
                        <span style={{ fontSize: "11px", color: stateColors[exp.state] || "var(--text-muted)", textTransform: "uppercase", fontWeight: 600 }}>● {exp.state}</span>
                      </div>
                      <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>Target: <code>{exp.target_service}</code> · Duration: {exp.duration_seconds}s</div>
                    </div>
                    <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                      {exp.state === "completed" && (
                        <div style={{ textAlign: "right" }}>
                          <div style={{ display: "flex", alignItems: "center", gap: "4px", justifyContent: "flex-end" }}>
                            {exp.hypothesis_passed ? <CheckCircle size={14} color="#10b981" /> : <XCircle size={14} color="#ef4444" />}
                            <span style={{ fontSize: "12px", fontWeight: 700, color: exp.hypothesis_passed ? "#10b981" : "#ef4444" }}>Score: {exp.resilience_score}</span>
                          </div>
                          <div style={{ fontSize: "10px", color: "var(--text-muted)", display: "flex", alignItems: "center", gap: "3px" }}>
                            <Clock size={10} />MTTR: {exp.remediation_latency_seconds}s
                          </div>
                        </div>
                      )}
                      {(exp.state === "idle" || exp.state === "completed") && (
                        <button className="btn btn-ghost btn-sm" style={{ color: "#06b6d4", borderColor: "rgba(6,182,212,0.4)", fontSize: "11px" }} onClick={() => handleLaunch(exp)} disabled={isLaunching || isStopping}>
                          <Play size={11} className={isLaunching ? "spin" : ""} /><span>{isLaunching ? "Injecting..." : "Launch"}</span>
                        </button>
                      )}
                      {exp.state === "running" && (
                        <button className="btn btn-sm" style={{ background: "#ef4444", color: "#fff", borderColor: "#dc2626", fontSize: "11px" }} onClick={() => handleStop(exp)} disabled={isStopping}>
                          <StopCircle size={11} /><span>{isStopping ? "Aborting..." : "Emergency Stop"}</span>
                        </button>
                      )}
                    </div>
                  </div>
                  <div style={{ padding: "8px 10px", background: "rgba(6,182,212,0.05)", borderRadius: "4px", border: "1px solid rgba(6,182,212,0.2)", fontSize: "11px", color: "var(--text-secondary)", marginBottom: exp.summary ? "8px" : "0" }}>
                    <strong style={{ color: "var(--accent-cyan)" }}>Hypothesis:</strong> {exp.hypothesis}
                  </div>
                  {exp.summary && <div style={{ fontSize: "11px", color: exp.hypothesis_passed === false ? "#fca5a5" : "var(--text-secondary)", fontStyle: "italic" }}>{exp.summary}</div>}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
