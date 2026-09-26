"""
Resilience & Chaos Engineering Engine.
Orchestrates simulated fault injections, validates steady-state hypotheses,
and computes cluster self-healing resilience scorecards.
"""
from typing import Dict, List, Optional
from backend.resilience.models import (
    FaultType,
    ExperimentState,
    ChaosExperiment,
    ResilienceScorecard,
    utc_now,
)
from backend.topology import topology_engine, NodeHealth

class ResilienceEngine:
    """Controls chaos experimentation, fault injection, and hypothesis scoring."""

    def __init__(self):
        self.experiments: Dict[str, ChaosExperiment] = {}
        self._init_catalog()

    def _init_catalog(self):
        """Seed pre-configured chaos engineering experiments."""
        exp1 = ChaosExperiment(
            experiment_id="exp-redis-partition",
            name="Redis Cache Latency Injection & Local Memory Fallback",
            target_service="redis-cache",
            fault_type=FaultType.LATENCY_SPIKE,
            duration_seconds=30,
            hypothesis="When Redis latency spikes +250ms, checkout-api falls back to in-memory cache with 0 HTTP 5xx errors.",
            state=ExperimentState.COMPLETED,
            started_at="2026-09-26T08:15:00Z",
            completed_at="2026-09-26T08:15:30Z",
            hypothesis_passed=True,
            steady_state_metrics={"p99_latency_ms": 2.1, "error_rate_pct": 0.0},
            fault_state_metrics={"p99_latency_ms": 255.0, "error_rate_pct": 0.02},
            resilience_score=94.0,
            remediation_latency_seconds=3.2,
            summary="PASSED: In-memory fallback engaged in 3.2s. Edge ingress error rate held at 0.02%.",
        )

        exp2 = ChaosExperiment(
            experiment_id="exp-checkout-pod-kill",
            name="Checkout API Random Pod SIGKILL Under Load",
            target_service="checkout-api",
            fault_type=FaultType.POD_CRASH,
            duration_seconds=45,
            hypothesis="Killing 2 out of 4 checkout pods causes K8s replica controller to spin up replacements within 15s.",
            state=ExperimentState.COMPLETED,
            started_at="2026-09-26T09:00:00Z",
            completed_at="2026-09-26T09:00:45Z",
            hypothesis_passed=True,
            steady_state_metrics={"replicas_ready": 4.0, "p99_latency_ms": 65.0},
            fault_state_metrics={"replicas_ready": 2.0, "p99_latency_ms": 95.0},
            resilience_score=88.5,
            remediation_latency_seconds=12.4,
            summary="PASSED: Kubernetes restarted missing replicas in 12.4s. Traffic automatically rerouted without dropping sessions.",
        )

        exp3 = ChaosExperiment(
            experiment_id="exp-payment-cpu-hog",
            name="Payment Engine Extreme CPU Starvation (4x Load)",
            target_service="payment-svc",
            fault_type=FaultType.CPU_HOG,
            duration_seconds=60,
            hypothesis="Under 95% CPU saturation, HPA triggers horizontal pod autoscaling within 45s.",
            state=ExperimentState.COMPLETED,
            started_at="2026-09-26T09:30:00Z",
            completed_at="2026-09-26T09:31:00Z",
            hypothesis_passed=False,
            steady_state_metrics={"cpu_pct": 35.0, "p99_latency_ms": 110.0},
            fault_state_metrics={"cpu_pct": 96.0, "p99_latency_ms": 620.0},
            resilience_score=62.0,
            remediation_latency_seconds=58.0,
            summary="FAILED: HPA scale-up took 58s (exceeding 45s threshold). P99 latency briefly spiked to 620ms.",
        )

        exp4 = ChaosExperiment(
            experiment_id="exp-postgres-deadlock",
            name="Order Primary PostgreSQL Connection Pool Contention",
            target_service="order-db",
            fault_type=FaultType.DB_DEADLOCK,
            duration_seconds=30,
            hypothesis="When database connections max out, connection pool queues requests without dropping connections.",
            state=ExperimentState.IDLE,
            hypothesis_passed=None,
            resilience_score=0.0,
            summary="Experiment ready to run.",
        )

        for e in [exp1, exp2, exp3, exp4]:
            self.experiments[e.experiment_id] = e

    def list_experiments(self) -> List[ChaosExperiment]:
        return list(self.experiments.values())

    def get_experiment(self, experiment_id: str) -> Optional[ChaosExperiment]:
        return self.experiments.get(experiment_id)

    def launch_experiment(self, experiment_id: str) -> ChaosExperiment:
        """Run simulated chaos experiment, injecting fault and verifying hypothesis."""
        exp = self.get_experiment(experiment_id)
        if not exp:
            raise ValueError(f"Experiment '{experiment_id}' not found.")

        exp.state = ExperimentState.RUNNING
        exp.started_at = utc_now()

        # Update topology to reflect chaos fault
        topology_engine.set_service_health(exp.target_service, NodeHealth.DEGRADED)

        # Simulate execution and verify hypothesis
        if exp.fault_type == FaultType.DB_DEADLOCK:
            exp.steady_state_metrics = {"active_conns": 52.0, "p99_latency_ms": 8.5}
            exp.fault_state_metrics = {"active_conns": 94.0, "p99_latency_ms": 32.0}
            exp.hypothesis_passed = True
            exp.resilience_score = 92.0
            exp.remediation_latency_seconds = 6.5
            exp.summary = "PASSED: Connection pool throttled queue efficiently with zero dropped SQL queries."
        else:
            exp.hypothesis_passed = True
            exp.resilience_score = 89.0
            exp.remediation_latency_seconds = 8.0
            exp.summary = f"PASSED: Fault '{exp.fault_type.value}' absorbed safely within resilience envelope."

        exp.state = ExperimentState.COMPLETED
        exp.completed_at = utc_now()
        topology_engine.set_service_health(exp.target_service, NodeHealth.HEALTHY)
        return exp

    def stop_experiment(self, experiment_id: str) -> ChaosExperiment:
        """Emergency abort of chaos experiment and return to steady state."""
        exp = self.get_experiment(experiment_id)
        if not exp:
            raise ValueError(f"Experiment '{experiment_id}' not found.")

        exp.state = ExperimentState.ABORTED
        exp.completed_at = utc_now()
        exp.summary = "ABORTED: Operator issued emergency stop."
        topology_engine.set_service_health(exp.target_service, NodeHealth.HEALTHY)
        return exp

    def get_scorecard(self) -> ResilienceScorecard:
        """Calculate aggregate resilience scorecard and reliability index."""
        exps = list(self.experiments.values())
        completed = [e for e in exps if e.state == ExperimentState.COMPLETED]
        passed = sum(1 for e in completed if e.hypothesis_passed is True)
        failed = sum(1 for e in completed if e.hypothesis_passed is False)

        avg_score = round(sum(e.resilience_score for e in completed) / len(completed), 1) if completed else 90.0
        avg_mttr = round(sum(e.remediation_latency_seconds for e in completed) / len(completed), 1) if completed else 20.0

        if avg_score >= 90.0:
            grade = "A+"
        elif avg_score >= 80.0:
            grade = "A"
        elif avg_score >= 70.0:
            grade = "B"
        else:
            grade = "C"

        return ResilienceScorecard(
            evaluated_at=utc_now(),
            cluster_resilience_grade=grade,
            resilience_index=avg_score,
            experiments_run=len(completed),
            hypotheses_validated=passed,
            hypotheses_failed=failed,
            mttr_seconds_avg=avg_mttr,
            experiments=exps,
        )

# Global resilience engine singleton
resilience_engine = ResilienceEngine()
