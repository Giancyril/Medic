"""
Day 4 Advanced Features Pytest Suite.
Covers Automated Canary Analysis (ACA), Progressive Traffic Splitting & Rollback State Machine,
Chaos Engineering Fault Injection & Resilience Scorecard, and Cryptographic Tamper-Evident Audit Ledger & Replay.
"""
import pytest
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.canary.models import CanaryPhase, MetricComparisonStatus
from backend.canary.engine import CanaryAnalysisEngine
from backend.canary.orchestrator import CanaryOrchestrator, canary_orchestrator
from backend.resilience.models import FaultType, ExperimentState
from backend.resilience.engine import ResilienceEngine
from backend.audit.models import ActorType, ActionCategory
from backend.audit.engine import AuditReplayEngine


class TestCanaryEngine:
    def test_canary_initial_catalog(self):
        engine = CanaryAnalysisEngine()
        assert "dep-canary-checkout-v24" in engine.deployments
        dep = engine.deployments["dep-canary-checkout-v24"]
        assert dep.service == "checkout-api"
        assert dep.canary_version == "v2.4.0-rc2"
        assert dep.current_weight_pct == 10

    def test_canary_metric_analysis(self):
        engine = CanaryAnalysisEngine()
        report = engine.analyze_metrics(
            deployment_id="dep-canary-checkout-v24",
            service="checkout-api",
            baseline_version="v2.3.9",
            canary_version="v2.4.0-rc2",
            traffic_split_pct=10,
        )
        assert report.deployment_id == "dep-canary-checkout-v24"
        assert 0.0 <= report.overall_score <= 100.0
        assert len(report.metrics) >= 4
        metric_names = [m.metric_name for m in report.metrics]
        assert "http_error_rate_pct" in metric_names
        assert "http_request_p95_latency_ms" in metric_names
        assert report.verdict in [
            MetricComparisonStatus.PASS,
            MetricComparisonStatus.WARN,
            MetricComparisonStatus.FAIL,
        ]

    def test_canary_traffic_advancement(self):
        orch = CanaryOrchestrator()
        dep = orch.get_deployment("dep-canary-checkout-v24")
        assert dep is not None
        dep.phase = CanaryPhase.RUNNING
        dep.current_step_index = 0
        dep.current_weight_pct = 5
        dep.auto_rollback_enabled = False  # Isolate step progression from automated circuit breaker

        updated_dep, report = orch.advance_traffic("dep-canary-checkout-v24")
        assert updated_dep.current_step_index == 1
        assert updated_dep.current_weight_pct == 10
        assert updated_dep.last_report is not None

    def test_canary_manual_and_automated_rollback(self):
        orch = CanaryOrchestrator()
        dep = orch.rollback_canary("dep-canary-checkout-v24", reason="Test manual safety trigger")
        assert dep.phase == CanaryPhase.ROLLED_BACK
        assert dep.current_weight_pct == 0

    def test_canary_full_promotion(self):
        orch = CanaryOrchestrator()
        dep = orch.promote_canary("dep-canary-checkout-v24")
        assert dep.phase == CanaryPhase.PROMOTED
        assert dep.current_weight_pct == 100


class TestResilienceEngine:
    def test_resilience_catalog_initialization(self):
        engine = ResilienceEngine()
        experiments = engine.list_experiments()
        assert len(experiments) >= 4
        exp_ids = [e.experiment_id for e in experiments]
        assert "exp-redis-partition" in exp_ids
        assert "exp-checkout-pod-kill" in exp_ids
        assert "exp-postgres-deadlock" in exp_ids

    def test_resilience_launch_experiment(self):
        engine = ResilienceEngine()
        exp = engine.launch_experiment("exp-postgres-deadlock")
        assert exp.state == ExperimentState.COMPLETED
        assert exp.hypothesis_passed is not None
        assert exp.resilience_score > 0
        assert exp.steady_state_metrics is not None
        assert exp.fault_state_metrics is not None

    def test_resilience_scorecard_calculation(self):
        engine = ResilienceEngine()
        scorecard = engine.get_scorecard()
        assert scorecard.experiments_run >= 3
        assert scorecard.resilience_index >= 0.0
        assert scorecard.cluster_resilience_grade in ["A+", "A", "B", "C", "D", "F"]
        assert scorecard.mttr_seconds_avg >= 0.0
        assert len(scorecard.experiments) >= 4

    def test_resilience_terminate_experiment(self):
        engine = ResilienceEngine()
        exp = engine.stop_experiment("exp-postgres-deadlock")
        assert exp.state == ExperimentState.ABORTED
        assert "ABORTED" in exp.summary.upper()


