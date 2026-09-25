"""
Predictive Anomaly & Time-to-Failure (TTF) Forecast Models.
Provides schemas for extrapolating metric trajectories, predicting threshold breaches, and warning of impending outages.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

class TrendDirection(str, Enum):
    UPWARD = "upward"
    DOWNWARD = "downward"
    FLAT = "flat"
    VOLATILE = "volatile"

class UrgencyLevel(str, Enum):
    NOMINAL = "nominal"
    WATCH = "watch"
    ELEVATED = "elevated"
    CRITICAL = "critical"

class MetricForecast(BaseModel):
    metric_name: str = Field(..., description="e.g. container_memory_usage_bytes or http_request_duration_seconds")
    service: str = Field(..., description="Service name, e.g. 'checkout-api'")
    current_value: float
    unit: str = Field(default="")
    predicted_value_5m: float
    predicted_value_15m: float
    threshold_critical: float
    trend: TrendDirection
    slope_per_second: float = Field(default=0.0)
    ttf_seconds: Optional[float] = Field(default=None, description="Seconds until threshold is breached")
    ttf_human: str = Field(default="Safe (> 1h)")
    urgency: UrgencyLevel = Field(default=UrgencyLevel.NOMINAL)
    confidence_score: float = Field(default=0.85, description="Prediction model confidence (0.0 to 1.0)")
    summary: str = Field(default="")

class ClusterPredictionSummary(BaseModel):
    evaluated_at: str = Field(default_factory=utc_now)
    total_metrics_evaluated: int = 0
    at_risk_count: int = 0
    imminent_breach_count: int = 0
    forecasts: List[MetricForecast] = Field(default_factory=list)
    systemic_risk_index: float = Field(default=0.0, description="0.0 (all stable) to 1.0 (severe cascading threat)")
