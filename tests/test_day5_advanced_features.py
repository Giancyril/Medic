"""
Day 5 Advanced Features Pytest Suite.
Covers:
1. Multi-Cluster Active-Active Routing & Automated Regional Traffic Evacuation.
2. Incident FinOps Impact & Dynamic Remediation Infrastructure Cost Delta Ledger.
3. Autonomous Closed-Loop Self-Healing Policies with Post-Mitigation Watchdog Verification.
"""
import pytest
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.multicluster.models import ClusterStatus, FailoverEventType
from backend.multicluster.engine import MultiClusterEngine
from backend.finops.models import ImpactTier
from backend.finops.engine import FinOpsEngine
from backend.selfhealing.models import VerificationStatus
from backend.selfhealing.engine import SelfHealingEngine


class TestMultiClusterEngine:
    def test_initial_clusters_and_weights(self):
        engine = MultiClusterEngine()
        overview = engine.get_overview()
        assert len(overview.clusters) >= 3
        # Weight sum should equal 100%
        total_weight = sum(c.traffic_weight_pct for c in overview.clusters)
        assert total_weight == 100
        assert overview.healthy_clusters >= 2

    def test_drain_and_restore_cluster(self):
        engine = MultiClusterEngine()
        target_cluster = engine.list_clusters()[0].cluster_id

        # Drain target cluster
        drained = engine.drain_cluster(target_cluster, reason="Planned regional maintenance")
        assert drained.traffic_weight_pct == 0
        assert drained.status == ClusterStatus.DRAINED

        # Verify traffic redistributed to other clusters to 100%
        remaining_weights = sum(c.traffic_weight_pct for c in engine.list_clusters())
        assert remaining_weights == 100
        assert len(engine.events) >= 1
        assert engine.events[0].cluster_id == target_cluster

        # Restore target cluster
        restored = engine.restore_cluster(target_cluster, target_weight_pct=30)
        assert restored.traffic_weight_pct > 0
        assert restored.status == ClusterStatus.HEALTHY
        total_weights_after = sum(c.traffic_weight_pct for c in engine.list_clusters())
        assert total_weights_after == 100

    def test_shift_traffic(self):
        engine = MultiClusterEngine()
        clusters = engine.list_clusters()
        src = clusters[0].cluster_id
        tgt = clusters[1].cluster_id
        src_orig_weight = clusters[0].traffic_weight_pct
        tgt_orig_weight = clusters[1].traffic_weight_pct

        engine.shift_traffic(source_id=src, target_id=tgt, shift_pct=10)
        updated_src = next(c for c in engine.list_clusters() if c.cluster_id == src)
        updated_tgt = next(c for c in engine.list_clusters() if c.cluster_id == tgt)

        assert updated_src.traffic_weight_pct == src_orig_weight - 10
        assert updated_tgt.traffic_weight_pct == tgt_orig_weight + 10


class TestFinOpsEngine:
    def test_calculate_impact_high_tier(self):
        engine = FinOpsEngine()
        summary = engine.calculate_impact(
            service="checkout-api",
            duration_minutes=15.0,
            error_rate_pct=12.5,
            incident_id="inc-test-finops-1",
        )
        assert summary.service == "checkout-api"
        assert summary.business_impact.cumulative_revenue_loss_usd > 0
        assert summary.business_impact.estimated_failed_transactions > 0
        assert summary.impact_tier == ImpactTier.TIER_1_CRITICAL
        assert summary.total_financial_loss_usd >= summary.business_impact.cumulative_revenue_loss_usd

    def test_remediation_cost_tracking(self):
        engine = FinOpsEngine()
        summary = engine.calculate_impact(
            service="order-db",
            duration_minutes=30.0,
            error_rate_pct=5.0,
            incident_id="inc-test-finops-2",
        )
        initial_cost = summary.total_infra_remediation_cost_usd

        delta = engine.add_remediation_cost(
            incident_id="inc-test-finops-2",
            action_type="horizontal_pod_autoscaling",
            resources="10x c6i.2xlarge spot instances",
            hourly_usd=3.40,
        )
        assert delta.action_type == "horizontal_pod_autoscaling"
        assert delta.hourly_cost_delta_usd == 3.40
        assert summary.total_infra_remediation_cost_usd > initial_cost


