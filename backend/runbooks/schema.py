from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class StepActionType(str, Enum):
    CHECK_METRIC = "CHECK_METRIC"
    INSPECT_LOGS = "INSPECT_LOGS"
    INSPECT_PODS = "INSPECT_PODS"
    EXECUTE_REMEDIATION = "EXECUTE_REMEDIATION"
    HUMAN_CONFIRMATION = "HUMAN_CONFIRMATION"
    VERIFY_STABILIZATION = "VERIFY_STABILIZATION"

class StepStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"

class RunbookStep(BaseModel):
    id: str
    title: str
    description: str
    action_type: StepActionType
    command_or_query: Optional[str] = None
    expected_condition: Optional[str] = None
    is_automated: bool = True
    status: StepStatus = StepStatus.PENDING
    output: Optional[str] = None
    executed_at: Optional[str] = None

class Runbook(BaseModel):
    id: str
    name: str
    description: str
    target_service: Optional[str] = "*"
    alert_patterns: List[str] = Field(default_factory=list)
    required_symptoms: List[str] = Field(default_factory=list)
    steps: List[RunbookStep] = Field(default_factory=list)
    version: str = "1.0.0"
    author: str = "SRE Reliability Team"

class RunbookExecutionState(BaseModel):
    runbook_id: str
    incident_id: str
    runbook_name: str
    current_step_index: int = 0
    steps: List[RunbookStep] = Field(default_factory=list)
    is_completed: bool = False
    success: Optional[bool] = None
    started_at: str = Field(default_factory=utc_now_iso)
    completed_at: Optional[str] = None
