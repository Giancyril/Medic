"""
Automated Canary Analysis (ACA) Models.
Defines schema for statistical canary vs baseline telemetry comparisons,
Kayenta-style health scoring, traffic weighting, and rollback recommendations.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

class CanaryPhase(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    EVALUATING = "evaluating"
    PROMOTING = "promoting"
    PROMOTED = "promoted"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"
    ABORTED = "aborted"

class MetricComparisonStatus(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"

class CanaryMetricComparison(BaseModel):
    metric_name: str
    unit: str
    baseline_value: float
    canary_value: float
    delta_pct: float
    weight: float = 1.0
    status: MetricComparisonStatus
    threshold_warn_pct: float = 10.0
    threshold_fail_pct: float = 25.0
    description: str

class CanaryAnalysisReport(BaseModel):
    deployment_id: str
    service: str
    baseline_version: str
    canary_version: str
    traffic_split_pct: int
    overall_score: float = Field(..., description="0-100 composite health score")
    verdict: MetricComparisonStatus
    auto_rollback_recommended: bool
    metrics: List[CanaryMetricComparison]
    evaluated_at: str = Field(default_factory=utc_now)
    message: str

class CanaryDeployment(BaseModel):
    deployment_id: str
    service: str
    baseline_version: str
    canary_version: str
    phase: CanaryPhase = CanaryPhase.RUNNING
    current_weight_pct: int = 10
    steps: List[int] = Field(default_factory=lambda: [5, 10, 25, 50, 100])
    current_step_index: int = 1
    minimum_score: float = 75.0
    auto_rollback_enabled: bool = True
    created_at: str = Field(default_factory=utc_now)
    last_evaluated_at: Optional[str] = None
    last_report: Optional[CanaryAnalysisReport] = None
