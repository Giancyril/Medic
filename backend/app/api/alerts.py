from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.database import get_db
from backend.app.schemas.incident import AlertmanagerWebhookPayload
from backend.app.core.incident_manager import process_incoming_alert

router = APIRouter(prefix="/alerts", tags=["alerts"])

@router.post("/webhook", status_code=status.HTTP_202_ACCEPTED)
async def receive_alertmanager_webhook(
    payload: AlertmanagerWebhookPayload,
    db: AsyncSession = Depends(get_db)
):
    """
    Receives Prometheus Alertmanager webhook payloads, parses alerts,
    deduplicates against active incidents, persists updates/new incidents,
    and returns processed incident identifiers.
    """
    processed_incidents = []
    
    # Process each firing alert
    for alert in payload.alerts:
        incident = await process_incoming_alert(db, alert)
        processed_incidents.append({
            "incident_id": incident.id,
            "fingerprint": incident.fingerprint,
            "status": incident.status,
            "service": incident.service,
            "firing_count": incident.firing_count
        })

    return {
        "status": "accepted",
        "alerts_received": len(payload.alerts),
        "incidents_processed": len(processed_incidents),
        "incidents": processed_incidents,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
