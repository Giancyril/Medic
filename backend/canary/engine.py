"""
Automated Canary Analysis (ACA) Engine.
Evaluates statistical health of canary vs baseline workloads,
computes composite Kayenta-style scores, and triggers automated rollbacks.
"""
from typing import Dict, List, Optional
from backend.canary.models import (
    CanaryPhase,
    MetricComparisonStatus,
    CanaryMetricComparison,
    CanaryAnalysisReport,
    CanaryDeployment,
    utc_now,
)

class CanaryAnalysisEngine:
    """Performs statistical comparisons between canary and baseline telemetry."""

    def __init__(self):
        self.deployments: Dict[str, CanaryDeployment] = {}
        self._init_demo_deployment()

    def _init_demo_deployment(self):
        """Seed a representative active canary deployment."""
        dep = CanaryDeployment(
            deployment_id="dep-canary-checkout-v24",
            service="checkout-api",
            baseline_version="v2.3.9",
            canary_version="v2.4.0-rc2",
            phase=CanaryPhase.RUNNING,
            current_weight_pct=10,
            current_step_index=1,
            minimum_score=75.0,
            auto_rollback_enabled=True,
        )
        self.deployments[dep.deployment_id] = dep

    def analyze_metrics(
        self,
        deployment_id: str,
        service: str,
        baseline_version: str,
        canary_version: str,
        traffic_split_pct: int,
        metric_inputs: Optional[List[Dict]] = None,
    ) -> CanaryAnalysisReport:
        """
        Compare telemetry between baseline and canary workloads.
        """
        comparisons: List[CanaryMetricComparison] = []

        # If custom metrics not supplied, evaluate representative benchmark
        if not metric_inputs:
            metric_inputs = [
                {
                    "metric_name": "http_error_rate_pct",
                    "unit": "%",
                    "baseline": 0.04,
                    "canary": 0.09,
                    "weight": 3.0,
                    "warn_threshold": 25.0,
                    "fail_threshold": 50.0,
                    "higher_is_worse": True,
                },
                {
                    "metric_name": "http_request_p95_latency_ms",
                    "unit": "ms",
                    "baseline": 42.0,
                    "canary": 46.5,
                    "weight": 2.5,
                    "warn_threshold": 10.0,
                    "fail_threshold": 25.0,
                    "higher_is_worse": True,
                },
                {
                    "metric_name": "container_cpu_usage_cores",
                    "unit": "cores",
                    "baseline": 0.45,
                    "canary": 0.48,
                    "weight": 1.0,
                    "warn_threshold": 15.0,
                    "fail_threshold": 30.0,
                    "higher_is_worse": True,
                },
                {
                    "metric_name": "container_memory_usage_mb",
                    "unit": "MB",
                    "baseline": 612.0,
                    "canary": 630.0,
                    "weight": 1.5,
                    "warn_threshold": 10.0,
                    "fail_threshold": 20.0,
                    "higher_is_worse": True,
                },
                {
                    "metric_name": "http_request_success_rate_pct",
                    "unit": "%",
                    "baseline": 99.96,
                    "canary": 99.91,
                    "weight": 3.0,
                    "warn_threshold": 0.05,
                    "fail_threshold": 0.20,
                    "higher_is_worse": False,
                },
            ]

        total_weight = 0.0
        weighted_points = 0.0
        has_critical_failure = False

        for m in metric_inputs:
            b_val = float(m["baseline"])
            c_val = float(m["canary"])
            w = float(m.get("weight", 1.0))
            warn_th = float(m.get("warn_threshold", 10.0))
            fail_th = float(m.get("fail_threshold", 25.0))
            higher_worse = m.get("higher_is_worse", True)

            # Compute delta pct
            if b_val > 0:
                delta = ((c_val - b_val) / b_val) * 100.0 if higher_worse else ((b_val - c_val) / b_val) * 100.0
            else:
                delta = 0.0

            delta = round(delta, 2)

            if delta >= fail_th:
                status = MetricComparisonStatus.FAIL
                pts = 0.0
                if w >= 2.5:
                    has_critical_failure = True
                desc = f"Degradation exceeded critical threshold (+{delta}% vs {fail_th}%)"
            elif delta >= warn_th:
                status = MetricComparisonStatus.WARN
                pts = 50.0
                desc = f"Moderate drift observed (+{delta}% vs {warn_th}%)"
            else:
                status = MetricComparisonStatus.PASS
                pts = 100.0
                desc = f"Operating well within tolerance (delta: {delta}%)"

            total_weight += w
            weighted_points += (pts * w)

            comparisons.append(
                CanaryMetricComparison(
                    metric_name=m["metric_name"],
                    unit=m["unit"],
                    baseline_value=b_val,
                    canary_value=c_val,
                    delta_pct=delta,
                    weight=w,
                    status=status,
                    threshold_warn_pct=warn_th,
                    threshold_fail_pct=fail_th,
                    description=desc,
                )
            )

        overall_score = round(weighted_points / total_weight, 1) if total_weight > 0 else 100.0

        if has_critical_failure or overall_score < 70.0:
            verdict = MetricComparisonStatus.FAIL
            rollback_rec = True
            msg = f"Canary health score failed ({overall_score}/100). Critical thresholds breached. Automated rollback recommended."
        elif overall_score < 85.0:
            verdict = MetricComparisonStatus.WARN
            rollback_rec = False
            msg = f"Canary health score ({overall_score}/100) indicates moderate deviation. Proceed with caution."
        else:
            verdict = MetricComparisonStatus.PASS
            rollback_rec = False
            msg = f"Canary health score excellent ({overall_score}/100). Safe to promote to next traffic stage."

        return CanaryAnalysisReport(
            deployment_id=deployment_id,
            service=service,
            baseline_version=baseline_version,
            canary_version=canary_version,
            traffic_split_pct=traffic_split_pct,
            overall_score=overall_score,
            verdict=verdict,
            auto_rollback_recommended=rollback_rec,
            metrics=comparisons,
            evaluated_at=utc_now(),
            message=msg,
        )

# Global canary analysis singleton
canary_analysis_engine = CanaryAnalysisEngine()
