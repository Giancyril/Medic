import pytest
from backend.tools.cluster_simulator import simulator
from backend.tools.investigator import collect_evidence
from backend.agent.diagnose import diagnose_incident_evidence

@pytest.mark.asyncio
async def test_diagnosis_oomkilled():
    simulator.inject_chaos_scenario("OOMKilled", service="order-processor", namespace="production")
    evidence = await collect_evidence("order-processor", "production")
    
    diagnosis = diagnose_incident_evidence(evidence, alert_summary="Pod order-processor is OOMKilled")
    assert diagnosis.confidence >= 0.90
    assert "memory" in diagnosis.root_cause.lower()
    assert len(diagnosis.supporting_evidence) >= 2
    assert diagnosis.action_type == "RESTART_POD"
    assert diagnosis.requires_escalation is False

@pytest.mark.asyncio
async def test_diagnosis_crashloop():
    simulator.inject_chaos_scenario("CrashLoopBackOff", service="payment-api", namespace="production")
    evidence = await collect_evidence("payment-api", "production")
    
    diagnosis = diagnose_incident_evidence(evidence, alert_summary="Pod payment-api is CrashLooping")
    assert diagnosis.confidence >= 0.90
    assert "startup" in diagnosis.root_cause.lower() or "crash" in diagnosis.root_cause.lower()
    assert diagnosis.action_type == "ROLLBACK_DEPLOYMENT"
    assert diagnosis.risk_tier == "TIER_3_HIGH"
    assert diagnosis.requires_escalation is False

@pytest.mark.asyncio
async def test_diagnosis_upstream_timeout():
    simulator.inject_chaos_scenario("UpstreamTimeout", service="auth-service", namespace="production")
    evidence = await collect_evidence("auth-service", "production")
    
    diagnosis = diagnose_incident_evidence(evidence, alert_summary="High latency on auth-service")
    assert diagnosis.confidence >= 0.85
    assert "pool" in diagnosis.root_cause.lower() or "timeout" in diagnosis.root_cause.lower() or "latency" in diagnosis.root_cause.lower()
    assert diagnosis.requires_escalation is False

@pytest.mark.asyncio
async def test_diagnosis_ambiguous_escalation():
    # Fresh healthy evidence with vague alert
    simulator._seed_default_state()
    evidence = await collect_evidence("inventory-db", "production")
    
    diagnosis = diagnose_incident_evidence(evidence, alert_summary="Intermittent flapping alert")
    assert diagnosis.confidence < 0.70
    assert diagnosis.requires_escalation is True
    assert diagnosis.action_type == "ESCALATE_HUMAN"
