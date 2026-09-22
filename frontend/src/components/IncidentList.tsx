
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
  const active = sorted.filter(i => i.status !== "RESOLVED");
  const resolved = sorted.filter(i => i.status === "RESOLVED");

  return (
    <>
      <div className="incident-list-header">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
        Active Incidents
        <span className="count">{active.length}</span>
      </div>

      {active.length === 0 && (
        <div className="empty-state" style={{ padding: "40px 24px" }}>
          <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
          <h3>All Clear</h3>
          <p>No active incidents. Use the Chaos Lab to fire test alerts.</p>
        </div>
      )}

      {active.map((inc) => (
        <IncidentItem key={inc.id} incident={inc} active={selectedId === inc.id} onClick={() => onSelect(inc.id)} />
      ))}

      {resolved.length > 0 && (
        <>
          <div className="incident-list-header" style={{ marginTop: "4px" }}>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12"/></svg>
            Resolved
            <span className="count">{resolved.length}</span>
          </div>
          {resolved.map((inc) => (
            <IncidentItem key={inc.id} incident={inc} active={selectedId === inc.id} onClick={() => onSelect(inc.id)} />
          ))}
        </>
      )}
    </>
  );
}

function IncidentItem({ incident: inc, active, onClick }: { incident: Incident; active: boolean; onClick: () => void }) {
  return (
    <div className={`incident-item ${active ? "active" : ""}`} onClick={onClick} id={`incident-item-${inc.id}`}>
      <div className="incident-item-header">
        <span style={{ width: 8, height: 8, borderRadius: "50%", background: getSeverityDot(inc.severity), flexShrink: 0 }} />
        <span className="incident-item-title" title={inc.title}>{inc.title}</span>
        <span className={`badge ${getSeverityClass(inc.severity)}`}>{inc.severity}</span>
      </div>
      <div className="incident-item-meta">
        <span className="incident-item-service">{inc.service}</span>
        <span className={`badge ${getStatusClass(inc.status)}`} style={{ fontSize: "10px" }}>{inc.status.replace(/_/g, " ")}</span>
        <span className="firing-count" style={{ marginLeft: "auto" }}>{inc.firing_count}× · {timeAgo(inc.last_seen_at)}</span>
      </div>
    </div>
  );
}
