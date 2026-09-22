from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.app.models.incident import IncidentStatus, IncidentSeverity

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

class IncidentEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    incident_id: str
    event_type: str
    message: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

class IncidentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    fingerprint: str
    title: str
    service: str
    namespace: str
    alert_name: str
    severity: str
    status: str
    summary: str
    description: str
    firing_count: int
    first_seen_at: datetime
    last_seen_at: datetime
    resolved_at: Optional[datetime] = None
    labels: Dict[str, Any] = Field(default_factory=dict)
    annotations: Dict[str, Any] = Field(default_factory=dict)
    evidence: Dict[str, Any] = Field(default_factory=dict)
    diagnosis: Dict[str, Any] = Field(default_factory=dict)
    remediation: Dict[str, Any] = Field(default_factory=dict)
    events: List[IncidentEventRead] = Field(default_factory=list)

class IncidentListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    fingerprint: str
    title: str
    service: str
    namespace: str
    alert_name: str
    severity: str
    status: str
    summary: str
    firing_count: int
    first_seen_at: datetime
    last_seen_at: datetime
    resolved_at: Optional[datetime] = None

class IncidentStatusUpdate(BaseModel):
    status: IncidentStatus
    reason: Optional[str] = None
