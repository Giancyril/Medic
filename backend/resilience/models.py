"""
Resilience & Chaos Engineering Models.
Defines fault injection types, steady-state hypothesis verification,
experiment lifecycles, and cluster resilience scorecards.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

class FaultType(str, Enum):
    LATENCY_SPIKE = "latency_spike"
    PACKET_DROP = "packet_drop"
    POD_CRASH = "pod_crash"
    CPU_HOG = "cpu_hog"
    DB_DEADLOCK = "db_deadlock"

class ExperimentState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    RECOVERING = "recovering"
    COMPLETED = "completed"
    ABORTED = "aborted"

class ChaosExperiment(BaseModel):
    experiment_id: str
    name: str
    target_service: str
    fault_type: FaultType
    duration_seconds: int = 30
    hypothesis: str
    state: ExperimentState = ExperimentState.IDLE
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    hypothesis_passed: Optional[bool] = None
    steady_state_metrics: Dict[str, float] = Field(default_factory=dict)
    fault_state_metrics: Dict[str, float] = Field(default_factory=dict)
    resilience_score: float = 0.0
    remediation_latency_seconds: float = 0.0
    summary: str = ""

class ResilienceScorecard(BaseModel):
    evaluated_at: str = Field(default_factory=utc_now)
    cluster_resilience_grade: str = "A"
    resilience_index: float = 91.5
    experiments_run: int = 4
    hypotheses_validated: int = 3
    hypotheses_failed: int = 1
    mttr_seconds_avg: float = 24.5
    experiments: List[ChaosExperiment] = Field(default_factory=list)
