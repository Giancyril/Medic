import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.core.database import reset_db

@pytest.mark.asyncio
async def test_alert_ingestion_and_deduplication():
    await reset_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Ingest initial alert
        payload1 = {
            "version": "4",
            "status": "firing",
            "receiver": "webhook-receiver",
            "alerts": [
                {
                    "status": "firing",
                    "labels": {
                        "alertname": "PodCrashLooping",
                        "service": "order-processor",
                        "namespace": "ecommerce",
                        "severity": "critical"
                    },
                    "annotations": {
                        "summary": "Pod order-processor-79d9cb is crash looping",
                        "description": "Container exited with code 1"
                    }
                }
            ]
        }
        res1 = await client.post("/api/v1/alerts/webhook", json=payload1)
        assert res1.status_code == 202
        data1 = res1.json()
        assert data1["incidents_processed"] == 1
        incident_id = data1["incidents"][0]["incident_id"]
        assert data1["incidents"][0]["firing_count"] == 1

        # 2. Ingest duplicate alert for same issue -> Should dedup into same incident
        payload2 = {
            "version": "4",
            "status": "firing",
            "receiver": "webhook-receiver",
            "alerts": [
                {
                    "status": "firing",
                    "labels": {
                        "alertname": "PodCrashLooping",
                        "service": "order-processor",
                        "namespace": "ecommerce",
                        "severity": "critical"
                    },
                    "annotations": {
                        "summary": "Pod order-processor-79d9cb is still crash looping (repeat)",
                    }
                }
            ]
        }
        res2 = await client.post("/api/v1/alerts/webhook", json=payload2)
        assert res2.status_code == 202
        data2 = res2.json()
        assert data2["incidents_processed"] == 1
        assert data2["incidents"][0]["incident_id"] == incident_id
        assert data2["incidents"][0]["firing_count"] == 2

        # 3. Ingest alert for different service -> Should create new incident
        payload3 = {
            "version": "4",
            "status": "firing",
            "alerts": [
                {
                    "status": "firing",
                    "labels": {
                        "alertname": "HighLatencyP99",
                        "service": "auth-service",
                        "namespace": "security",
                        "severity": "warning"
                    },
                    "annotations": {
                        "summary": "Auth service latency spiked above 500ms"
                    }
                }
            ]
        }
        res3 = await client.post("/api/v1/alerts/webhook", json=payload3)
        assert res3.status_code == 202
        data3 = res3.json()
        new_inc_id = data3["incidents"][0]["incident_id"]
        assert new_inc_id != incident_id

        # 4. Query incident list
        list_res = await client.get("/api/v1/incidents")
        assert list_res.status_code == 200
        items = list_res.json()
        assert len(items) >= 2
        # Check filtered query
        filt_res = await client.get("/api/v1/incidents?severity=critical")
        assert filt_res.status_code == 200
        filt_items = filt_res.json()
        assert all(it["severity"] == "critical" for it in filt_items)

        # 5. Query incident detail with events
        detail_res = await client.get(f"/api/v1/incidents/{incident_id}")
        assert detail_res.status_code == 200
        detail = detail_res.json()
        assert detail["id"] == incident_id
        assert detail["firing_count"] == 2
        assert len(detail["events"]) >= 2
        event_types = [e["event_type"] for e in detail["events"]]
        assert "ALERT_INGESTED" in event_types
        assert "ALERT_DEDUPED" in event_types

        # 6. Status update
        status_res = await client.patch(
            f"/api/v1/incidents/{incident_id}/status",
            json={"status": "INVESTIGATING", "reason": "SRE bot dispatched investigation"}
        )
        assert status_res.status_code == 200
        updated = status_res.json()
        assert updated["status"] == "INVESTIGATING"
