"""
Day 3 Advanced Features Pytest Suite.
Covers Service Topology & Blast Radius, Predictive Anomaly Forecasting (TTF),
Alert Deduplication & Grouping Engine, and On-Call Schedule & Escalation.
"""
import pytest
from backend.topology.models import NodeHealth, ServiceTier
from backend.topology.engine import TopologyEngine
from backend.prediction.models import UrgencyLevel, TrendDirection
from backend.prediction.engine import PredictionEngine
from backend.grouping.engine import AlertGroupingEngine
from backend.oncall.models import PageStatus, ResponderRole
from backend.oncall.engine import OnCallEngine


class TestTopologyEngine:
    def test_topology_graph_initialization(self):
        engine = TopologyEngine()
        graph = engine.get_graph()
        assert len(graph.nodes) >= 10
        assert len(graph.edges) >= 9
        assert graph.healthy_count == len(graph.nodes)
        assert graph.failing_count == 0

    def test_topology_node_health_update(self):
        engine = TopologyEngine()
        engine.set_service_health("checkout-api", NodeHealth.FAILING, incident_id="inc-99", error_rate_pct=0.25)
        graph = engine.get_graph()
        checkout = next(n for n in graph.nodes if n.id == "checkout-api")
        assert checkout.health == NodeHealth.FAILING
        assert "inc-99" in checkout.active_incidents
        assert checkout.error_rate_pct == 0.25
        assert graph.failing_count == 1

        # Clear health
        engine.clear_service_incidents("checkout-api")
        assert engine.nodes["checkout-api"].health == NodeHealth.HEALTHY

    def test_topology_blast_radius_core_service(self):
        engine = TopologyEngine()
        report = engine.calculate_blast_radius("checkout-api")
        assert report.origin_service == "checkout-api"
        assert "api-gateway" in report.direct_upstream
        assert "edge-ingress" in report.indirect_upstream
        assert "payment-svc" in report.direct_downstream
        assert report.total_blast_score >= 70.0
        assert len(report.critical_services_impacted) > 0
        assert "circuit breaker" in report.mitigation_guidance.lower()

    def test_topology_blast_radius_unknown_service(self):
        engine = TopologyEngine()
        report = engine.calculate_blast_radius("ghost-service")
        assert report.total_blast_score == 0.0
        assert "not found" in report.mitigation_guidance.lower()


class TestPredictionEngine:
    def test_prediction_linear_trend_fitting(self):
        engine = PredictionEngine()
        # Linear slope y = 2x + 10
        points = [(0.0, 10.0), (10.0, 30.0), (20.0, 50.0), (30.0, 70.0)]
        slope, intercept, r2 = engine.calculate_linear_trend(points)
        assert pytest.approx(slope, 0.01) == 2.0
        assert pytest.approx(intercept, 0.01) == 10.0
        assert pytest.approx(r2, 0.01) == 1.0

    def test_prediction_time_to_failure_imminent(self):
        engine = PredictionEngine()
        # Rising memory approaching 1024 MB
        points = [(0.0, 800.0), (60.0, 860.0), (120.0, 920.0)]
        forecast = engine.evaluate_metric(
            metric_name="memory_mb",
            service="checkout-api",
            points=points,
            threshold_critical=1024.0,
            unit="MB",
            higher_is_worse=True,
        )
        assert forecast.trend == TrendDirection.UPWARD
        assert forecast.urgency == UrgencyLevel.CRITICAL
        assert forecast.ttf_seconds is not None
        assert forecast.ttf_seconds <= 120.0
        assert "m " in forecast.ttf_human or "s" in forecast.ttf_human

    def test_prediction_time_to_failure_stable(self):
        engine = PredictionEngine()
        points = [(0.0, 10.0), (30.0, 10.0), (60.0, 10.0)]
        forecast = engine.evaluate_metric(
            metric_name="error_rate",
            service="auth-service",
            points=points,
            threshold_critical=100.0,
            unit="%",
            higher_is_worse=True,
        )
        assert forecast.trend == TrendDirection.FLAT
        assert forecast.urgency == UrgencyLevel.NOMINAL
        assert forecast.ttf_human == "Safe (> 1h)"

    def test_prediction_cluster_summary(self):
        engine = PredictionEngine()
        summary = engine.generate_cluster_predictions()
        assert summary.total_metrics_evaluated >= 4
        assert summary.at_risk_count >= 1
        assert 0.0 <= summary.systemic_risk_index <= 1.0


class TestGroupingEngine:
    def test_grouping_fingerprint_deterministic(self):
        engine = AlertGroupingEngine()
        fp1 = engine.generate_fingerprint("checkout-api", "HighErrorRate")
        fp2 = engine.generate_fingerprint("checkout-api", "HighErrorRate")
        fp3 = engine.generate_fingerprint("auth-service", "HighErrorRate")
        assert fp1 == fp2
        assert fp1 != fp3
        assert len(fp1) == 12

    def test_grouping_duplicate_suppression(self):
        engine = AlertGroupingEngine()
        initial_dups = engine.duplicate_count
        cluster = engine.ingest_alert("a1", "OOMKilled", "test-svc", "critical")
        assert cluster.alerts_count == 1
        assert cluster.duplicate_count == 0

        # Ingest exact same alert again
        cluster2 = engine.ingest_alert("a2", "OOMKilled", "test-svc", "critical")
        assert cluster2.alerts_count == 2
        assert cluster2.duplicate_count == 1
        assert engine.duplicate_count == initial_dups + 1

    def test_grouping_noise_reduction_stats(self):
        engine = AlertGroupingEngine()
        stats = engine.get_noise_reduction_stats()
        assert stats.total_raw_alerts > 0
        assert stats.grouped_incidents > 0
        assert stats.noise_reduction_pct >= 50.0


class TestOnCallEngine:
    def test_oncall_schedule_roster(self):
        engine = OnCallEngine()
        status = engine.get_status()
        assert status.current_shift.primary_responder.role == ResponderRole.PRIMARY_SRE
        assert status.current_shift.primary_responder.name == "Alex Chen"
        assert status.current_shift.secondary_responder.name == "Maria Santos"
        assert status.mtta_seconds_avg > 0

    def test_oncall_page_dispatch_and_acknowledgment(self):
        engine = OnCallEngine()
        page = engine.dispatch_page("inc-404", tier=1, notes="Test page")
        assert page.status == PageStatus.PENDING
        assert page.responder.name == "Alex Chen"
        assert page.tier_level == 1

        acked = engine.acknowledge_page(page.page_id)
        assert acked is not None
        assert acked.status == PageStatus.ACKNOWLEDGED
        assert acked.acknowledged_at is not None

    def test_oncall_page_escalation(self):
        engine = OnCallEngine()
        p1 = engine.dispatch_page("inc-500", tier=1)
        p2 = engine.escalate_page(p1.page_id, reason="Unresponsive after 5m")
        assert p2 is not None
        assert p2.tier_level == 2
        assert p2.responder.name == "Maria Santos"
        assert engine.pages[p1.page_id].status == PageStatus.ESCALATED
