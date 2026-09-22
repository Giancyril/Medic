import { useState } from "react";
import type { Incident, Diagnosis, RemediationAction, InvestigationEvidence } from "../types/incident";
import {
  timeAgo, getSeverityClass, getStatusClass, getTierClass, getTierLabel,
  getConfidenceClass, hasEvidence, hasDiagnosis, hasRemediation, needsApproval,
  getPodStatusClass
} from "../utils";
import { GoldenSignals } from "./GoldenSignals";
import { api } from "../api/client";

interface Props {
  incident: Incident;
  onUpdate?: () => void;
}

export function IncidentDetail({ incident: inc, onUpdate }: Props) {
  const [approving, setApproving] = useState(false);
  const [investigating, setInvestigating] = useState(false);
  const [escalating, setEscalating] = useState(false);

  const diag = hasDiagnosis(inc) ? (inc.diagnosis as Diagnosis) : null;
  const rem = hasRemediation(inc) ? (inc.remediation as RemediationAction) : null;
  const ev = hasEvidence(inc) ? (inc.evidence as InvestigationEvidence) : null;

  async function handleInvestigate() {
    setInvestigating(true);
    try { await api.remediation.investigate(inc.id); onUpdate?.(); }
    catch (e) { alert("Investigation error: " + (e instanceof Error ? e.message : String(e))); }
    finally { setInvestigating(false); }
  }

  async function handleApprove() {
    setApproving(true);
    try { await api.remediation.approve(inc.id, "operator", "Approved via dashboard"); onUpdate?.(); }
    catch (e) { alert("Approve error: " + (e instanceof Error ? e.message : String(e))); }
    finally { setApproving(false); }
  }

  async function handleReject() {
    setApproving(true);
    try { await api.remediation.reject(inc.id, "operator", "Rejected via dashboard — manual investigation needed"); onUpdate?.(); }
    catch (e) { alert("Reject error: " + (e instanceof Error ? e.message : String(e))); }
    finally { setApproving(false); }
  }

  async function handleEscalate() {
    setEscalating(true);
    try { await api.remediation.escalate(inc.id, "Manual escalation from dashboard"); onUpdate?.(); }
    catch (e) { alert("Escalate error: " + (e instanceof Error ? e.message : String(e))); }
    finally { setEscalating(false); }
  }

  async function handleResolve() {
    try { await api.remediation.updateStatus(inc.id, "RESOLVED", "Resolved via dashboard"); onUpdate?.(); }
    catch (e) { alert("Resolve error: " + (e instanceof Error ? e.message : String(e))); }
  }

  const confidenceClass = diag ? getConfidenceClass(diag.confidence) : "low";

  return (
    <>
      {/* Header */}
      <div className="detail-header">
        <div className="detail-header-top">
          <div style={{ flex: 1 }}>
            <div className="detail-meta" style={{ marginBottom: "6px" }}>
              <span className={`badge ${getSeverityClass(inc.severity)}`}>{inc.severity}</span>
              <span className={`badge ${getStatusClass(inc.status)}`}>{inc.status.replace(/_/g, " ")}</span>
              <span className="text-mono" style={{ color: "var(--text-muted)", fontSize: "11px" }}>{inc.service}/{inc.namespace}</span>
              <span className="text-muted" style={{ fontSize: "11px" }}>· {timeAgo(inc.last_seen_at)}</span>
            </div>
            <div className="detail-title">{inc.title}</div>
            {inc.summary && <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "4px" }}>{inc.summary}</div>}
          </div>
        </div>
        <div className="detail-actions">
          {(inc.status === "NEW" || inc.status === "INVESTIGATING") && (
            <button className="btn btn-primary btn-sm" onClick={handleInvestigate} disabled={investigating} id={`btn-investigate-${inc.id}`}>
              {investigating ? <><div className="spinner" style={{ width: 12, height: 12 }} />Running…</> : <>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg>
                Investigate
              </>}
            </button>
          )}
          {inc.status !== "RESOLVED" && inc.status !== "ESCALATED" && (
            <button className="btn btn-ghost btn-sm" onClick={handleEscalate} disabled={escalating} id={`btn-escalate-${inc.id}`}>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 2L11 13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
              Escalate
            </button>
          )}
          {inc.status !== "RESOLVED" && (
            <button className="btn btn-ghost btn-sm" onClick={handleResolve} id={`btn-resolve-${inc.id}`}>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="20 6 9 17 4 12"/></svg>
              Resolve
            </button>
          )}
        </div>
      </div>

      {/* Body */}
      <div className="detail-body">

        {/* Safety Gate Approval Banner */}
        {needsApproval(inc) && rem && (
          <div className="approval-banner">
            <div className="approval-banner-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
            </div>
            <div className="approval-banner-content">
              <div className="approval-banner-title">⚡ Human Approval Required — Safety Gate</div>
              <div className="approval-banner-sub">
                <strong>{rem.name}</strong> — {rem.description}
                &nbsp;·&nbsp;<span className={`badge ${getTierClass(rem.risk_tier)}`}>{getTierLabel(rem.risk_tier)}</span>
              </div>
              {rem.diff_preview && (
                <div className="diff-viewer">
                  {rem.diff_preview.split("\n").map((line, i) => (
                    <div key={i} className={line.startsWith("+") ? "add" : line.startsWith("-") ? "del" : line.startsWith("#") ? "comment" : ""}>
                      {line}
                    </div>
                  ))}
                </div>
              )}
              <div className="approval-banner-actions">
                <button className="btn btn-success" onClick={handleApprove} disabled={approving} id={`btn-approve-${inc.id}`}>
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                  {approving ? "Approving…" : "Approve Remediation"}
                </button>
                <button className="btn btn-danger" onClick={handleReject} disabled={approving} id={`btn-reject-${inc.id}`}>
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                  Reject
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Pipeline Trail */}
        <PipelineTrail inc={inc} />

        {/* Golden Signals */}
        {ev?.golden_signals && <GoldenSignals data={ev.golden_signals} />}

        {/* Diagnosis Panel */}
        {diag && (
          <div className="card">
            <div className="card-title">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93A10 10 0 000 12a10 10 0 0020 0"/></svg>
              AI Diagnosis
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <div style={{ padding: "12px 14px", background: "var(--bg-elevated)", borderRadius: "var(--radius-sm)", border: "1px solid var(--border)" }}>
                <div style={{ fontSize: "13px", fontWeight: 600, marginBottom: "4px" }}>{diag.root_cause}</div>
                <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>{diag.recommended_action}</div>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: "10px", textTransform: "uppercase", letterSpacing: "0.5px", color: "var(--text-muted)", marginBottom: "5px", fontWeight: 600 }}>
                    Confidence
                  </div>
                  <div className="confidence-bar-wrap">
                    <div className="confidence-bar">
                      <div className={`confidence-fill ${confidenceClass}`} style={{ width: `${diag.confidence * 100}%` }} />
                    </div>
                    <span className="text-mono" style={{ fontSize: "12px", fontWeight: 600 }}>{(diag.confidence * 100).toFixed(0)}%</span>
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: "10px", textTransform: "uppercase", letterSpacing: "0.5px", color: "var(--text-muted)", marginBottom: "4px", fontWeight: 600 }}>Risk</div>
                  <span className={`badge ${getTierClass(diag.risk_tier)}`}>{getTierLabel(diag.risk_tier)}</span>
                </div>
              </div>

              {diag.supporting_evidence?.length > 0 && (
                <div>
                  <div className="section-title" style={{ marginBottom: "8px", fontSize: "10px" }}>Supporting Evidence</div>
                  {diag.supporting_evidence.map((e, i) => (
                    <div key={i} className="evidence-item">
                      <svg className="icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="var(--accent-blue)" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                      {e}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Pod Table */}
        {ev?.pods && ev.pods.length > 0 && (
          <div className="card">
            <div className="card-title">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
              Pod Status ({ev.pods.length} pods)
            </div>
            <table className="pod-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Status</th>
                  <th>Restarts</th>
                  <th>Node</th>
                </tr>
              </thead>
              <tbody>
                {ev.pods.map((pod, i) => (
                  <tr key={i}>
                    <td>{pod.name}</td>
                    <td>
                      <div className="pod-status">
                        <span className={`pod-status-dot ${getPodStatusClass(pod.status, pod.ready)}`} />
                        {pod.status}
                        {pod.reason && <span style={{ color: "var(--text-muted)", marginLeft: "4px" }}>({pod.reason})</span>}
                      </div>
                    </td>
                    <td style={{ color: pod.restart_count > 0 ? "var(--sev-critical)" : "inherit" }}>{pod.restart_count}</td>
                    <td>{pod.node}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Logs */}
        {ev?.logs?.errors && ev.logs.errors.length > 0 && (
          <div className="card">
            <div className="card-title">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
              Error Logs — {ev.logs.error_count} errors in {ev.logs.total_lines_scanned} lines
            </div>
            <div className="log-viewer">
              {ev.logs.errors.map((l, i) => (
                <div key={i} className="log-line error">
                  <span style={{ color: "var(--text-muted)" }}>[{l.pod}]</span> {l.message}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Cluster Events */}
        {ev?.events && ev.events.length > 0 && (
          <div className="card">
            <div className="card-title">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
              Cluster Events
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              {ev.events.map((e, i) => (
                <div key={i} style={{ display: "flex", gap: "8px", fontSize: "12px", padding: "7px 10px", background: "var(--bg-elevated)", borderRadius: "var(--radius-sm)", border: `1px solid ${e.type === "Warning" ? "rgba(245,158,11,0.2)" : "var(--border)"}` }}>
                  <span style={{ color: e.type === "Warning" ? "var(--sev-warning)" : "var(--text-muted)", minWidth: "60px", fontWeight: 600 }}>{e.reason}</span>
                  <span style={{ color: "var(--text-secondary)", flex: 1 }}>{e.message}</span>
                  <span className="text-mono" style={{ color: "var(--text-muted)", fontSize: "11px" }}>{e.object}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Event Timeline */}
        {inc.events?.length > 0 && (
          <div className="card">
            <div className="card-title">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
              Activity Timeline
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "0" }}>
              {[...inc.events].reverse().map((evt, i) => (
                <div key={i} style={{ display: "flex", gap: "12px", paddingBottom: "12px", position: "relative" }}>
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                    <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: "var(--accent-blue)", flexShrink: 0, marginTop: "3px" }} />
                    {i < inc.events.length - 1 && <div style={{ width: "1px", flex: 1, background: "var(--border)", marginTop: "4px" }} />}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "2px" }}>
                      <span style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-primary)" }}>{evt.event_type.replace(/_/g, " ")}</span>
                      <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>{timeAgo(evt.created_at)}</span>
                    </div>
                    <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>{evt.message}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Labels */}
        {Object.keys(inc.labels ?? {}).length > 0 && (
          <div className="card card-sm">
            <div className="card-title">Labels</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
              {Object.entries(inc.labels).map(([k, v]) => (
                <span key={k} style={{ fontFamily: "var(--font-mono)", fontSize: "11px", background: "var(--bg-elevated)", padding: "3px 8px", borderRadius: "4px", color: "var(--text-secondary)" }}>
                  <span style={{ color: "var(--text-muted)" }}>{k}=</span>{v}
                </span>
              ))}
            </div>
          </div>
        )}

      </div>
    </>
  );
}

/* ─── Pipeline Trail ─── */
function PipelineTrail({ inc }: { inc: Incident }) {
  const ev = hasEvidence(inc) ? (inc.evidence as InvestigationEvidence) : null;
  const diag = hasDiagnosis(inc) ? (inc.diagnosis as Diagnosis) : null;
  const rem = hasRemediation(inc) ? (inc.remediation as RemediationAction) : null;

  type StageState = "pending" | "active" | "done" | "blocked";

  function stageState(phase: "ingest" | "investigate" | "diagnose" | "act"): StageState {
    const order = ["NEW", "INVESTIGATING", "DIAGNOSED", "ACTION_REQUIRED", "REMEDIATING", "RESOLVED", "ESCALATED"];
    const idx = order.indexOf(inc.status);
    switch (phase) {
      case "ingest":      return "done";
      case "investigate": return ev ? "done" : idx >= 1 ? "active" : "pending";
      case "diagnose":    return diag ? "done" : ev ? "active" : "pending";
      case "act":
        if (inc.status === "RESOLVED") return "done";
        if (inc.status === "ACTION_REQUIRED") return "blocked";
        if (rem) return "active";
        return "pending";
    }
  }

  const stages = [
    { phase: "ingest" as const, label: "Alert Ingested", icon: "📡", detail: `${inc.alert_name} · ${inc.firing_count} firing` },
    { phase: "investigate" as const, label: "Investigation", icon: "🔍", detail: ev ? `Health score ${(ev.health_score * 100).toFixed(0)}% · ${ev.anomalies?.length ?? 0} anomalies` : "Pending…" },
    { phase: "diagnose" as const, label: "Diagnosis", icon: "🧠", detail: diag ? `${diag.root_cause.slice(0, 60)}…` : "Pending…" },
    { phase: "act" as const, label: "Remediation", icon: "⚡", detail: rem ? rem.name : "Pending…" },
  ];

  const stateToNumber: Record<StageState, string> = { done: "✓", active: "●", blocked: "!", pending: "" };

  return (
    <div className="pipeline-stages">
      {stages.map((s, i) => {
        const state = stageState(s.phase);
        return (
          <div key={s.phase} className="pipeline-stage">
            <div className="pipeline-stage-header">
              <div className={`stage-number ${state === "done" ? "done" : state === "active" ? "active" : state === "blocked" ? "blocked" : ""}`}>
                {state === "pending" ? i + 1 : stateToNumber[state]}
              </div>
              <span style={{ fontSize: "16px" }}>{s.icon}</span>
              <span className="stage-name">{s.label}</span>
              <span style={{ fontSize: "11px", color: "var(--text-muted)", maxWidth: "200px", textAlign: "right", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{s.detail}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
