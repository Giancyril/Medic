"""
FinOps & Incident Financial Impact Models.
Quantifies real-time business downtime loss, SLA penalty tiers,
and cloud infrastructure cost deltas incurred during autonomous remediations.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

class ImpactTier(str, Enum):
    TIER_1_CRITICAL = "tier_1_mission_critical"
    TIER_2_CORE = "tier_2_core_business"
    TIER_3_INTERNAL = "tier_3_internal_support"

class BusinessImpactMetric(BaseModel):
    revenue_loss_per_minute_usd: float
    cumulative_revenue_loss_usd: float
    incident_duration_minutes: float
    estimated_failed_transactions: int
    sla_target_availability_pct: float = 99.95
    actual_availability_pct: float
    sla_breach_penalty_usd: float

class RemediationCostDelta(BaseModel):
    action_type: str
    resources_added: str
    hourly_cost_delta_usd: float
    monthly_projected_cost_usd: float
    cost_status: str = "approved_temporary"
    applied_at: str = Field(default_factory=utc_now)

class FinOpsSummary(BaseModel):
    service: str
    incident_id: str
    impact_tier: ImpactTier
    business_impact: BusinessImpactMetric
    remediation_costs: List[RemediationCostDelta] = Field(default_factory=list)
    total_financial_loss_usd: float
    total_infra_remediation_cost_usd: float
    total_incident_cost_usd: float
    roi_saved_usd: float = Field(..., description="Estimated loss prevented by fast MTTR")
    rightsizing_recommendation: str
    evaluated_at: str = Field(default_factory=utc_now)
