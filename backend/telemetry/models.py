"""
Telemetry Pipeline Models & SLI/SLO Evaluation Engine.
Provides schema for multi-signal metrics, traces, events, and dynamic SLO burn-rate evaluation.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

class MetricType(str, Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"

class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

class SLIType(str, Enum):
    LATENCY_P99 = "latency_p99"
    AVAILABILITY = "availability"
    ERROR_BUDGET = "error_budget"
    SATURATION = "saturation"

class TelemetryPoint(BaseModel):
    timestamp: str = Field(default_factory=utc_now)
    metric_name: str
    service: str
    namespace: str = "production"
    value: float
    labels: Dict[str, str] = Field(default_factory=dict)

class SLODefinition(BaseModel):
    id: str
    service: str
    name: str
    target_pct: float = 99.9  # e.g. 99.9%
    sli_type: SLIType
    threshold_value: float    # e.g. 500ms or 1.0%
    window_hours: int = 24    # Rolling window
    description: str

class SLIStatus(BaseModel):
    slo_id: str
    service: str
    target_pct: float
    current_pct: float
    burn_rate: float          # 1.0 = normal consumption, >14.4 = 1h fast burn page
    error_budget_remaining_pct: float
    is_breached: bool
    status: str               # "healthy", "warning", "critical"
    evaluated_at: str = Field(default_factory=utc_now)

class CorrelatedSignal(BaseModel):
    signal_name: str
    service: str
    correlation_coefficient: float  # -1.0 to 1.0
    lag_seconds: int = 0
    p_value: float = 0.01
    description: str
