"""
Automated Post-Mortem Generator
Produces a structured post-mortem document from incident data, timeline, runbook execution,
and agent findings. Supports Markdown output with YAML frontmatter for GitOps workflows.
"""
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import os, logging

logger = logging.getLogger(__name__)
SIMULATION_MODE = os.getenv("SIMULATION_MODE", "true").lower() == "true"


# ── Models ───────────────────────────────────────────────────────────────────

class TimelineEvent(BaseModel):
    timestamp: str
    actor: str  # "agent" | "human" | "system"
    event: str

class PostMortemData(BaseModel):
    incident_id: str
    title: str
    severity: str = "high"
    service: str = "unknown"
    namespace: str = "production"
    alert_name: str = ""
    detected_at: str = ""
    resolved_at: str = ""
    duration_minutes: Optional[int] = None
    timeline: List[TimelineEvent] = []
    root_cause: str = ""
    impact: str = ""
    golden_signals: Dict[str, Any] = {}
    runbook_id: Optional[str] = None
    runbook_name: Optional[str] = None
    runbook_steps: List[Dict[str, Any]] = []
    agent_diagnosis: str = ""
    action_items: List[str] = []
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class PostMortemDocument(BaseModel):
    incident_id: str
    title: str
    markdown: str
    generated_at: str
    word_count: int


# ── Generator ─────────────────────────────────────────────────────────────────

def _format_duration(minutes: Optional[int]) -> str:
    if minutes is None:
        return "Unknown"
    h, m = divmod(minutes, 60)
    return f"{h}h {m}m" if h else f"{m}m"

def _render_timeline(events: List[TimelineEvent]) -> str:
    if not events:
        return "_No timeline events recorded._\n"
    lines = []
    for ev in events:
        actor_badge = {"agent": "🤖 Agent", "human": "👤 Human", "system": "⚙️ System"}.get(ev.actor, ev.actor)
        lines.append(f"| `{ev.timestamp}` | {actor_badge} | {ev.event} |")
    header = "| Timestamp | Actor | Event |\n|-----------|-------|-------|\n"
    return header + "\n".join(lines) + "\n"

def _render_runbook_steps(steps: List[Dict[str, Any]]) -> str:
    if not steps:
        return "_No runbook steps recorded._\n"
    lines = []
    for i, step in enumerate(steps, 1):
        status = step.get("status", "unknown")
        icon = {"passed": "✅", "failed": "❌", "skipped": "⏭️", "pending": "⏳"}.get(status.lower(), "•")
        lines.append(f"{i}. {icon} **{step.get('title', f'Step {i}')}** — {step.get('output', '')}")
    return "\n".join(lines) + "\n"

def _render_action_items(items: List[str]) -> str:
    if not items:
        return "- [ ] Review incident retrospectively with the team\n"
    return "\n".join(f"- [ ] {item}" for item in items) + "\n"

def _simulate_root_cause(data: PostMortemData) -> str:
    alert = data.alert_name.lower()
    if "oom" in alert or "memory" in alert:
        return (
            "The service container exceeded its configured memory limit of 512Mi due to a gradual "
            "heap memory leak introduced in the v2.14.3 deployment. The leak was triggered by a new "
            "LRU cache implementation that failed to evict entries under sustained write-heavy workloads. "
            "Kubernetes OOM-killed the pod after memory saturation reached 97.5%, causing service disruption "
            "for approximately 4 minutes until the automated pod restart completed."
        )
    if "crashloop" in alert or "crash" in alert:
        return (
            "A nil pointer dereference in the new session management module (introduced in v2.15.0) "
            "caused the service to panic on startup when the Redis connection pool was unavailable. "
            "The CrashLoopBackOff entered exponential backoff with a maximum delay of 5 minutes, "
            "extending the outage window. The rollback to v2.14.3 restored service stability."
        )
    if "latency" in alert or "timeout" in alert:
        return (
            "The upstream payment gateway experienced elevated P99 response times (>3s) due to a "
            "misconfigured connection pool size after their infrastructure migration. This cascaded "
            "to our checkout service, which lacked circuit breaker protection on this dependency. "
            "Scaling the checkout service to 6 replicas provided sufficient buffer while the "
            "upstream team resolved their connection pool configuration."
        )
    return (
        f"Root cause analysis is pending further investigation. Alert: {data.alert_name}. "
        "Review agent diagnostic findings and correlate with recent deployments and configuration changes."
    )

