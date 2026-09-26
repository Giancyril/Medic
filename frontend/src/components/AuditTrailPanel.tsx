import React, { useState, useEffect } from "react";
import { Shield, RefreshCw, Lock, CheckCircle, Play, SkipForward } from "lucide-react";
import { api } from "../api/client";
import type { AuditEntry, ComplianceReport, IncidentReplayFrame } from "../types/day4";

interface Props {
  incidentId?: string;
}

const ACTOR_COLORS: Record<string, string> = {
  ai_agent: "#a855f7",
  human_operator: "#06b6d4",
  kubernetes_controller: "#10b981",
  system: "var(--text-muted)",
};

const CATEGORY_ICONS: Record<string, string> = {
  diagnosis: "🔍",
  approval_request: "🔒",
  approval_decision: "✅",
  remediation_execution: "⚡",
  rollback: "↩️",
  escalation: "📢",
  canary_progression: "🐦",
};

export const AuditTrailPanel: React.FC<Props> = ({ incidentId = "inc-demo-1" }) => {
  const [ledger, setLedger] = useState<AuditEntry[]>([]);
  const [compliance, setCompliance] = useState<ComplianceReport | null>(null);
  const [frames, setFrames] = useState<IncidentReplayFrame[]>([]);
  const [integrity, setIntegrity] = useState<boolean>(true);
  const [loading, setLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<"ledger" | "replay" | "compliance">("ledger");
  const [replayFrame, setReplayFrame] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);

  const loadAll = async () => {
    setLoading(true);
    try {
      const [ledgerData, compData, replayData] = await Promise.all([
        api.audit.getLedger(),
        api.audit.getCompliance(incidentId),
        api.audit.getReplay(incidentId),
      ]);
      setLedger(ledgerData.ledger);
      setIntegrity(ledgerData.integrity_verified);
      setCompliance(compData);
      setFrames(replayData.frames);
    } catch (err) {
      console.error("Failed to load audit data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadAll(); }, [incidentId]);

  // Auto-play replay
  useEffect(() => {
    if (!isPlaying || frames.length === 0) return;
    if (replayFrame >= frames.length - 1) { setIsPlaying(false); return; }
    const t = setTimeout(() => setReplayFrame((p) => p + 1), 1500);
    return () => clearTimeout(t);
  }, [isPlaying, replayFrame, frames.length]);

  const currentFrame = frames[replayFrame];

  return (
    <div className="card" style={{ padding: "18px", marginTop: "16px" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <Shield size={18} color="var(--accent-emerald)" />
          <h3 style={{ margin: 0, fontSize: "14px", fontWeight: 600 }}>Audit Trail, Incident Replay & Compliance</h3>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ fontSize: "11px", display: "flex", alignItems: "center", gap: "4px", color: integrity ? "#10b981" : "#ef4444" }}>
            <Lock size={11} />
            {integrity ? "Tamper-Proof Chain Verified" : "Integrity Violation Detected!"}
          </span>
          <div style={{ display: "flex", background: "rgba(0,0,0,0.3)", borderRadius: "6px", padding: "2px", border: "1px solid var(--border)" }}>
            {(["ledger", "replay", "compliance"] as const).map((tab) => (
              <button key={tab} onClick={() => setActiveTab(tab)} style={{ background: activeTab === tab ? "var(--bg-card)" : "transparent", border: "none", color: activeTab === tab ? "var(--text-primary)" : "var(--text-muted)", padding: "4px 10px", fontSize: "11px", fontWeight: 600, borderRadius: "4px", cursor: "pointer", textTransform: "capitalize" }}>
                {tab === "ledger" ? "Audit Ledger" : tab === "replay" ? "Incident Replay" : "Compliance"}
              </button>
            ))}
          </div>
          <button className="btn btn-ghost btn-sm" onClick={loadAll} disabled={loading}>
            <RefreshCw size={12} className={loading ? "spin" : ""} />
          </button>
        </div>
      </div>

      {/* Tab: Audit Ledger */}
      {activeTab === "ledger" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          {ledger.map((entry) => (
            <div key={entry.entry_id} style={{ display: "flex", gap: "12px", padding: "10px 12px", background: "rgba(0,0,0,0.2)", borderRadius: "6px", border: "1px solid var(--border)" }}>
              <div style={{ width: "32px", height: "32px", borderRadius: "50%", background: `${ACTOR_COLORS[entry.actor_type]}22`, border: `1px solid ${ACTOR_COLORS[entry.actor_type]}66`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: "14px", flexShrink: 0 }}>
                {CATEGORY_ICONS[entry.category] || "📋"}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "2px" }}>
                  <span style={{ fontSize: "12px", fontWeight: 600 }}>{entry.action_summary}</span>
                  <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>{new Date(entry.timestamp).toLocaleTimeString()}</span>
                </div>
                <div style={{ display: "flex", gap: "8px", fontSize: "10px" }}>
                  <span style={{ color: ACTOR_COLORS[entry.actor_type] }}>{entry.actor_name}</span>
                  <span style={{ color: "var(--text-muted)" }}>· {entry.category.replace(/_/g, " ")}</span>
                  <span style={{ color: "var(--text-muted)", fontFamily: "monospace" }}>#{entry.tamper_hash.slice(0, 8)}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Tab: Incident Replay */}
      {activeTab === "replay" && (
        <div>
          {/* Timeline Progress */}
          <div style={{ display: "flex", gap: "4px", marginBottom: "14px" }}>
            {frames.map((_, i) => (
              <button key={i} onClick={() => { setIsPlaying(false); setReplayFrame(i); }} style={{ flex: 1, height: "6px", borderRadius: "3px", background: i === replayFrame ? "var(--accent-cyan)" : i < replayFrame ? "rgba(6,182,212,0.4)" : "var(--border)", border: "none", cursor: "pointer", transition: "background 0.2s" }} />
            ))}
          </div>

          {/* Current Frame */}
          {currentFrame && (
            <div style={{ padding: "14px 16px", background: "rgba(0,0,0,0.3)", borderRadius: "8px", border: "1px solid var(--border)", marginBottom: "14px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "8px" }}>
                <div>
                  <div style={{ fontSize: "11px", color: "var(--accent-cyan)", fontWeight: 600, textTransform: "uppercase", marginBottom: "4px" }}>
                    Frame {currentFrame.frame_index + 1} / {frames.length} · T+{currentFrame.relative_time_seconds}s
                  </div>
                  <h4 style={{ margin: 0, fontSize: "14px", fontWeight: 700 }}>{currentFrame.event_title}</h4>
                </div>
                <span style={{ padding: "2px 8px", borderRadius: "4px", fontSize: "11px", fontWeight: 600, background: currentFrame.cluster_health === "healthy" ? "rgba(16,185,129,0.2)" : currentFrame.cluster_health === "failing" ? "rgba(239,68,68,0.2)" : "rgba(245,158,11,0.2)", color: currentFrame.cluster_health === "healthy" ? "#10b981" : currentFrame.cluster_health === "failing" ? "#ef4444" : "#f59e0b" }}>
                  {currentFrame.cluster_health.toUpperCase()}
                </span>
              </div>
              <p style={{ fontSize: "12px", color: "var(--text-secondary)", margin: "0 0 10px 0" }}>{currentFrame.description}</p>
              {currentFrame.action_taken && (
                <div style={{ padding: "6px 10px", background: "rgba(6,182,212,0.08)", borderRadius: "4px", border: "1px solid rgba(6,182,212,0.25)", fontSize: "11px", color: "var(--text-secondary)" }}>
                  <strong style={{ color: "var(--accent-cyan)" }}>Action Taken:</strong> {currentFrame.action_taken}
                </div>
              )}
              <div style={{ display: "flex", gap: "8px", marginTop: "10px" }}>
                {Object.entries(currentFrame.service_state).map(([k, v]) => (
                  <span key={k} style={{ padding: "2px 8px", borderRadius: "3px", fontSize: "10px", background: "var(--bg-card)", border: "1px solid var(--border)", color: "var(--text-secondary)" }}>
                    {k}: <strong style={{ color: "var(--text-primary)" }}>{String(v)}</strong>
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Replay Controls */}
          <div style={{ display: "flex", gap: "8px", justifyContent: "center" }}>
            <button className="btn btn-ghost btn-sm" onClick={() => { setIsPlaying(false); setReplayFrame(0); }}>
              <SkipForward size={12} style={{ transform: "rotate(180deg)" }} /><span>Restart</span>
            </button>
            <button className="btn btn-primary btn-sm" onClick={() => setIsPlaying(!isPlaying)} style={{ minWidth: "100px", justifyContent: "center" }}>
              {isPlaying ? <><RefreshCw size={12} className="spin" /><span>Playing...</span></> : <><Play size={12} /><span>Auto-Play Replay</span></>}
            </button>
            <button className="btn btn-ghost btn-sm" onClick={() => { setIsPlaying(false); setReplayFrame(Math.min(replayFrame + 1, frames.length - 1)); }} disabled={replayFrame >= frames.length - 1}>
              <SkipForward size={12} /><span>Next Frame</span>
            </button>
          </div>
        </div>
      )}

      {/* Tab: Compliance Report */}
      {activeTab === "compliance" && compliance && (
        <div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "10px", marginBottom: "14px" }}>
            {[
              { label: "SOC-2 Compliant", value: compliance.soc2_compliant, icon: <CheckCircle size={20} /> },
              { label: "SOX Safety Gates", value: compliance.sox_safety_gates_passed, icon: <Lock size={20} /> },
              { label: "Audit Trail Verified", value: compliance.audit_trail_verified, icon: <Shield size={20} /> },
            ].map((item) => (
              <div key={item.label} style={{ padding: "14px", background: item.value ? "rgba(16,185,129,0.1)" : "rgba(239,68,68,0.1)", borderRadius: "6px", border: `1px solid ${item.value ? "rgba(16,185,129,0.4)" : "rgba(239,68,68,0.4)"}`, display: "flex", alignItems: "center", gap: "10px" }}>
                <span style={{ color: item.value ? "#10b981" : "#ef4444" }}>{item.icon}</span>
                <div>
                  <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>{item.label}</div>
                  <div style={{ fontSize: "13px", fontWeight: 700, color: item.value ? "#10b981" : "#ef4444" }}>{item.value ? "COMPLIANT" : "VIOLATION"}</div>
                </div>
              </div>
            ))}
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "10px", marginBottom: "14px" }}>
            {[
              { label: "TOTAL ACTIONS LOGGED", value: String(compliance.total_actions) },
              { label: "AUTONOMOUS AI ACTIONS", value: String(compliance.autonomous_actions_count) },
              { label: "HUMAN DUAL-CONTROL APPROVALS", value: String(compliance.human_approved_actions_count) },
            ].map((stat) => (
              <div key={stat.label} style={{ padding: "10px", background: "rgba(0,0,0,0.25)", borderRadius: "6px", border: "1px solid var(--border)" }}>
                <div style={{ fontSize: "10px", color: "var(--text-muted)" }}>{stat.label}</div>
                <div style={{ fontSize: "20px", fontWeight: 700, marginTop: "2px" }}>{stat.value}</div>
              </div>
            ))}
          </div>

          <div style={{ padding: "12px 14px", background: "rgba(6,182,212,0.08)", borderRadius: "6px", border: "1px solid rgba(6,182,212,0.3)", fontSize: "12px", color: "var(--text-secondary)" }}>
            <strong style={{ color: "var(--accent-cyan)" }}>Certification Summary:</strong> {compliance.summary}
          </div>
        </div>
      )}
    </div>
  );
};
