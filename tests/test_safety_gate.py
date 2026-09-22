import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.core.database import reset_db
from backend.tools.cluster_simulator import simulator
from backend.remediation.catalog import build_remediation_action, RiskTier
from backend.remediation.executor import execute_remediation, SafetyGateError

@pytest.mark.asyncio
async def test_safety_gate_blocks_unapproved_tier3_action():
    action = build_remediation_action("ROLLBACK_DEPLOYMENT", service="payment-api", namespace="production")
    assert action.risk_tier == RiskTier.TIER_3_HIGH
    assert action.requires_human_approval is True

    # Direct execution without approval MUST raise SafetyGateError
    with pytest.raises(SafetyGateError) as exc_info:
        await execute_remediation(action, is_approved_by_human=False)
    assert "SAFETY GATE BLOCKED" in str(exc_info.value)

@pytest.mark.asyncio
async def test_safety_gate_allows_approved_tier3_action():
    action = build_remediation_action("ROLLBACK_DEPLOYMENT", service="payment-api", namespace="production")
    
    # Approved execution succeeds
    res = await execute_remediation(action, is_approved_by_human=True, approver="alice@company.com")
    assert res["status"] == "SUCCESS"
    assert res["approved_by"] == "alice@company.com"

@pytest.mark.asyncio
async def test_dry_run_mode_generates_diff_without_mutations():
    action = build_remediation_action("ROLLBACK_DEPLOYMENT", service="order-processor", namespace="production")
    res = await execute_remediation(action, is_approved_by_human=False, dry_run=True)
    assert res["status"] == "DRY_RUN_SUCCESS"
    assert "--- a/deployment/order-processor" in res["diff"]

@pytest.mark.asyncio
async def test_full_incident_approval_lifecycle_api():
    await reset_db()
    simulator.inject_chaos_scenario("CrashLoopBackOff", service="payment-api", namespace="production")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Ingest alert
        alert_payload = {
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
                        "summary": "Payment API crashed on startup"
                    }
                }
            ]
        }
        res1 = await client.post("/api/v1/alerts/webhook", json=alert_payload)
        assert res1.status_code == 202
        inc_id = res1.json()["incidents"][0]["incident_id"]

        # 2. Trigger LangGraph investigation & diagnosis
        inv_res = await client.post(f"/api/v1/incidents/{inc_id}/investigate")
        assert inv_res.status_code == 200
        inv_data = inv_res.json()
        assert inv_data["status"] == "ACTION_REQUIRED"
        assert inv_data["remediation"]["action_type"] == "ROLLBACK_DEPLOYMENT"
        assert inv_data["remediation"]["risk_tier"] == "TIER_3_HIGH"

        # 3. Retrieve diff preview
        diff_res = await client.get(f"/api/v1/incidents/{inc_id}/diff")
        assert diff_res.status_code == 200
        diff_data = diff_res.json()
        assert "diff" in diff_data
        assert "--- a/deployment/payment-api" in diff_data["diff"]

        # 4. Approve gated action
        appr_res = await client.post(
            f"/api/v1/incidents/{inc_id}/approve",
            json={"approver": "sre-lead@acme.corp", "comment": "Approved rollback to v1.4.1"}
        )
        assert appr_res.status_code == 200
        resolved_data = appr_res.json()
        assert resolved_data["status"] == "RESOLVED"
        assert resolved_data["resolved_at"] is not None

        # Verify event audit trail contains approval record
        events = resolved_data["events"]
        assert any(e["event_type"] == "ACTION_EXECUTED" for e in events)
