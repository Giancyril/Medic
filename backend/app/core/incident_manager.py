import hashlib
import uuid
import json
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from backend.app.models.incident import Incident, IncidentEvent, IncidentStatus, IncidentSeverity
from backend.app.schemas.incident import AlertmanagerAlert

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

def compute_fingerprint(service: str, namespace: str, alert_name: str) -> str:
    raw = f"{namespace.strip().lower()}:{service.strip().lower()}:{alert_name.strip().lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

class EventBroadcaster:
    """Async pub/sub queue for Server-Sent Events (SSE) streaming."""
    def __init__(self):
        self._subscribers: Set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subscribers.discard(q)

    async def broadcast(self, event_type: str, data: Dict[str, Any]) -> None:
        message = json.dumps({"event": event_type, "data": data, "timestamp": utc_now().isoformat()})
        dead = set()
        for q in self._subscribers:
            try:
                q.put_nowait(message)
            except Exception:
                dead.add(q)
        self._subscribers.difference_update(dead)

broadcaster = EventBroadcaster()

async def process_incoming_alert(session: AsyncSession, alert: AlertmanagerAlert) -> Incident:
    """
    Normalizes an Alertmanager alert, deduplicates against active incidents,
    and updates or creates the Incident record.
    """
    labels = alert.labels or {}
    annotations = alert.annotations or {}

    service = labels.get("service") or labels.get("app") or labels.get("job") or "unknown-service"
    namespace = labels.get("namespace") or "default"
    alert_name = labels.get("alertname") or "SystemAlert"
    severity_str = labels.get("severity", "warning").lower()
    if severity_str not in [s.value for s in IncidentSeverity]:
        severity_str = IncidentSeverity.WARNING.value

    summary = annotations.get("summary") or annotations.get("message") or f"{alert_name} on {service}"
    description = annotations.get("description") or summary

    fingerprint = compute_fingerprint(service, namespace, alert_name)

    # Check for active incident with this fingerprint
    stmt = select(Incident).where(
        Incident.fingerprint == fingerprint,
        Incident.status != IncidentStatus.RESOLVED.value
    )
    result = await session.execute(stmt)
    existing_incident = result.scalars().first()

    now = utc_now()

    if existing_incident:
        existing_incident.firing_count += 1
        existing_incident.last_seen_at = now
        # Update annotations if newer
        existing_incident.summary = summary
        existing_incident.description = description

        # Add event
        event = IncidentEvent(
            incident_id=existing_incident.id,
            event_type="ALERT_DEDUPED",
            message=f"Consecutive alert fired ({existing_incident.firing_count}x): {alert_name}",
            payload_json=json.dumps({"alert": alert.model_dump()}),
            created_at=now
        )
        session.add(event)
        await session.commit()
        await session.refresh(existing_incident)

        await broadcaster.broadcast("incident_updated", {
            "id": existing_incident.id,
            "status": existing_incident.status,
            "firing_count": existing_incident.firing_count,
            "service": existing_incident.service,
            "severity": existing_incident.severity
        })

        return existing_incident

    # Create new incident
    incident_id = f"inc-{uuid.uuid4().hex[:8]}"
    title = f"[{severity_str.upper()}] {service}: {alert_name}"
    
    new_incident = Incident(
        id=incident_id,
        fingerprint=fingerprint,
        title=title,
        service=service,
        namespace=namespace,
        alert_name=alert_name,
        severity=severity_str,
        status=IncidentStatus.NEW.value,
        summary=summary,
        description=description,
        firing_count=1,
        first_seen_at=now,
        last_seen_at=now,
        labels_json=json.dumps(labels),
        annotations_json=json.dumps(annotations),
        evidence_json="{}",
        diagnosis_json="{}",
        remediation_json="{}"
    )
    session.add(new_incident)
    await session.flush()

    event = IncidentEvent(
        incident_id=incident_id,
        event_type="ALERT_INGESTED",
        message=f"Incident opened from alert {alert_name} on {namespace}/{service}",
        payload_json=json.dumps({"alert": alert.model_dump()}),
        created_at=now
    )
    session.add(event)
    await session.commit()
    await session.refresh(new_incident)

    await broadcaster.broadcast("incident_created", {
        "id": new_incident.id,
        "title": new_incident.title,
        "service": new_incident.service,
        "namespace": new_incident.namespace,
        "severity": new_incident.severity,
        "status": new_incident.status,
        "firing_count": 1,
        "summary": new_incident.summary,
        "created_at": now.isoformat()
    })

    return new_incident
