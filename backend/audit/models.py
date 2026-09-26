"""
Audit Trail, Compliance & Incident Replay Models.
Maintains tamper-evident cryptographic log of all agent and human interventions,
provides SOX/SOC-2 compliance verification, and builds step-by-step incident replay frames.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

class ActorType(str, Enum):
    AI_AGENT = "ai_agent"
    HUMAN_OPERATOR = "human_operator"
    KUBERNETES_CONTROLLER = "kubernetes_controller"
    SYSTEM = "system"

class ActionCategory(str, Enum):
    DIAGNOSIS = "diagnosis"
    APPROVAL_REQUEST = "approval_request"
    APPROVAL_DECISION = "approval_decision"
    REMEDIATION_EXECUTION = "remediation_execution"
    ROLLBACK = "rollback"
    ESCALATION = "escalation"
    CANARY_PROGRESSION = "canary_progression"

class AuditEntry(BaseModel):
    entry_id: str
    timestamp: str = Field(default_factory=utc_now)
    incident_id: str
    actor_type: ActorType
    actor_name: str
    category: ActionCategory
    action_summary: str
    details: Dict[str, Any] = Field(default_factory=dict)
    tamper_hash: str = ""

class IncidentReplayFrame(BaseModel):
    frame_index: int
    relative_time_seconds: int
    timestamp: str
    event_title: str
    description: str
    cluster_health: str
    service_state: Dict[str, Any] = Field(default_factory=dict)
    action_taken: Optional[str] = None

class ComplianceReport(BaseModel):
    incident_id: str
    generated_at: str = Field(default_factory=utc_now)
    total_actions: int
    autonomous_actions_count: int
    human_approved_actions_count: int
    soc2_compliant: bool = True
    sox_safety_gates_passed: bool = True
    audit_trail_verified: bool = True
    summary: str = ""
