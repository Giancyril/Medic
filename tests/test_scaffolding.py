import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app

@pytest.mark.asyncio
async def test_health_check():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "Incident Response Agent" in data["service"]

@pytest.mark.asyncio
async def test_webhook_stub():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "version": "4",
            "status": "firing",
            "receiver": "incident-agent-webhook",
            "groupLabels": {"alertname": "HighMemoryUsage"},
            "commonLabels": {"service": "payment-api", "namespace": "production"},
            "commonAnnotations": {"summary": "Payment API memory usage exceeded 90%"},
            "alerts": [
                {
                    "status": "firing",
                    "labels": {
                        "alertname": "HighMemoryUsage",
                        "service": "payment-api",
                        "namespace": "production",
                        "severity": "critical"
                    },
                    "annotations": {
                        "summary": "Container payment-api is near memory limit"
                    }
                }
            ]
        }
        response = await client.post("/api/v1/alerts/webhook", json=payload)
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted"
        assert data["alerts_received"] == 1
