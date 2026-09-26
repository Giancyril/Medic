"""
Autonomous Closed-Loop Self-Healing Models.
Defines schemas for declarative auto-mitigation policies, velocity guardrails,
and post-mitigation health verification watchdog executions.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

class PolicyStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    TRIGGERED = "triggered"
    COOLING_DOWN = "cooling_down"

class VerificationStatus(str, Enum):
    PENDING = "pending"
    VERIFYING = "verifying"
    VERIFIED_RESOLVED = "verified_resolved"
    VERIFICATION_FAILED_REVERTED = "verification_failed_reverted"

class SelfHealingPolicy(BaseModel):
    policy_id: str
    name: str
    target_service: str
    trigger_condition: str
    action_type: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
    cooldown_minutes: int = 15
    last_triggered_at: Optional[str] = None
    execution_count: int = 0
    success_count: int = 0
    risk_level: str = "medium"

class ClosedLoopExecution(BaseModel):
    execution_id: str
    policy_id: str
    policy_name: str
    incident_id: str
    target_service: str
    action_taken: str
    started_at: str = Field(default_factory=utc_now)
    completed_at: Optional[str] = None
    initial_metrics: Dict[str, float] = Field(default_factory=dict)
    post_mitigation_metrics: Dict[str, float] = Field(default_factory=dict)
    status: VerificationStatus = VerificationStatus.VERIFIED_RESOLVED
    watchdog_verdict: str = "System health nominal post-remediation. Closed-loop verified."
    revert_triggered: bool = False

class GuardrailStatus(BaseModel):
    velocity_limit_per_15m: int = 5
    actions_in_current_window: int = 2
    rate_limit_exceeded: bool = False
    blast_radius_cap: float = 80.0
    human_intervention_required: bool = False
    last_reset_at: str = Field(default_factory=utc_now)
