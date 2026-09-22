import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.core.database import reset_db
from backend.agent.escalate import dispatcher

@pytest.mark.asyncio
async def test_slack_block_kit_payload():
    incident = {
        "id": "inc-test-01",
        "service": "order-processor",
        "severity": "critical"
    }
    diagnosis = {
        "root_cause": "Container memory limit exceeded",
        "confidence": 0.95
    }
    action = {
        "name": "Restart failed pod",
        "risk_tier": "TIER_1_LOW",
        "diff_preview": "# kubectl delete pod order-processor-abc"
    }

    blocks_data = dispatcher.format_slack_blocks(incident, diagnosis, action)
    assert "blocks" in blocks_data
    blocks = blocks_data["blocks"]
    assert any("INCIDENT ESCALATION" in str(b) for b in blocks)
    assert any("order-processor" in str(b) for b in blocks)
    assert any("Approve & Remediate" in str(b) for b in blocks)

@pytest.mark.asyncio
async def test_pagerduty_dispatch():
    incident = {
        "id": "inc-test-02",
        "service": "payment-api",
        "severity": "critical",
        "fingerprint": "fp-12345"
    }
    diagnosis = {
        "root_cause": "Connection pool timeout",
        "confidence": 0.88,
        "supporting_evidence": ["P99 latency > 3000ms"]
    }
    res = await dispatcher.dispatch_pagerduty(incident, diagnosis)
    assert res["status"] == "SENT"
    assert res["payload"]["dedup_key"] == "fp-12345"
    assert res["payload"]["payload"]["component"] == "payment-api"

@pytest.mark.asyncio
async def test_api_escalate_endpoint():
    await reset_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create incident
        alert_payload = {
            "version": "4",
            "status": "firing",
            "alerts": [
                {
                    "status": "firing",
                    "labels": {"alertname": "DatabaseDeadlock", "service": "billing-service", "namespace": "production"},
                    "annotations": {"summary": "Database deadlocks detected"}
                }
            ]
        }
        create_res = await client.post("/api/v1/alerts/webhook", json=alert_payload)
        inc_id = create_res.json()["incidents"][0]["incident_id"]

        # Escalate
        esc_res = await client.post(
            f"/api/v1/incidents/{inc_id}/escalate",
            json={"reason": "Complex database deadlock requiring senior DBA intervention", "channel": "all"}
        )
        assert esc_res.status_code == 200
        esc_data = esc_res.json()
        assert esc_data["status"] == "ESCALATED"
        events = esc_data["events"]
        assert any(e["event_type"] == "ESCALATED" for e in events)
