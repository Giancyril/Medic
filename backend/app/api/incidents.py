from fastapi import APIRouter, HTTPException, Depends, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from typing import List, Optional
import json
import asyncio
from backend.app.core.database import get_db
from backend.app.models.incident import Incident, IncidentEvent, IncidentStatus, IncidentSeverity
from backend.app.schemas.incident import IncidentRead, IncidentListItem, IncidentStatusUpdate
from backend.app.core.incident_manager import broadcaster, utc_now

router = APIRouter(prefix="/incidents", tags=["incidents"])

@router.get("", response_model=List[IncidentListItem])
async def list_incidents(
    status: Optional[str] = Query(None, description="Filter by status (e.g. NEW, INVESTIGATING, ACTION_REQUIRED)"),
    severity: Optional[str] = Query(None, description="Filter by severity (critical, warning, info)"),
    service: Optional[str] = Query(None, description="Filter by service name"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """List incidents with optional filters, sorted by most recently active."""
    query = select(Incident).order_by(desc(Incident.last_seen_at)).limit(limit)
    if status:
        query = query.where(Incident.status == status.upper())
    if severity:
        query = query.where(Incident.severity == severity.lower())
    if service:
        query = query.where(Incident.service == service.lower())

    result = await db.execute(query)
    incidents = result.scalars().all()
    return incidents

@router.get("/stream")
async def stream_incidents():
    """Server-Sent Events (SSE) real-time incident event stream."""
    queue = broadcaster.subscribe()

    async def event_generator():
        try:
            # Initial ping
            yield f"data: {json.dumps({'event': 'connected', 'timestamp': utc_now().isoformat()})}\n\n"
            while True:
                data = await queue.get()
                yield f"data: {data}\n\n"
        except asyncio.CancelledError:
            broadcaster.unsubscribe(queue)
            raise
        finally:
            broadcaster.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.get("/{incident_id}", response_model=IncidentRead)
async def get_incident(
    incident_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve detailed incident record including chronological event trail and evidence."""
    stmt = (
        select(Incident)
        .options(selectinload(Incident.events))
        .where(Incident.id == incident_id)
    )
    result = await db.execute(stmt)
    incident = result.scalars().first()
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Incident {incident_id} not found")
    return incident

@router.patch("/{incident_id}/status", response_model=IncidentRead)
async def update_incident_status(
    incident_id: str,
    body: IncidentStatusUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Transition incident status and record lifecycle event in the audit trail."""
    stmt = (
        select(Incident)
        .options(selectinload(Incident.events))
        .where(Incident.id == incident_id)
    )
    result = await db.execute(stmt)
    incident = result.scalars().first()
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Incident {incident_id} not found")

    old_status = incident.status
    incident.status = body.status.value
    now = utc_now()
    incident.last_seen_at = now
    if body.status == IncidentStatus.RESOLVED:
        incident.resolved_at = now

    msg = f"Status changed from {old_status} to {body.status.value}"
    if body.reason:
        msg += f": {body.reason}"

    event = IncidentEvent(
        incident_id=incident.id,
        event_type="STATUS_CHANGED",
        message=msg,
        payload_json=json.dumps({"old_status": old_status, "new_status": body.status.value, "reason": body.reason}),
        created_at=now
    )
    db.add(event)
    await db.commit()
    await db.refresh(incident)

    await broadcaster.broadcast("incident_status_changed", {
        "id": incident.id,
        "old_status": old_status,
        "new_status": incident.status,
        "reason": body.reason
    })

    return incident
