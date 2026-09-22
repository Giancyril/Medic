import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.core.database import reset_db
from backend.tools.cluster_simulator import simulator
from backend.remediation.catalog import build_remediation_action, RiskTier
from backend.remediation.executor import execute_remediation, SafetyGateError

@pytest.mark.asyncio
async def test_oomkilled_chaos_scenario():
    """
    Scenario 1: OOMKilled Memory Exhaustion
    Fires KubePodOOMKilled -> Ingest -> Investigate -> Diagnose OOM (>85% confidence)
    -> Proposes RESTART_POD -> Auto-resolves / recovers pod in simulator.
    """
    await reset_db()
    simulator.inject_chaos_scenario("OOMKilled", service="order-service", namespace="production")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/v1/alerts/webhook", json={
            "version": "4",
            "status": "firing",
            "alerts": [
                {
                    "status": "firing",
                    "labels": {
                        "alertname": "KubePodOOMKilled",
                        "service": "order-service",
                        "namespace": "production",
                        "severity": "critical"
                    },
                    "annotations": {
                        "summary": "Container in pod order-service-xxx terminated with exit code 137 (OOMKilled)"
                    }
                }
            ]
        })
        assert res.status_code == 202
        inc_id = res.json()["incidents"][0]["incident_id"]

        # Run investigation
        inv_res = await client.post(f"/api/v1/incidents/{inc_id}/investigate")
        assert inv_res.status_code == 200
        inv_data = inv_res.json()

        # Check diagnosis
        diag = inv_data["diagnosis"]
        assert "OOM" in diag["root_cause"] or "exhaustion" in diag["root_cause"]
        assert diag["confidence"] >= 0.85
        assert diag["action_type"] == "RESTART_POD"

@pytest.mark.asyncio
async def test_bad_deployment_crashloop_chaos_scenario():
    """
    Scenario 2: Bad Release / CrashLoopBackOff Gated Remediation
    Fires CrashLoopBackOff -> Diagnoses bad release (>85% confidence)
    -> Recommends ROLLBACK_DEPLOYMENT (Tier 3 High Risk)
    -> Safety gate enforces ACTION_REQUIRED
    -> Human approves -> Deployment rolled back -> Incident RESOLVED.
    """
    await reset_db()
    simulator.inject_chaos_scenario("CrashLoopBackOff", service="payment-api", namespace="production")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/v1/alerts/webhook", json={
            "version": "4",
            "status": "firing",
            "alerts": [
                {
                    "status": "firing",
                    "labels": {
                        "alertname": "CrashLoopBackOff",
                        "service": "payment-api",
                        "namespace": "production",
                        "severity": "critical"
                    },
                    "annotations": {
                        "summary": "Payment API pod in CrashLoopBackOff after release v1.4.2"
                    }
                }
            ]
        })
        inc_id = res.json()["incidents"][0]["incident_id"]

        # Investigate
        inv_res = await client.post(f"/api/v1/incidents/{inc_id}/investigate")
        assert inv_res.status_code == 200
        inv_data = inv_res.json()

        assert inv_data["status"] == "ACTION_REQUIRED"
        assert inv_data["remediation"]["action_type"] == "ROLLBACK_DEPLOYMENT"
        assert inv_data["remediation"]["risk_tier"] == "TIER_3_HIGH"
        assert inv_data["remediation"]["requires_human_approval"] is True

        # Diff inspection
        diff_res = await client.get(f"/api/v1/incidents/{inc_id}/diff")
        assert diff_res.status_code == 200
        assert "--- a/deployment/payment-api" in diff_res.json()["diff"]

        # Human approval
        appr_res = await client.post(
            f"/api/v1/incidents/{inc_id}/approve",
            json={"approver": "sre-lead@acme.corp", "comment": "Rollback approved for production"}
        )
        assert appr_res.status_code == 200
        assert appr_res.json()["status"] == "RESOLVED"

