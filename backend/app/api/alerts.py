from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

router = APIRouter(prefix="/alerts", tags=["alerts"])

class AlertmanagerAlert(BaseModel):
    status: str
    labels: Dict[str, str] = Field(default_factory=dict)
    annotations: Dict[str, str] = Field(default_factory=dict)
    startsAt: Optional[str] = None
    endsAt: Optional[str] = None
    generatorURL: Optional[str] = None
    fingerprint: Optional[str] = None

class AlertmanagerWebhookPayload(BaseModel):
    version: str = "4"
    groupKey: Optional[str] = None
    truncatedAlerts: int = 0
    status: str
    receiver: Optional[str] = None
    groupLabels: Dict[str, str] = Field(default_factory=dict)
    commonLabels: Dict[str, str] = Field(default_factory=dict)
    commonAnnotations: Dict[str, str] = Field(default_factory=dict)
    externalURL: Optional[str] = None
    alerts: List[AlertmanagerAlert] = Field(default_factory=list)

@router.post("/webhook", status_code=status.HTTP_202_ACCEPTED)
async def receive_alertmanager_webhook(payload: AlertmanagerWebhookPayload):
    """
    Receives Prometheus Alertmanager webhook payloads, parses alerts,
    and enqueues them for investigation.
    """
    alert_count = len(payload.alerts)
    return {
        "status": "accepted",
        "alerts_received": alert_count,
        "receiver": payload.receiver,
        "common_labels": payload.commonLabels,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
