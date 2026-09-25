import { useState } from "react";
import {
  Search,
  Brain,
  Zap,
  CheckCircle2,
  AlertTriangle,
  Server,
  FileText,
  Activity,
  Clock,
  Check,
  X,
  Send,
  Tag
} from "lucide-react";
import type {
  Incident,
  Diagnosis,
  RemediationAction,
  InvestigationEvidence,
} from "../types/incident";
import {
  timeAgo,
  formatTime,
  getSeverityClass,
  getStatusClass,
  getTierClass,
  getTierLabel,
  getConfidenceClass,
  hasEvidence,
  hasDiagnosis,
  hasRemediation,
  needsApproval,
  getPodStatusClass,
} from "../utils";
import { GoldenSignals } from "./GoldenSignals";
import { SLOMonitorPanel } from "./SLOMonitorPanel";
import { CorrelationGraphPanel } from "./CorrelationGraphPanel";
import { RunbookPanel } from "./RunbookPanel";
import { CopilotDrawer } from "./CopilotDrawer";
import { PostMortemModal } from "./PostMortemModal";
import { ServiceTopologyPanel } from "./ServiceTopologyPanel";
import { PredictiveHealthPanel } from "./PredictiveHealthPanel";
import { Bot } from "lucide-react";
import { api } from "../api/client";

interface Props {
  incident: Incident;
  onUpdate?: () => void;
}