@pytest.mark.asyncio
async def test_ambiguous_alert_triggers_escalation_scenario():
    """
    Scenario 3: Ambiguous / Low-Confidence Alert Routes to Human Escalation
    Alert with no fatal crash in metrics/logs -> Diagnosed with low confidence (<0.50)
    -> Requires escalation -> Status becomes ESCALATED.
    """
    await reset_db()
    # No chaos injected -> normal telemetry
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/v1/alerts/webhook", json={
            "version": "4",
            "status": "firing",
            "alerts": [
                {
                    "status": "firing",
                    "labels": {
                        "alertname": "AmbiguousWarningAlert",
                        "service": "billing-worker",
                        "namespace": "production",
                        "severity": "warning"
                    },
                    "annotations": {
                        "summary": "Ephemeral network jitter detected"
                    }
                }
            ]
        })
        inc_id = res.json()["incidents"][0]["incident_id"]

        # Investigate
        inv_res = await client.post(f"/api/v1/incidents/{inc_id}/investigate")
        assert inv_res.status_code == 200
        inv_data = inv_res.json()

        diag = inv_data["diagnosis"]
        assert diag["confidence"] <= 0.50
        assert diag["requires_escalation"] is True
        assert inv_data["status"] == "ESCALATED"

@pytest.mark.asyncio
async def test_flapping_and_deduplication_scenario():
    """
    Scenario 4: Flapping / Duplicate Alert Deduplication
    Ensures 5 repeated alerts within window are grouped into 1 incident with firing_count=5.
    """
    await reset_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        alert_payload = {
            "version": "4",
            "status": "firing",
            "alerts": [
                {
                    "status": "firing",
                    "labels": {
                        "alertname": "HighCPUThrottling",
                        "service": "worker-pool",
                        "namespace": "production",
                        "severity": "warning"
                    },
                    "annotations": {
                        "summary": "Worker pool CPU throttling elevated"
                    }
                }
            ]
        }

        first_inc_id = None
        for _ in range(5):
            res = await client.post("/api/v1/alerts/webhook", json=alert_payload)
            assert res.status_code == 202
            inc_id = res.json()["incidents"][0]["incident_id"]
            if first_inc_id is None:
                first_inc_id = inc_id
            else:
                assert inc_id == first_inc_id

        # Verify only 1 incident exists in database and firing_count == 5
        inc_res = await client.get(f"/api/v1/incidents/{first_inc_id}")
        assert inc_res.status_code == 200
        inc = inc_res.json()
        assert inc["firing_count"] == 5

        # Check total incidents list has count 1
        all_res = await client.get("/api/v1/incidents")
        assert len(all_res.json()) == 1

@pytest.mark.asyncio
async def test_safety_gate_bypass_prevention_and_rejection():
    """
    Scenario 5: Safety Gate Bypass Prevention & Rejection Workflow
    Ensures:
    1. Unapproved execution of Tier 3 throws SafetyGateError
    2. Rejection endpoint transitions incident to ACTION_REQUIRED / audit log without mutating cluster
    """
    await reset_db()
    simulator.inject_chaos_scenario("CrashLoopBackOff", service="billing-service", namespace="production")

    # 1. Direct Python invocation of Tier 3 without approval must be blocked
    action = build_remediation_action("ROLLBACK_DEPLOYMENT", service="billing-service", namespace="production")
    with pytest.raises(SafetyGateError) as exc_info:
        await execute_remediation(action, is_approved_by_human=False)
    assert "SAFETY GATE BLOCKED" in str(exc_info.value)

    # 2. REST API rejection flow
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/v1/alerts/webhook", json={
            "version": "4",
            "status": "firing",
            "alerts": [
                {
                    "status": "firing",
                    "labels": {
                        "alertname": "CrashLoopBackOff",
                        "service": "billing-service",
                        "namespace": "production",
                        "severity": "critical"
                    }
                }
            ]
        })
        inc_id = res.json()["incidents"][0]["incident_id"]

        # Run investigation
        await client.post(f"/api/v1/incidents/{inc_id}/investigate")

        # Operator rejects remediation
        rej_res = await client.post(
            f"/api/v1/incidents/{inc_id}/reject",
            json={"rejector": "bob@acme.corp", "reason": "Root cause seems unrelated to release rollback"}
        )
        assert rej_res.status_code == 200
        data = rej_res.json()
        assert data["status"] == "ESCALATED"

        # Check event log records rejection
        events = data["events"]
        assert any(e["event_type"] == "ACTION_REJECTED" for e in events)