class TestAuditReplayEngine:
    def test_audit_trail_entry_recording_and_hashing(self):
        engine = AuditReplayEngine()
        initial_count = len(engine.ledger)
        entry = engine.record_entry(
            incident_id="inc-test-01",
            actor_type=ActorType.AI_AGENT,
            actor_name="IncidentCommanderAI",
            category=ActionCategory.REMEDIATION_EXECUTION,
            action_summary="Scaled checkout-api replicas from 4 to 8",
            details={"replicas_before": 4, "replicas_after": 8},
        )
        assert entry.incident_id == "inc-test-01"
        assert len(entry.tamper_hash) == 64
        assert len(engine.ledger) == initial_count + 1

    def test_audit_trail_cryptographic_verification(self):
        engine = AuditReplayEngine()
        valid = engine.verify_audit_integrity()
        assert valid is True

    def test_audit_trail_tamper_detection(self):
        engine = AuditReplayEngine()
        # Deliberately mutate an entry's action summary
        engine.ledger[2].action_summary = "UNAUTHORIZED_ALTERATION"
        valid = engine.verify_audit_integrity()
        assert valid is False

    def test_compliance_report_generation(self):
        engine = AuditReplayEngine()
        report = engine.generate_compliance_report("inc-demo-1")
        assert report.incident_id == "inc-demo-1"
        assert report.total_actions >= 5
        assert report.soc2_compliant is True
        assert report.audit_trail_verified is True

    def test_incident_replay_frames(self):
        engine = AuditReplayEngine()
        frames = engine.get_replay_timeline("inc-demo-1")
        assert len(frames) >= 5
        for i in range(len(frames) - 1):
            assert frames[i].frame_index < frames[i + 1].frame_index
        assert "KubePodCrashLooping" in frames[0].event_title


@pytest.mark.asyncio
class TestDay4Endpoints:
    async def test_canary_deployments_endpoint(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/v1/canary/deployments")
            assert res.status_code == 200
            data = res.json()
            assert "deployments" in data
            assert len(data["deployments"]) >= 1

    async def test_canary_deployment_detail_endpoint(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/v1/canary/deployments/dep-canary-checkout-v24")
            assert res.status_code == 200
            data = res.json()
            assert data["deployment_id"] == "dep-canary-checkout-v24"

    async def test_canary_advance_and_rollback_endpoints(self):
        dep = canary_orchestrator.get_deployment("dep-canary-checkout-v24")
        if dep:
            dep.phase = CanaryPhase.RUNNING
            dep.current_step_index = 0
            dep.current_weight_pct = 5
            dep.auto_rollback_enabled = False

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res_adv = await client.post("/api/v1/canary/deployments/dep-canary-checkout-v24/advance")
            assert res_adv.status_code == 200
            adv_data = res_adv.json()
            assert "deployment" in adv_data

            res_rollback = await client.post(
                "/api/v1/canary/deployments/dep-canary-checkout-v24/rollback",
                json={"reason": "Manual safety trigger"},
            )
            assert res_rollback.status_code == 200
            rollback_data = res_rollback.json()
            assert rollback_data["phase"] == "rolled_back"

    async def test_resilience_endpoints(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res_scorecard = await client.get("/api/v1/resilience/scorecard")
            assert res_scorecard.status_code == 200
            assert "resilience_index" in res_scorecard.json()

            res_exps = await client.get("/api/v1/resilience/experiments")
            assert res_exps.status_code == 200
            assert "experiments" in res_exps.json()

            res_launch = await client.post("/api/v1/resilience/experiments/exp-postgres-deadlock/launch")
            assert res_launch.status_code == 200
            assert res_launch.json()["state"] == "completed"

    async def test_audit_endpoints(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res_ledger = await client.get("/api/v1/audit/ledger")
            assert res_ledger.status_code == 200
            assert "ledger" in res_ledger.json()
            assert res_ledger.json()["integrity_verified"] is True

            res_compliance = await client.get("/api/v1/audit/compliance/inc-demo-1")
            assert res_compliance.status_code == 200
            assert "soc2_compliant" in res_compliance.json()

            res_replay = await client.get("/api/v1/audit/replay/inc-demo-1")
            assert res_replay.status_code == 200
            assert "frames" in res_replay.json()
            assert len(res_replay.json()["frames"]) >= 5