export function IncidentDetail({ incident: inc, onUpdate }: Props) {
  const [approving, setApproving] = useState(false);
  const [investigating, setInvestigating] = useState(false);
  const [escalating, setEscalating] = useState(false);
  const [copilotOpen, setCopilotOpen] = useState(false);
  const [postMortemOpen, setPostMortemOpen] = useState(false);

  const diag = hasDiagnosis(inc) ? (inc.diagnosis as Diagnosis) : null;
  const rem = hasRemediation(inc) ? (inc.remediation as RemediationAction) : null;
  const ev = hasEvidence(inc) ? (inc.evidence as InvestigationEvidence) : null;

  async function handleInvestigate() {
    setInvestigating(true);
    try {
      await api.remediation.investigate(inc.id);
      onUpdate?.();
    } catch (e) {
      alert("Investigation error: " + (e instanceof Error ? e.message : String(e)));
    } finally {
      setInvestigating(false);
    }
  }

  async function handleApprove() {
    setApproving(true);
    try {
      await api.remediation.approve(inc.id, "operator", "Approved via dashboard safety gate");
      onUpdate?.();
    } catch (e) {
      alert("Approve error: " + (e instanceof Error ? e.message : String(e)));
    } finally {
      setApproving(false);
    }
  }

  async function handleReject() {
    setApproving(true);
    try {
      await api.remediation.reject(inc.id, "operator", "Rejected via dashboard — escalated to on-call");
      onUpdate?.();
    } catch (e) {
      alert("Reject error: " + (e instanceof Error ? e.message : String(e)));
    } finally {
      setApproving(false);
    }
  }

  async function handleEscalate() {
    setEscalating(true);
    try {
      await api.remediation.escalate(inc.id, "Manual operator escalation from dashboard");
      onUpdate?.();
    } catch (e) {
      alert("Escalate error: " + (e instanceof Error ? e.message : String(e)));
    } finally {
      setEscalating(false);
    }
  }

  async function handleResolve() {
    try {
      await api.remediation.updateStatus(inc.id, "RESOLVED", "Resolved via dashboard");
      onUpdate?.();
    } catch (e) {
      alert("Resolve error: " + (e instanceof Error ? e.message : String(e)));
    }
  }

  const confidenceClass = diag ? getConfidenceClass(diag.confidence) : "low";

  return (
    <>
      {/* PagerDuty-Style High-Priority Incident Header Card with Left Accent Border */}
      <div className={`detail-header-card sev-${inc.severity}`}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16 }}>
          <div style={{ flex: 1 }}>
            <div className="detail-meta-row">
              <span className={`badge ${getSeverityClass(inc.severity)}`}>{inc.severity}</span>
              <span className={`badge ${getStatusClass(inc.status)}`}>{inc.status.replace(/_/g, " ")}</span>
              <span className="detail-service-tag">{inc.service}/{inc.namespace}</span>
              <span style={{ color: "var(--text-muted)", fontSize: "12px" }}>· Triggered {timeAgo(inc.first_seen_at)}</span>
            </div>
            <h1 className="detail-title">{inc.title}</h1>
            {inc.summary && (
              <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginTop: "6px", lineHeight: 1.4 }}>
                {inc.summary}
              </p>
            )}
          </div>

          {/* Risk-Coded Action Buttons */}
          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", alignItems: "center" }}>
            {(inc.status === "NEW" || inc.status === "INVESTIGATING") && (
              <button
                className="btn btn-action-investigate"
                onClick={handleInvestigate}
                disabled={investigating}
                id={`btn-investigate-${inc.id}`}
              >
                {investigating ? (
                  <><div className="spinner" style={{ width: 12, height: 12 }} /> Investigating…</>
                ) : (
                  <>
                    <Search size={13} strokeWidth={2.2} />
                    <span>Investigate</span>
                  </>
                )}
              </button>
            )}

            {inc.status !== "RESOLVED" && inc.status !== "ESCALATED" && (
              <button
                className="btn btn-action-escalate"
                onClick={handleEscalate}
                disabled={escalating}
                id={`btn-escalate-${inc.id}`}
                title="Page on-call engineer via Slack & PagerDuty"
              >
                <Send size={13} strokeWidth={2} />
                <span>Escalate</span>
              </button>
            )}

            {inc.status !== "RESOLVED" && (
              <button
                className="btn btn-action-resolve"
                onClick={handleResolve}
                id={`btn-resolve-${inc.id}`}
                title="Close and mark incident resolved"
              >
                <Check size={13} strokeWidth={2.2} />
                <span>Resolve</span>
              </button>
            )}

              <button
                className="btn btn-secondary"
                onClick={() => setCopilotOpen(true)}
                title="Open Medic SRE Copilot AI chat"
                style={{ display: "flex", alignItems: "center", gap: "6px" }}
              >
                <Bot size={13} strokeWidth={2.2} />
                <span>Copilot AI</span>
              </button>

              <button
                className="btn btn-secondary"
                onClick={() => setPostMortemOpen(true)}
                title="Generate blameless post-mortem report"
                style={{ display: "flex", alignItems: "center", gap: "6px" }}
              >
                <FileText size={13} strokeWidth={2.2} />
                <span>Post-Mortem</span>
              </button>
          </div>
        </div>
      </div>

      {/* Detail Body */}
      <div className="detail-body">
        {/* Safety Gate Human Approval Banner */}
        {needsApproval(inc) && rem && (
          <div className="approval-banner">
            <div className="approval-banner-icon">
              <AlertTriangle size={20} strokeWidth={2.2} />
            </div>
            <div className="approval-banner-content">
              <div className="approval-banner-title">Human Authorization Required — Safety Gate</div>
              <div className="approval-banner-sub">
                <strong style={{ color: "var(--text-primary)" }}>{rem.name}</strong> — {rem.description}
                &nbsp;·&nbsp;<span className={`badge ${getTierClass(rem.risk_tier)}`}>{getTierLabel(rem.risk_tier)}</span>
              </div>
              {rem.diff_preview && (
                <div className="diff-viewer">
                  {rem.diff_preview.split("\n").map((line, i) => (
                    <div
                      key={i}
                      className={
                        line.startsWith("+")
                          ? "add"
                          : line.startsWith("-")
                          ? "del"
                          : line.startsWith("#")
                          ? "comment"
                          : ""
                      }
                    >
                      {line}
                    </div>
                  ))}
                </div>
              )}
              <div style={{ display: "flex", gap: "8px" }}>
                <button
                  className="btn btn-success"
                  onClick={handleApprove}
                  disabled={approving}
                  id={`btn-approve-${inc.id}`}
                >
                  <Check size={13} strokeWidth={2.2} />
                  <span>{approving ? "Applying Fix…" : "Approve Remediation"}</span>
                </button>
                <button
                  className="btn btn-danger"
                  onClick={handleReject}
                  disabled={approving}
                  id={`btn-reject-${inc.id}`}
                >
                  <X size={13} strokeWidth={2.2} />
                  <span>Reject</span>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Connected Pipeline Timeline */}
        <ConnectedPipelineTimeline inc={inc} />

        {/* Multi-Window SLO & Burn Rate Monitor */}
        <SLOMonitorPanel service={inc.service} />

        {/* Cross-Signal Anomaly Correlation */}
        <CorrelationGraphPanel service={inc.service} />

        {/* Day 3: Multi-Service Dependency Topology & Blast Radius */}
        <ServiceTopologyPanel selectedServiceId={inc.service} />

        {/* Day 3: Predictive Health, Time-to-Failure & Alert Deduplication */}
        <PredictiveHealthPanel incidentId={inc.id} service={inc.service} />

        {/* Golden Signals Metrics Card */}
        {ev?.golden_signals && <GoldenSignals data={ev.golden_signals} />}

        {/* Automated Runbook Engine */}
        <div style={{ marginBottom: "16px" }}>
          <RunbookPanel incident={inc} />
        </div>

        {/* AI Diagnosis Panel */}
        {diag && (
          <div className="card">
            <div className="card-title">
              <Brain size={14} strokeWidth={2} style={{ color: "var(--accent-purple)" }} />
              <span>Diagnostic Synthesis</span>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div
                style={{
                  padding: "14px 16px",
                  background: "var(--bg-elevated)",
                  borderRadius: "var(--radius)",
                  border: "1px solid var(--border)",
                }}
              >
                <div style={{ fontSize: "14px", fontWeight: 600, color: "var(--text-primary)", marginBottom: "4px" }}>
                  {diag.root_cause}
                </div>
                <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                  {diag.recommended_action}
                </div>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "20px" }}>
                <div style={{ flex: 1 }}>
                  <div
                    style={{
                      fontSize: "10px",
                      textTransform: "uppercase",
                      letterSpacing: "0.5px",
                      color: "var(--text-muted)",
                      marginBottom: "6px",
                      fontWeight: 600,
                    }}
                  >
                    Calibrated Confidence
                  </div>
                  <div className="confidence-bar-wrap">
                    <div className="confidence-bar">
                      <div
                        className={`confidence-fill ${confidenceClass}`}
                        style={{ width: `${diag.confidence * 100}%` }}
                      />
                    </div>
                    <span
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: "12px",
                        fontWeight: 600,
                        color: "var(--text-primary)",
                      }}
                    >
                      {(diag.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
                <div>
                  <div
                    style={{
                      fontSize: "10px",
                      textTransform: "uppercase",
                      letterSpacing: "0.5px",
                      color: "var(--text-muted)",
                      marginBottom: "6px",
                      fontWeight: 600,
                    }}
                  >
                    Remediation Risk
                  </div>
                  <span className={`badge ${getTierClass(diag.risk_tier)}`}>
                    {getTierLabel(diag.risk_tier)}
                  </span>
                </div>
              </div>

              {diag.supporting_evidence?.length > 0 && (
                <div>
                  <div
                    style={{
                      fontSize: "11px",
                      fontWeight: 600,
                      textTransform: "uppercase",
                      letterSpacing: "0.5px",
                      color: "var(--text-muted)",
                      marginBottom: "8px",
                    }}
                  >
                    Correlated Evidence Points
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                    {diag.supporting_evidence.map((e, i) => (
                      <div
                        key={i}
                        style={{
                          display: "flex",
                          alignItems: "flex-start",
                          gap: "8px",
                          fontSize: "12px",
                          color: "var(--text-secondary)",
                          padding: "8px 12px",
                          background: "var(--bg-elevated)",
                          borderRadius: "var(--radius-sm)",
                          border: "1px solid var(--border-subtle)",
                        }}
                      >
                        <CheckCircle2
                          size={13}
                          strokeWidth={2}
                          style={{ color: "var(--accent-primary)", flexShrink: 0, marginTop: "2px" }}
                        />
                        <span>{e}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Kubernetes Pod Status Table */}
        {ev?.pods && ev.pods.length > 0 && (
          <div className="card">
            <div className="card-title">
              <Server size={14} strokeWidth={2} style={{ color: "var(--accent-cyan)" }} />
              <span>Cluster Pod State ({ev.pods.length} pods inspected)</span>
            </div>
            <table className="pod-table">
              <thead>
                <tr>
                  <th>Pod Name</th>
                  <th>Status</th>
                  <th>Restarts</th>
                  <th>Host Node</th>
                </tr>
              </thead>
              <tbody>
                {ev.pods.map((pod, i) => (
                  <tr key={i}>
                    <td style={{ fontWeight: 500, color: "var(--text-primary)" }}>{pod.name}</td>
                    <td>
                      <div className="pod-status">
                        <span className={`pod-status-dot ${getPodStatusClass(pod.status, pod.ready)}`} />
                        <span>{pod.status}</span>
                        {pod.reason && (
                          <span style={{ color: "var(--text-muted)", fontSize: "11px" }}>
                            ({pod.reason})
                          </span>
                        )}
                      </div>
                    </td>
                    <td
                      style={{
                        color: pod.restart_count > 0 ? "var(--color-critical)" : "var(--text-secondary)",
                        fontWeight: pod.restart_count > 0 ? 600 : 400,
                      }}
                    >
                      {pod.restart_count}
                    </td>
                    <td style={{ color: "var(--text-muted)" }}>{pod.node}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Container Error Log Stream */}
        {ev?.logs?.errors && ev.logs.errors.length > 0 && (
          <div className="card">
            <div className="card-title">
              <FileText size={14} strokeWidth={2} style={{ color: "var(--color-critical)" }} />
              <span>
                Diagnostic Log Tail — {ev.logs.error_count} errors out of {ev.logs.total_lines_scanned} lines scanned
              </span>
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

        {/* Cluster Warning Events */}
        {ev?.events && ev.events.length > 0 && (
          <div className="card">
            <div className="card-title">
              <Activity size={14} strokeWidth={2} style={{ color: "var(--color-warning)" }} />
              <span>Correlated Kubernetes Events</span>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              {ev.events.map((e, i) => (
                <div
                  key={i}
                  style={{
                    display: "flex",
                    gap: "10px",
                    fontSize: "12px",
                    padding: "8px 12px",
                    background: "var(--bg-elevated)",
                    borderRadius: "var(--radius-sm)",
                    border: `1px solid ${
                      e.type === "Warning" ? "rgba(245,158,11,0.25)" : "var(--border)"
                    }`,
                  }}
                >
                  <span
                    style={{
                      color: e.type === "Warning" ? "var(--color-warning)" : "var(--text-muted)",
                      fontWeight: 600,
                      minWidth: "75px",
                    }}
                  >
                    {e.reason}
                  </span>
                  <span style={{ color: "var(--text-secondary)", flex: 1 }}>{e.message}</span>
                  <span style={{ fontFamily: "var(--font-mono)", color: "var(--text-muted)", fontSize: "11px" }}>
                    {e.object}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Incident Activity Timeline */}
        {inc.events?.length > 0 && (
          <div className="card">
            <div className="card-title">
              <Clock size={14} strokeWidth={2} style={{ color: "var(--accent-primary)" }} />
              <span>Incident Audit Log</span>
            </div>
            <div style={{ display: "flex", flexDirection: "column" }}>
              {[...inc.events].reverse().map((evt, i) => (
                <div
                  key={i}
                  style={{
                    display: "flex",
                    gap: "12px",
                    paddingBottom: "12px",
                    position: "relative",
                  }}
                >
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                    <div
                      style={{
                        width: 7,
                        height: 7,
                        borderRadius: "50%",
                        background: "var(--accent-primary)",
                        marginTop: "5px",
                        flexShrink: 0,
                      }}
                    />
                    {i < inc.events.length - 1 && (
                      <div style={{ width: 1, flex: 1, background: "var(--border)", marginTop: "4px" }} />
                    )}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "2px" }}>
                      <span style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-primary)" }}>
                        {evt.event_type.replace(/_/g, " ")}
                      </span>
                      <span style={{ fontSize: "11px", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                        {formatTime(evt.created_at)} ({timeAgo(evt.created_at)})
                      </span>
                    </div>
                    <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>{evt.message}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Incident Labels */}
        {Object.keys(inc.labels ?? {}).length > 0 && (
          <div className="card">
            <div className="card-title">
              <Tag size={13} strokeWidth={2} style={{ color: "var(--text-muted)" }} />
              <span>Alertmanager Match Labels</span>
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
              {Object.entries(inc.labels).map(([k, v]) => (
                <span
                  key={k}
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "11px",
                    background: "var(--bg-elevated)",
                    border: "1px solid var(--border)",
                    padding: "3px 8px",
                    borderRadius: "4px",
                    color: "var(--text-secondary)",
                  }}
                >
                  <span style={{ color: "var(--text-muted)" }}>{k}=</span>
                  {v}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

        <CopilotDrawer
          incident={inc}
          isOpen={copilotOpen}
          onClose={() => setCopilotOpen(false)}
        />

        <PostMortemModal
          incident={inc}
          isOpen={postMortemOpen}
          onClose={() => setPostMortemOpen(false)}
        />
    </>
  );
}

/* ─── Connected Incident Pipeline Timeline ─── */
function ConnectedPipelineTimeline({ inc }: { inc: Incident }) {
  const ev = hasEvidence(inc) ? (inc.evidence as InvestigationEvidence) : null;
  const diag = hasDiagnosis(inc) ? (inc.diagnosis as Diagnosis) : null;
  const rem = hasRemediation(inc) ? (inc.remediation as RemediationAction) : null;

  type StageState = "completed" | "active" | "blocked" | "pending";

  function computeStageState(phase: "ingest" | "investigate" | "diagnose" | "act"): StageState {
    const order = ["NEW", "INVESTIGATING", "DIAGNOSED", "ACTION_REQUIRED", "REMEDIATING", "RESOLVED", "ESCALATED"];
    const idx = order.indexOf(inc.status);

    switch (phase) {
      case "ingest":
        return "completed";
      case "investigate":
        if (ev) return "completed";
        if (inc.status === "INVESTIGATING" || idx >= 1) return "active";
        return "pending";
      case "diagnose":
        if (diag) return "completed";
        if (ev && inc.status !== "RESOLVED") return "active";
        return "pending";
      case "act":
        if (inc.status === "RESOLVED") return "completed";
        if (inc.status === "ACTION_REQUIRED") return "blocked";
        if (rem || inc.status === "REMEDIATING") return "active";
        return "pending";
    }
  }

  const stages = [
    {
      phase: "ingest" as const,
      title: "Alert Ingested",
      icon: CheckCircle2,
      time: formatTime(inc.first_seen_at),
      detail: `${inc.alert_name} · ${inc.firing_count} firing alert(s) normalized and deduplicated`,
    },
    {
      phase: "investigate" as const,
      title: "Telemetry Investigation",
      icon: Search,
      time: ev ? formatTime(ev.collected_at) : computeStageState("investigate") === "active" ? "In progress…" : "Awaiting trigger",
      detail: ev
        ? `Cluster health ${(ev.health_score * 100).toFixed(0)}% · ${ev.anomalies?.length ?? 0} anomaly patterns · ${ev.pods?.length ?? 0} pods inspected`
        : "Automated collection of PromQL golden signals, pod lifecycle states, and container log tails",
    },
    {
      phase: "diagnose" as const,
      title: "Diagnostic Synthesis",
      icon: Brain,
      time: diag ? formatTime(diag.diagnosed_at) : computeStageState("diagnose") === "active" ? "Reasoning…" : "Pending investigation",
      detail: diag
        ? `Confidence ${(diag.confidence * 100).toFixed(0)}% · ${diag.root_cause}`
        : "AI heuristic synthesis over correlated logs, metrics, and deployment history",
    },
    {
      phase: "act" as const,
      title: "Remediation & Action",
      icon: Zap,
      time: inc.resolved_at
        ? formatTime(inc.resolved_at)
        : inc.status === "ACTION_REQUIRED"
        ? "Safety Gate Blocked"
        : "Pending diagnosis",
      detail: inc.status === "RESOLVED"
        ? "Remediation successfully applied and verified stable"
        : rem
        ? `${rem.name} (${getTierLabel(rem.risk_tier)}) — ${rem.description}`
        : "Declarative cluster mitigation or escalation dispatch",
    },
  ];

  return (
    <div className="card" style={{ padding: "20px 22px 6px" }}>
      <div className="card-title" style={{ marginBottom: "18px" }}>
        <Activity size={14} strokeWidth={2} style={{ color: "var(--accent-primary)" }} />
        <span>Incident Pipeline Control Loop</span>
      </div>

      <div className="pipeline-timeline-container">
        {stages.map((stg, i) => {
          const state = computeStageState(stg.phase);
          const Icon = stg.icon;
          const isLast = i === stages.length - 1;

          return (
            <div key={stg.phase} className="timeline-step-row">
              {/* Continuous vertical connector track */}
              {!isLast && (
                <div
                  className={`timeline-track-segment ${
                    state === "completed" ? "completed" : ""
                  }`}
                />
              )}

              {/* Numbered / Status Node sitting directly ON the line */}
              <div className="timeline-node-wrap">
                <div className={`timeline-node ${state}`}>
                  {state === "completed" ? (
                    <Check size={16} strokeWidth={2.5} />
                  ) : state === "active" ? (
                    <Icon size={16} strokeWidth={2.2} />
                  ) : state === "blocked" ? (
                    <AlertTriangle size={16} strokeWidth={2.2} />
                  ) : (
                    <span>{i + 1}</span>
                  )}
                </div>
              </div>

              {/* Elevated Step Content Card */}
              <div
                className={`timeline-content-card ${
                  state === "active" ? "active" : state === "blocked" ? "blocked" : ""
                }`}
              >
                <div className="timeline-step-header">
                  <div className="timeline-step-title">
                    <span>{stg.title}</span>
                    {state === "active" && (
                      <span className="badge badge-INVESTIGATING" style={{ fontSize: "9px" }}>
                        RUNNING
                      </span>
                    )}
                    {state === "blocked" && (
                      <span className="badge badge-ACTION_REQUIRED" style={{ fontSize: "9px" }}>
                        APPROVAL REQUIRED
                      </span>
                    )}
                    {state === "completed" && (
                      <span className="badge badge-RESOLVED" style={{ fontSize: "9px" }}>
                        COMPLETE
                      </span>
                    )}
                  </div>
                  <span className="timeline-step-time">{stg.time}</span>
                </div>
                <div className={`timeline-step-detail ${state === "pending" ? "muted" : ""}`}>
                  {stg.detail}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}