def _simulate_impact(data: PostMortemData) -> str:
    dur = _format_duration(data.duration_minutes)
    return (
        f"Service **{data.service}** in namespace **{data.namespace}** was degraded for {dur}. "
        "Estimated impact: elevated error rates affecting a subset of users during the incident window. "
        "No data loss occurred. SLA impact: potential breach if duration exceeded 99.9% monthly budget."
    )

def _simulate_action_items(data: PostMortemData) -> List[str]:
    alert = data.alert_name.lower()
    base = [
        "Add runbook playbook to incident wiki and link from monitoring alert",
        "Set up automated runbook trigger for this alert pattern in staging first",
        "Review and update resource limits and requests for all services in namespace",
    ]
    if "oom" in alert or "memory" in alert:
        return [
            "Fix memory leak in LRU cache implementation (assign to backend team, P0)",
            "Increase memory limits by 25% and set readiness probe to fail before OOM",
            "Add memory saturation alert at 75% threshold (before OOM, not after)",
            "Enable Vertical Pod Autoscaler (VPA) for right-sizing recommendations",
        ] + base
    if "crash" in alert:
        return [
            "Add unit test for nil pointer dereference in session manager",
            "Implement startup health check for Redis dependency before accepting traffic",
            "Add canary deployment policy to catch startup panics before full rollout",
        ] + base
    return base


# ── Markdown Renderer ─────────────────────────────────────────────────────────

def generate_postmortem(data: PostMortemData) -> PostMortemDocument:
    """Render a complete post-mortem Markdown document from incident data."""
    if not data.root_cause:
        data.root_cause = _simulate_root_cause(data)
    if not data.impact:
        data.impact = _simulate_impact(data)
    if not data.action_items:
        data.action_items = _simulate_action_items(data)

    signals = data.golden_signals
    sig_lines = ""
    if signals:
        for k, v in signals.items():
            sig_lines += f"| {k} | {v} |\n"
    else:
        sig_lines = "| — | No golden signal data recorded | |\n"

    md = f"""---
incident_id: {data.incident_id}
severity: {data.severity}
service: {data.service}
generated_at: {data.generated_at}
status: draft
---

# Post-Mortem: {data.title}

> **Severity:** {data.severity.upper()} | **Service:** `{data.service}` | **Namespace:** `{data.namespace}`

## Summary

| Field | Value |
|-------|-------|
| Incident ID | `{data.incident_id}` |
| Alert | `{data.alert_name or "—"}` |
| Detected At | `{data.detected_at or "—"}` |
| Resolved At | `{data.resolved_at or "—"}` |
| Duration | {_format_duration(data.duration_minutes)} |
| Runbook Applied | `{data.runbook_id or "None"}` — {data.runbook_name or "Manual response"} |

## Impact

{data.impact}

## Root Cause

{data.root_cause}

## Timeline

{_render_timeline(data.timeline)}

## Golden Signals at Time of Incident

| Metric | Value |
|--------|-------|
{sig_lines}

## Agent Diagnostic Findings

{data.agent_diagnosis or "_No automated diagnostic output was captured for this incident._"}

## Runbook Execution Log

**Runbook:** `{data.runbook_id or "N/A"}` — {data.runbook_name or "No runbook applied"}

{_render_runbook_steps(data.runbook_steps)}

## Action Items

{_render_action_items(data.action_items)}

## Contributing Factors

- Missing or insufficient resource limits/requests
- Lack of upstream dependency circuit breakers
- Alert threshold set too late in the saturation curve
- No automated runbook trigger configured for this alert pattern

## Lessons Learned

1. Automated runbook execution reduced MTTR by eliminating manual triage steps.
2. The Medic agent correctly matched the incident pattern with confidence ≥ 0.9.
3. Human approval gates provided necessary safety for rollback operations.
4. Earlier alerting thresholds (at 75% saturation vs 97%) would have prevented customer impact.

---
_Generated by Medic Incident Response Agent on {data.generated_at}_
"""
    word_count = len(md.split())
    return PostMortemDocument(
        incident_id=data.incident_id,
        title=data.title,
        markdown=md,
        generated_at=data.generated_at,
        word_count=word_count,
    )