class TestSelfHealingEngine:
    def test_list_and_toggle_policies(self):
        engine = SelfHealingEngine()
        policies = engine.list_policies()
        assert len(policies) >= 3

        first_id = policies[0].policy_id
        initially_enabled = policies[0].enabled

        # Toggle policy
        toggled = engine.toggle_policy(first_id, not initially_enabled)
        assert toggled.enabled == (not initially_enabled)

        # Toggle back
        restored = engine.toggle_policy(first_id, initially_enabled)
        assert restored.enabled == initially_enabled

    def test_execute_policy_closed_loop(self):
        engine = SelfHealingEngine()
        policies = [p for p in engine.list_policies() if p.enabled]
        assert len(policies) > 0
        policy = policies[0]

        execution = engine.execute_policy(
            policy_id=policy.policy_id,
            incident_id="inc-heal-test-01",
            initial_metrics={"http_error_rate_pct": 14.5, "cpu_usage_pct": 89.0},
        )
        assert execution.policy_id == policy.policy_id
        assert execution.status == VerificationStatus.VERIFIED_RESOLVED
        assert "nominal" in execution.watchdog_verdict.lower() or "closed-loop" in execution.watchdog_verdict.lower()

        # Check guardrails
        guardrails = engine.get_guardrail_status()
        assert guardrails.actions_in_current_window >= 1


class TestDay5ApiEndpoints:
    @pytest.mark.asyncio
    async def test_multicluster_endpoints(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res_overview = await client.get("/api/v1/multicluster/overview")
            assert res_overview.status_code == 200
            assert "clusters" in res_overview.json()

            res_clusters = await client.get("/api/v1/multicluster/clusters")
            assert res_clusters.status_code == 200
            clusters = res_clusters.json()["clusters"]
            assert len(clusters) >= 3

            cluster_id = clusters[0]["cluster_id"]
            res_drain = await client.post(
                f"/api/v1/multicluster/clusters/{cluster_id}/drain",
                json={"reason": "Automated regional isolation"},
            )
            assert res_drain.status_code == 200
            assert res_drain.json()["status"] == "drained"

            res_restore = await client.post(
                f"/api/v1/multicluster/clusters/{cluster_id}/restore",
                json={"target_weight_pct": 35},
            )
            assert res_restore.status_code == 200
            assert res_restore.json()["status"] == "restored"

    @pytest.mark.asyncio
    async def test_finops_endpoints(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res_summaries = await client.get("/api/v1/finops/summaries")
            assert res_summaries.status_code == 200
            assert "summaries" in res_summaries.json()

            res_calc = await client.post(
                "/api/v1/finops/calculate",
                json={
                    "service": "checkout-api",
                    "duration_minutes": 10.0,
                    "error_rate_pct": 9.2,
                    "incident_id": "inc-calc-test",
                },
            )
            assert res_calc.status_code == 200
            data = res_calc.json()
            assert data["service"] == "checkout-api"
            assert data["total_financial_loss_usd"] > 0

            res_cost = await client.post(
                "/api/v1/finops/remediation-cost",
                json={
                    "incident_id": "inc-calc-test",
                    "action_type": "read_replica_spinup",
                    "resources": "2x db.r6g.xlarge Aurora read replicas",
                    "hourly_usd": 1.28,
                },
            )
            assert res_cost.status_code == 200
            assert res_cost.json()["action_type"] == "read_replica_spinup"

    @pytest.mark.asyncio
    async def test_selfhealing_endpoints(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res_policies = await client.get("/api/v1/selfhealing/policies")
            assert res_policies.status_code == 200
            policies = res_policies.json()["policies"]
            assert len(policies) >= 3

            policy_id = policies[0]["policy_id"]
            res_toggle = await client.post(
                f"/api/v1/selfhealing/policies/{policy_id}/toggle",
                json={"enabled": True},
            )
            assert res_toggle.status_code == 200
            assert res_toggle.json()["enabled"] is True

            res_exec = await client.post(
                f"/api/v1/selfhealing/policies/{policy_id}/execute",
                json={
                    "incident_id": "inc-api-test-01",
                    "initial_metrics": {"http_error_rate_pct": 12.0},
                },
            )
            assert res_exec.status_code == 200
            assert res_exec.json()["status"] == "verified_resolved"

            res_guard = await client.get("/api/v1/selfhealing/guardrails")
            assert res_guard.status_code == 200
            assert "velocity_limit_per_15m" in res_guard.json()
