"""
On-Call Schedule & Escalation Policy Models.
Tracks responder shifts, tier ladders, page dispatch states, and MTTA (Mean Time to Acknowledge).
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

class PageStatus(str, Enum):
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    ESCALATED = "escalated"
    RESOLVED = "resolved"

class ResponderRole(str, Enum):
    PRIMARY_SRE = "primary_sre"
    SECONDARY_SRE = "secondary_sre"
    SERVICE_OWNER = "service_owner"
    INCIDENT_COMMANDER = "incident_commander"

class Responder(BaseModel):
    id: str
    name: str
    email: str
    role: ResponderRole
    phone: str
    avatar_initials: str

class OnCallShift(BaseModel):
    shift_id: str
    rotation_name: str
    primary_responder: Responder
    secondary_responder: Responder
    escalation_lead: Responder
    starts_at: str
    ends_at: str
    tz: str = "UTC"

class PageEvent(BaseModel):
    page_id: str
    incident_id: str
    tier_level: int = 1
    responder: Responder
    status: PageStatus = PageStatus.PENDING
    dispatched_at: str = Field(default_factory=utc_now)
    acknowledged_at: Optional[str] = None
    channel: str = "PagerDuty / Push Notification"
    escalation_timeout_seconds: int = 300
    notes: str = ""

class OnCallRosterStatus(BaseModel):
    current_shift: OnCallShift
    active_pages: List[PageEvent] = Field(default_factory=list)
    recent_resolved_pages: List[PageEvent] = Field(default_factory=list)
    mtta_seconds_avg: float = 42.0
