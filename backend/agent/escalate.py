import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import json
from backend.app.core.config import settings

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class EscalationDispatcher:
    """
    Dispatches rich incident context (Golden Signals, Diagnosis, Confidence,
    Diff Preview, and Approval Deep-Links) to Slack and PagerDuty.
    """
    def __init__(self):
        self.dispatched_history: List[Dict[str, Any]] = []

    def format_slack_blocks(self, incident: Dict[str, Any], diagnosis: Dict[str, Any], action: Dict[str, Any]) -> Dict[str, Any]:
        severity = incident.get("severity", "warning").upper()
        emoji = ":rotating_light:" if severity == "CRITICAL" else ":warning:"
        inc_id = incident.get("id", "inc-unknown")
        service = incident.get("service", "app")
        confidence = round(diagnosis.get("confidence", 0.0) * 100, 1)

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} INCIDENT ESCALATION: [{severity}] {service}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Incident ID:*\n`{inc_id}`"},
                    {"type": "mrkdwn", "text": f"*Affected Service:*\n`{service}`"},
                    {"type": "mrkdwn", "text": f"*Diagnosis Confidence:*\n`{confidence}%`"},
                    {"type": "mrkdwn", "text": f"*Action Risk Tier:*\n`{action.get('risk_tier', 'TIER_3_HIGH')}`"}
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Probable Root Cause:*\n{diagnosis.get('root_cause', 'Inconclusive telemetry analysis.')}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Proposed Remediation:*\n*{action.get('name', 'Manual Triage')}*\n```{action.get('diff_preview', 'No diff available.')}```"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Approve & Remediate"},
                        "style": "primary",
                        "value": f"approve_{inc_id}"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Reject Action"},
                        "style": "danger",
                        "value": f"reject_{inc_id}"
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Open Dashboard"},
                        "url": f"http://localhost:5173/incident/{inc_id}"
                    }
                ]
            }
        ]
        return {"blocks": blocks}

    async def dispatch_slack(self, incident: Dict[str, Any], diagnosis: Dict[str, Any], action: Dict[str, Any]) -> Dict[str, Any]:
        payload = self.format_slack_blocks(incident, diagnosis, action)
        record = {
            "channel": "slack",
            "incident_id": incident.get("id"),
            "timestamp": utc_now().isoformat(),
            "payload": payload,
            "status": "SENT"
        }
        self.dispatched_history.append(record)

        if settings.SLACK_WEBHOOK_URL and not settings.SIMULATION_MODE:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(settings.SLACK_WEBHOOK_URL, json=payload)

        return record

    async def dispatch_pagerduty(self, incident: Dict[str, Any], diagnosis: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "routing_key": settings.PAGERDUTY_ROUTING_KEY or "simulated-pd-key",
            "event_action": "trigger",
            "dedup_key": incident.get("fingerprint"),
            "payload": {
                "summary": f"[{incident.get('severity', 'warning').upper()}] {incident.get('service')}: {diagnosis.get('root_cause', '')[:100]}",
                "severity": incident.get("severity", "warning"),
                "source": "incident-response-agent",
                "component": incident.get("service"),
                "custom_details": {
                    "incident_id": incident.get("id"),
                    "confidence": diagnosis.get("confidence"),
                    "supporting_evidence": diagnosis.get("supporting_evidence", [])
                }
            }
        }
        record = {
            "channel": "pagerduty",
            "incident_id": incident.get("id"),
            "timestamp": utc_now().isoformat(),
            "payload": payload,
            "status": "SENT"
        }
        self.dispatched_history.append(record)
        return record

dispatcher = EscalationDispatcher()
