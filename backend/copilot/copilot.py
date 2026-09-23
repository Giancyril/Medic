"""SRE Copilot - Agentic LLM chat for incident-aware Q&A and remediation guidance."""
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import os, json, logging

logger = logging.getLogger(__name__)
SIMULATION_MODE = os.getenv("SIMULATION_MODE", "true").lower() == "true"

class CopilotMessage(BaseModel):
    role: str
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class CopilotSession(BaseModel):
    session_id: str
    incident_id: Optional[str] = None
    messages: List[CopilotMessage] = []
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    incident_context: Optional[Dict[str, Any]] = None

class CopilotRequest(BaseModel):
    session_id: str
    message: str
    incident_context: Optional[Dict[str, Any]] = None

class CopilotResponse(BaseModel):
    session_id: str
    reply: str
    suggestions: List[str] = []
    referenced_runbook_id: Optional[str] = None
    confidence: float = 1.0

def _build_system_prompt(ctx: Optional[Dict[str, Any]] = None) -> str:
    base = ("You are Medic Copilot, an expert SRE assistant. Help on-call engineers diagnose and resolve "
            "production incidents. Speak concisely. Prefer actionable kubectl/prometheus commands. "
            "Reference runbooks by canonical ID (e.g. rb-k8s-oom-recovery). Say so if unsure.")
    if not ctx:
        return base
    parts = [base, "", "=== INCIDENT CONTEXT ==="]
    for key in ["alert_name", "service", "namespace", "severity"]:
        if ctx.get(key):
            parts.append(f"{key}: {ctx[key]}")
    if ctx.get("golden_signals"):
        parts.append(f"signals: {json.dumps(ctx['golden_signals'])}")
    parts.append("========================")
    return "\n".join(parts)

_SIM = {
    "oom": {"reply": ("OOMKilled (exit 137) — container exceeded memory limit.\n\n"
                      "**Actions:**\n1. `kubectl describe pod <pod> -n production` — confirm OOMKilled\n"
                      "2. `kubectl top pod -n production` — check consumption\n"
                      "3. Apply runbook **rb-k8s-oom-recovery** via the Runbook panel\n\n"
                      "**Root causes:** memory leak, burst traffic, missing resource limits.\n"
                      "**Fix:** increase limits +25%, set requests=70% of limits."),
            "suggestions": ["Run rb-k8s-oom-recovery", "Check memory trend in Grafana (6h)", "Review deployment resource limits"],
            "runbook": "rb-k8s-oom-recovery"},
    "crashloop": {"reply": ("CrashLoopBackOff — container crashes repeatedly.\n\n"
                             "**Triage:**\n1. `kubectl logs <pod> --previous` — last crash logs\n"
                             "2. `kubectl describe pod <pod>` — exit code + restart count\n"
                             "3. `kubectl rollout history deployment/<svc>` — detect bad deploy\n\n"
                             "Apply **rb-k8s-crashloop-rollback** for automated rollback."),
                  "suggestions": ["Run rb-k8s-crashloop-rollback", "Check last deployment diff", "Inspect startup logs"],
                  "runbook": "rb-k8s-crashloop-rollback"},
    "latency": {"reply": ("High P99 latency — upstream saturation or resource contention.\n\n"
                           "**Triage:**\n1. `curl http://upstream-svc/health` — upstream check\n"
                           "2. `kubectl top pods -n production` — CPU throttling\n"
                           "3. Distributed traces for slow spans\n\n"
                           "Apply **rb-upstream-timeout** for circuit breaker + traffic mitigation.\n"
                           "Interim scale: `kubectl scale deployment/<svc> --replicas=6`"),
                "suggestions": ["Run rb-upstream-timeout", "Check upstream health", "Scale deployment"],
                "runbook": "rb-upstream-timeout"},
    "default": {"reply": ("Analyzing incident. Key SRE principles:\n\n"
                           "1. **Stabilize first** — stop the bleeding\n"
                           "2. **4 golden signals** — latency, traffic, errors, saturation\n"
                           "3. **Recent changes** — deploys, config, upstream incidents\n"
                           "4. **Use a runbook** — safe execution with human gates\n\n"
                           "Share the alert name or error for targeted guidance."),
                "suggestions": ["Describe alert/error", "Run /api/v1/runbooks/match", "Check golden signals dashboard"],
                "runbook": None},
}

def _simulate(message: str, ctx: Optional[Dict[str, Any]], session_id: str) -> CopilotResponse:
    m = message.lower()
    a = (ctx or {}).get("alert_name", "").lower()
    k = "oom" if ("oom" in m or "memory" in m or "oom" in a) else \
        "crashloop" if ("crash" in m or "restart" in m) else \
        "latency" if ("latency" in m or "slow" in m or "timeout" in m) else "default"
    r = _SIM[k]
    return CopilotResponse(session_id=session_id, reply=r["reply"],
                           suggestions=r["suggestions"], referenced_runbook_id=r["runbook"], confidence=0.92)

async def _llm_call(session: CopilotSession, msg: str, ctx: Optional[Dict[str, Any]]) -> CopilotResponse:
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI()
        history = [{"role": "system", "content": _build_system_prompt(ctx)}]
        for m in session.messages[-10:]:
            history.append({"role": m.role, "content": m.content})
        history.append({"role": "user", "content": msg})
        resp = await client.chat.completions.create(model="gpt-4o-mini", messages=history, temperature=0.3, max_tokens=800)
        return CopilotResponse(session_id=session.session_id, reply=resp.choices[0].message.content, confidence=0.95)
    except Exception as ex:
        logger.warning("LLM fallback to sim: %s", ex)
        return _simulate(msg, ctx, session.session_id)

async def chat(session: CopilotSession, user_message: str, incident_context: Optional[Dict[str, Any]] = None) -> CopilotResponse:
    ctx = incident_context or session.incident_context
    if SIMULATION_MODE:
        return _simulate(user_message, ctx, session.session_id)
    return await _llm_call(session, user_message, ctx)
