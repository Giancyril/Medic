import { AlertOctagon, CheckCircle2 } from "lucide-react";
import type { Incident } from "../types/incident";
import { timeAgo, getSeverityClass, getStatusClass, getSeverityDot } from "../utils";

interface Props {
  incidents: Incident[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

const STATUS_ORDER: Record<string, number> = {
  ACTION_REQUIRED: 0,
  ESCALATED: 1,
  INVESTIGATING: 2,
  DIAGNOSED: 3,
  REMEDIATING: 4,
  NEW: 5,
  RESOLVED: 6,
};

function sortIncidents(list: Incident[]): Incident[] {
  return [...list].sort((a, b) => {
    const so = (STATUS_ORDER[a.status] ?? 9) - (STATUS_ORDER[b.status] ?? 9);
    if (so !== 0) return so;
    const sevOrd: Record<string, number> = { critical: 0, warning: 1, info: 2 };
    const sev = (sevOrd[a.severity] ?? 9) - (sevOrd[b.severity] ?? 9);
    if (sev !== 0) return sev;
    return new Date(b.last_seen_at).getTime() - new Date(a.last_seen_at).getTime();
  });
}

export function IncidentList({ incidents, selectedId, onSelect }: Props) {
  const sorted = sortIncidents(incidents);
  const active = sorted.filter((i) => i.status !== "RESOLVED");
  const resolved = sorted.filter((i) => i.status === "RESOLVED");

  return (
    <>
      <div className="incident-list-header">
        <AlertOctagon size={13} strokeWidth={2.2} />
        <span>Active Incidents</span>
        <span className="count">{active.length}</span>
      </div>

      {active.length === 0 && (
        <div className="empty-state" style={{ padding: "40px 24px" }}>
          <CheckCircle2 size={32} strokeWidth={1.5} style={{ opacity: 0.35, color: "var(--color-success)" }} />
          <h3>All Clear</h3>
          <p>No active incidents. Use the Chaos Simulator above to fire test alerts.</p>
        </div>
      )}

      {active.map((inc) => (
        <IncidentItem
          key={inc.id}
          incident={inc}
          active={selectedId === inc.id}
          onClick={() => onSelect(inc.id)}
        />
      ))}

      {resolved.length > 0 && (
        <>
          <div className="incident-list-header" style={{ marginTop: "4px" }}>
            <CheckCircle2 size={13} strokeWidth={2} style={{ color: "var(--color-success)" }} />
            <span>Resolved</span>
            <span className="count">{resolved.length}</span>
          </div>
          {resolved.map((inc) => (
            <IncidentItem
              key={inc.id}
              incident={inc}
              active={selectedId === inc.id}
              onClick={() => onSelect(inc.id)}
            />
          ))}
        </>
      )}
    </>
  );
}

function IncidentItem({
  incident: inc,
  active,
  onClick,
}: {
  incident: Incident;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <div
      className={`incident-item ${active ? "active" : ""}`}
      onClick={onClick}
      id={`incident-item-${inc.id}`}
    >
      <div className="incident-item-header">
        <span
          style={{
            width: 7,
            height: 7,
            borderRadius: "50%",
            background: getSeverityDot(inc.severity),
            flexShrink: 0,
          }}
        />
        <span className="incident-item-title" title={inc.title}>
          {inc.title}
        </span>
        <span className={`badge ${getSeverityClass(inc.severity)}`}>
          {inc.severity}
        </span>
      </div>
      <div className="incident-item-meta">
        <span className="incident-item-service">{inc.service}</span>
        <span className={`badge ${getStatusClass(inc.status)}`} style={{ fontSize: "9px" }}>
          {inc.status.replace(/_/g, " ")}
        </span>
        <span style={{ marginLeft: "auto", color: "var(--text-muted)", fontSize: "11px" }}>
          {inc.firing_count}× · {timeAgo(inc.last_seen_at)}
        </span>
      </div>
    </div>
  );
}
