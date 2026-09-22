import type { Incident, IncidentSeverity, IncidentStatus } from "./types/incident";

export function timeAgo(iso: string): string {
  const d = new Date(iso);
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false });
}

export function getSeverityClass(sev: IncidentSeverity): string {
  return `badge-${sev}`;
}

export function getStatusClass(status: IncidentStatus): string {
  return `badge-${status.replace(/_/g, "_")}`;
}

export function getTierClass(tier: string): string {
  if (tier.includes("1") || tier.includes("LOW")) return "badge-tier-low";
  if (tier.includes("2") || tier.includes("MEDIUM")) return "badge-tier-medium";
  return "badge-tier-high";
}

export function getTierLabel(tier: string): string {
  if (tier.includes("1") || tier.includes("LOW")) return "Low Risk";
  if (tier.includes("2") || tier.includes("MEDIUM")) return "Medium Risk";
  return "High Risk";
}

export function getConfidenceClass(conf: number): string {
  if (conf >= 0.7) return "high";
  if (conf >= 0.45) return "medium";
  return "low";
}

export function getSeverityDot(sev: IncidentSeverity): string {
  const colors: Record<IncidentSeverity, string> = {
    critical: "var(--sev-critical)",
    warning: "var(--sev-warning)",
    info: "var(--sev-info)",
  };
  return colors[sev] ?? "var(--text-muted)";
}

export function getPodStatusClass(status: string, ready: boolean): string {
  if (status === "Running" && ready) return "ok";
  if (status === "OOMKilled") return "crit";
  if (status === "CrashLoopBackOff") return "crit";
  if (status === "Pending" || status === "Init") return "warn";
  return "unknown";
}

export function getHealthColor(score: number): string {
  if (score >= 0.7) return "var(--accent-green)";
  if (score >= 0.4) return "var(--sev-warning)";
  return "var(--sev-critical)";
}

export function hasEvidence(incident: Incident): boolean {
  return !!incident.evidence && Object.keys(incident.evidence).length > 0;
}

export function hasDiagnosis(incident: Incident): boolean {
  return !!incident.diagnosis && "root_cause" in incident.diagnosis;
}

export function hasRemediation(incident: Incident): boolean {
  return !!incident.remediation && "action_type" in incident.remediation;
}

export function needsApproval(incident: Incident): boolean {
  return (
    hasRemediation(incident) &&
    "requires_human_approval" in incident.remediation &&
    (incident.remediation as { requires_human_approval: boolean }).requires_human_approval === true &&
    incident.status === "ACTION_REQUIRED"
  );
}
