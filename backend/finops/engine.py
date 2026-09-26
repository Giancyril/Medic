"""
FinOps & Incident Financial Impact Engine.
Calculates real-time business downtime loss, SLA breach penalties,
and infrastructure cost deltas incurred by autonomous remediation actions.
"""
from typing import Dict, List, Optional
from backend.finops.models import (
    ImpactTier,
    BusinessImpactMetric,
    RemediationCostDelta,
    FinOpsSummary,
    utc_now,
)

SERVICE_TIER_CONFIG = {
    "payment-svc": {
        "tier": ImpactTier.TIER_1_CRITICAL,
        "base_rev_loss_per_min": 1800.0,
        "sla_target": 99.99,
        "sla_penalty_base": 10000.0,
        "sla_penalty_per_min": 250.0,
        "avg_tx_per_min": 850,
    },
    "checkout-api": {
        "tier": ImpactTier.TIER_1_CRITICAL,
        "base_rev_loss_per_min": 1450.0,
        "sla_target": 99.95,
        "sla_penalty_base": 5000.0,
        "sla_penalty_per_min": 150.0,
        "avg_tx_per_min": 620,
    },
    "order-db": {
        "tier": ImpactTier.TIER_1_CRITICAL,
        "base_rev_loss_per_min": 1600.0,
        "sla_target": 99.99,
        "sla_penalty_base": 8000.0,
        "sla_penalty_per_min": 200.0,
        "avg_tx_per_min": 700,
    },
    "inventory-svc": {
        "tier": ImpactTier.TIER_2_CORE,
        "base_rev_loss_per_min": 450.0,
        "sla_target": 99.9,
        "sla_penalty_base": 2500.0,
        "sla_penalty_per_min": 50.0,
        "avg_tx_per_min": 240,
    },
    "notification-svc": {
        "tier": ImpactTier.TIER_3_INTERNAL,
        "base_rev_loss_per_min": 95.0,
        "sla_target": 99.5,
        "sla_penalty_base": 500.0,
        "sla_penalty_per_min": 10.0,
        "avg_tx_per_min": 80,
    },
}

class FinOpsEngine:
    """Computes revenue impact, SLA penalties, and infrastructure cost deltas."""

    def __init__(self):
        self.summaries: Dict[str, FinOpsSummary] = {}
        self._init_demo_data()

    def _init_demo_data(self):
        s1 = self.calculate_impact(
            service="checkout-api",
            duration_minutes=8.5,
            error_rate_pct=14.2,
            incident_id="inc-checkout-503",
        )
        self.add_remediation_cost(
            incident_id="inc-checkout-503",
            action_type="horizontal_pod_autoscaling",
            resources="+4 c5.xlarge Pod Replicas",
            hourly_usd=0.68,
        )
        self.summaries["inc-checkout-503"] = s1

        s2 = self.calculate_impact(
            service="payment-svc",
            duration_minutes=4.2,
            error_rate_pct=5.5,
            incident_id="inc-payment-gw-01",
        )
        self.add_remediation_cost(
            incident_id="inc-payment-gw-01",
            action_type="circuit_breaker_cache_fallback",
            resources="Redis Memory Tier Allocation (16GB)",
            hourly_usd=0.32,
        )
        self.summaries["inc-payment-gw-01"] = s2

    def calculate_impact(
        self,
        service: str,
        duration_minutes: float,
        error_rate_pct: float,
        incident_id: str = "",
    ) -> FinOpsSummary:
        cfg = SERVICE_TIER_CONFIG.get(service, {
            "tier": ImpactTier.TIER_2_CORE,
            "base_rev_loss_per_min": 350.0,
            "sla_target": 99.9,
            "sla_penalty_base": 1500.0,
            "sla_penalty_per_min": 40.0,
            "avg_tx_per_min": 150,
        })

        effective_duration = max(0.5, duration_minutes)
        impact_factor = min(1.0, max(0.1, error_rate_pct / 100.0))
        rate_per_min = round(cfg["base_rev_loss_per_min"] * (0.5 + 0.5 * impact_factor), 2)
        revenue_loss = round(rate_per_min * effective_duration, 2)
        failed_tx = int(cfg["avg_tx_per_min"] * effective_duration * impact_factor)

        # SLA availability calculation
        availability = max(85.0, round(100.0 - error_rate_pct, 2))
        sla_penalty = 0.0
        if availability < cfg["sla_target"]:
            sla_penalty = round(cfg["sla_penalty_base"] + (cfg["sla_penalty_per_min"] * effective_duration), 2)

        # ROI savings: Human MTTR baseline is 45 mins; difference is saved
        human_mttr_baseline_minutes = 45.0
        minutes_saved = max(0.0, human_mttr_baseline_minutes - effective_duration)
        roi_saved = round(minutes_saved * cfg["base_rev_loss_per_min"], 2)

        # Existing remediation costs if any
        existing_remediation = []
        if incident_id and incident_id in self.summaries:
            existing_remediation = self.summaries[incident_id].remediation_costs

        infra_cost = sum(r.hourly_cost_delta_usd for r in existing_remediation)
        total_incident_cost = round(revenue_loss + sla_penalty + infra_cost, 2)

        recommendation = "Maintain current capacity. Rightsizing audit recommended after 24h stability."
        if infra_cost > 50.0:
            recommendation = "HIGH COST: Automated scale-down scheduled once golden signals remain nominal for 30m."

        summary = FinOpsSummary(
            service=service,
            incident_id=incident_id or f"inc-{service}-auto",
            impact_tier=cfg["tier"],
            business_impact=BusinessImpactMetric(
                revenue_loss_per_minute_usd=rate_per_min,
                cumulative_revenue_loss_usd=revenue_loss,
                incident_duration_minutes=effective_duration,
                estimated_failed_transactions=failed_tx,
                sla_target_availability_pct=cfg["sla_target"],
                actual_availability_pct=availability,
                sla_breach_penalty_usd=sla_penalty,
            ),
            remediation_costs=existing_remediation,
            total_financial_loss_usd=revenue_loss + sla_penalty,
            total_infra_remediation_cost_usd=infra_cost,
            total_incident_cost_usd=total_incident_cost,
            roi_saved_usd=roi_saved,
            rightsizing_recommendation=recommendation,
            evaluated_at=utc_now(),
        )

        if incident_id:
            self.summaries[incident_id] = summary
        return summary

    def add_remediation_cost(
        self,
        incident_id: str,
        action_type: str,
        resources: str,
        hourly_usd: float,
    ) -> RemediationCostDelta:
        delta = RemediationCostDelta(
            action_type=action_type,
            resources_added=resources,
            hourly_cost_delta_usd=round(hourly_usd, 3),
            monthly_projected_cost_usd=round(hourly_usd * 24 * 30, 2),
            cost_status="approved_temporary",
            applied_at=utc_now(),
        )
        if incident_id in self.summaries:
            self.summaries[incident_id].remediation_costs.append(delta)
            # Recompute total infra cost
            infra_cost = sum(r.hourly_cost_delta_usd for r in self.summaries[incident_id].remediation_costs)
            self.summaries[incident_id].total_infra_remediation_cost_usd = round(infra_cost, 2)
            self.summaries[incident_id].total_incident_cost_usd = round(
                self.summaries[incident_id].total_financial_loss_usd + infra_cost, 2
            )
        return delta

    def get_summary(self, incident_id: str) -> Optional[FinOpsSummary]:
        return self.summaries.get(incident_id)

    def list_summaries(self) -> List[FinOpsSummary]:
        return list(self.summaries.values())

# Global singleton
finops_engine = FinOpsEngine()
