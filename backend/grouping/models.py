"""
Alert Deduplication, Fingerprinting & Incident Grouping Models.
Provides schema for reducing alert noise by clustering correlated alerts into unified incidents.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

class GroupedAlertItem(BaseModel):
    alert_id: str
    alert_name: str
    service: str
    severity: str
    fired_at: str
    fingerprint: str
    is_duplicate: bool = False

class IncidentCluster(BaseModel):
    cluster_id: str
    title: str
    primary_service: str
    root_cause_candidate: str
    severity: str = "critical"
    alerts_count: int = 0
    duplicate_count: int = 0
    first_seen: str = Field(default_factory=utc_now)
    last_seen: str = Field(default_factory=utc_now)
    alerts: List[GroupedAlertItem] = Field(default_factory=list)
    similarity_score: float = Field(default=0.92)
    noise_reduction_pct: float = Field(default=0.0)

class NoiseReductionStats(BaseModel):
    total_raw_alerts: int = 0
    grouped_incidents: int = 0
    duplicate_alerts_suppressed: int = 0
    noise_reduction_pct: float = 0.0
    last_computed: str = Field(default_factory=utc_now)
