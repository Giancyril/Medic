"""
Canary Traffic Orchestrator & Rollback State Machine.
Manages canary promotion stages, progressive traffic split weights, and automated circuit-breaker rollbacks.
"""
from typing import Dict, Optional, Tuple
from backend.canary.models import (
    CanaryPhase,
    CanaryDeployment,
    CanaryAnalysisReport,
    MetricComparisonStatus,
    utc_now,
)
from backend.canary.engine import canary_analysis_engine

class CanaryOrchestrator:
    """Controls deployment progressive delivery lifecycle and automated rollbacks."""

    def __init__(self):
        self.engine = canary_analysis_engine

    def get_deployment(self, deployment_id: str) -> Optional[CanaryDeployment]:
        return self.engine.deployments.get(deployment_id)

    def list_deployments(self) -> Dict[str, CanaryDeployment]:
        return self.engine.deployments

    def advance_traffic(self, deployment_id: str) -> Tuple[CanaryDeployment, CanaryAnalysisReport]:
        """Progress traffic split to next tier (e.g. 10% -> 25% -> 50% -> 100%)."""
        dep = self.get_deployment(deployment_id)
        if not dep:
            raise ValueError(f"Deployment '{deployment_id}' not found.")

        if dep.phase in [CanaryPhase.ROLLED_BACK, CanaryPhase.ABORTED, CanaryPhase.PROMOTED]:
            raise ValueError(f"Cannot advance deployment in terminal phase '{dep.phase.value}'.")

        next_index = dep.current_step_index + 1
        if next_index < len(dep.steps):
            dep.current_step_index = next_index
            dep.current_weight_pct = dep.steps[next_index]
            dep.phase = CanaryPhase.RUNNING
        else:
            dep.current_weight_pct = 100
            dep.phase = CanaryPhase.PROMOTED

        # Run analysis at new traffic level
        report = self.engine.analyze_metrics(
            deployment_id=dep.deployment_id,
            service=dep.service,
            baseline_version=dep.baseline_version,
            canary_version=dep.canary_version,
            traffic_split_pct=dep.current_weight_pct,
        )
        dep.last_report = report
        dep.last_evaluated_at = utc_now()

        # Check auto-rollback trigger
        if report.auto_rollback_recommended and dep.auto_rollback_enabled:
            self.rollback_canary(deployment_id, reason="Automated rollback: Score breached safety threshold")

        return dep, report

    def promote_canary(self, deployment_id: str) -> CanaryDeployment:
        """Fully promote canary to 100% traffic and replace baseline."""
        dep = self.get_deployment(deployment_id)
        if not dep:
            raise ValueError(f"Deployment '{deployment_id}' not found.")

        dep.current_weight_pct = 100
        dep.current_step_index = len(dep.steps) - 1
        dep.phase = CanaryPhase.PROMOTED
        dep.last_evaluated_at = utc_now()
        return dep

    def rollback_canary(self, deployment_id: str, reason: str = "Manual rollback triggered") -> CanaryDeployment:
        """Immediately cut canary traffic to 0% and revert all routing to stable baseline."""
        dep = self.get_deployment(deployment_id)
        if not dep:
            raise ValueError(f"Deployment '{deployment_id}' not found.")

        dep.current_weight_pct = 0
        dep.phase = CanaryPhase.ROLLED_BACK
        dep.last_evaluated_at = utc_now()
        if dep.last_report:
            dep.last_report.message = f"ROLLED BACK: {reason}"
            dep.last_report.verdict = MetricComparisonStatus.FAIL
        return dep

    def evaluate_deployment(self, deployment_id: str) -> CanaryAnalysisReport:
        """Perform on-demand evaluation of active deployment."""
        dep = self.get_deployment(deployment_id)
        if not dep:
            raise ValueError(f"Deployment '{deployment_id}' not found.")

        report = self.engine.analyze_metrics(
            deployment_id=dep.deployment_id,
            service=dep.service,
            baseline_version=dep.baseline_version,
            canary_version=dep.canary_version,
            traffic_split_pct=dep.current_weight_pct,
        )
        dep.last_report = report
        dep.last_evaluated_at = utc_now()

        if report.auto_rollback_recommended and dep.auto_rollback_enabled:
            dep.phase = CanaryPhase.ROLLED_BACK
            dep.current_weight_pct = 0

        return report

# Global orchestrator singleton
canary_orchestrator = CanaryOrchestrator()
