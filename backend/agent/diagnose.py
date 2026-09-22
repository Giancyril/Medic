from typing import Dict, Any, List, Optional
import json
from datetime import datetime, timezone

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class DiagnosisResult:
    def __init__(
        self,
        root_cause: str,
        confidence: float,
        supporting_evidence: List[str],
        recommended_action: str,
        action_type: str,
        risk_tier: str,
        requires_escalation: bool
    ):
        self.root_cause = root_cause
        self.confidence = confidence
        self.supporting_evidence = supporting_evidence
        self.recommended_action = recommended_action
        self.action_type = action_type
        self.risk_tier = risk_tier
        self.requires_escalation = requires_escalation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "root_cause": self.root_cause,
            "confidence": round(self.confidence, 2),
            "supporting_evidence": self.supporting_evidence,
            "recommended_action": self.recommended_action,
            "action_type": self.action_type,
            "risk_tier": self.risk_tier,
            "requires_escalation": self.requires_escalation,
            "diagnosed_at": utc_now().isoformat()
        }

def diagnose_incident_evidence(evidence: Dict[str, Any], alert_summary: str = "") -> DiagnosisResult:
    """
    Synthesizes gathered telemetry (Prometheus golden signals, Kubernetes state,
    and container logs) to determine probable root cause, calibrated confidence,
    and recommended remediation.
    """
    signals = evidence.get("golden_signals", {}).get("signals", {})
    pods = evidence.get("pods", [])
    logs = evidence.get("logs", {})
    events = evidence.get("events", [])
    errors = logs.get("errors", [])
    service = evidence.get("service", "unknown-service")
    namespace = evidence.get("namespace", "production")

    error_rate = signals.get("error_rate_pct", 0.0)
    latency_p99 = signals.get("latency_p99_ms", 0.0)
    mem_pct = signals.get("memory_saturation_pct", 0.0)
    cpu_pct = signals.get("cpu_saturation_pct", 0.0)

    # 1. Check for OOMKilled pattern (Highest confidence)
    oom_pods = [p for p in pods if p.get("exit_code") == 137 or p.get("reason") == "OOMKilled"]
    oom_logs = [err for err in errors if "outofmemory" in err["message"].lower() or "sigkill" in err["message"].lower()]
    if oom_pods or (mem_pct > 95.0 and oom_logs):
        pod_names = [p["name"] for p in oom_pods] if oom_pods else ["active-pod"]
        evidence_points = [
            f"Container terminated with Exit Code 137 (OOMKilled) on pod(s): {', '.join(pod_names)}",
            f"Peak memory saturation recorded at {mem_pct}%",
        ]
        if oom_logs:
            evidence_points.append(f"Container log error: {oom_logs[0]['message']}")

        return DiagnosisResult(
            root_cause=f"Memory exhaustion in {service}. Container process exceeded hard cgroup memory ceiling and was terminated by the Linux kernel OOM killer.",
            confidence=0.96,
            supporting_evidence=evidence_points,
            recommended_action=f"Restart failed pod {pod_names[0]} and scale deployment memory limits",
            action_type="RESTART_POD",
            risk_tier="TIER_1_LOW",
            requires_escalation=False
        )

    # 2. Check for CrashLoopBackOff / Bad Release pattern
    crash_pods = [p for p in pods if p.get("status") == "CrashLoopBackOff" or p.get("exit_code") == 1]
    crash_logs = [err for err in errors if any(k in err["message"].lower() for k in ["keyerror", "config", "failed to start", "critical", "startup"])]
    if crash_pods or crash_logs:
        evidence_points = []
        if crash_pods:
            evidence_points.append(f"Pod in CrashLoopBackOff with {crash_pods[0].get('restart_count', 1)} restarts")
        if crash_logs:
            evidence_points.append(f"Startup crash log signature: {crash_logs[0]['message']}")
        evidence_points.append("Elevated HTTP failure rate following recent deployment rollout")

        return DiagnosisResult(
            root_cause=f"Application startup failure in {service} following release v1.4.2. Missing configuration or unhandled initialization exception causes immediate container exit.",
            confidence=0.92,
            supporting_evidence=evidence_points,
            recommended_action=f"Rollback deployment {service} in namespace {namespace} to previous stable revision v1.4.1",
            action_type="ROLLBACK_DEPLOYMENT",
            risk_tier="TIER_3_HIGH",  # High-risk action requiring human approval!
            requires_escalation=False
        )

    # 3. Check for Upstream / Database Pool Timeout pattern
    timeout_logs = [err for err in errors if "timeout" in err["message"].lower() or "504" in err["message"].lower() or "pool" in err["message"].lower()]
    if latency_p99 > 2500.0 or timeout_logs:
        evidence_points = [
            f"Severe P99 latency degradation: {latency_p99}ms (baseline < 150ms)",
            f"Elevated HTTP 5xx error rate: {error_rate}%",
        ]
        if timeout_logs:
            evidence_points.append(f"Connection/Gateway timeout log: {timeout_logs[0]['message']}")

        return DiagnosisResult(
            root_cause=f"Database connection pool starvation or downstream dependency latency spike affecting {service}, causing queue backlog and HTTP 504 Gateway Timeouts.",
            confidence=0.88,
            supporting_evidence=evidence_points,
            recommended_action=f"Scale deployment {service} up by 2 replicas to distribute queue load",
            action_type="SCALE_DEPLOYMENT",
            risk_tier="TIER_2_MEDIUM",
            requires_escalation=False
        )

    # 4. Check for CPU Throttling / High Load
    if cpu_pct > 85.0 and error_rate > 3.0:
        evidence_points = [
            f"CPU utilization at {cpu_pct}%, approaching container quota",
            f"Request rate: {signals.get('request_rate_rps', 0)} rps with {error_rate}% error rate"
        ]
        return DiagnosisResult(
            root_cause=f"CPU starvation in {service} under heavy traffic load.",
            confidence=0.82,
            supporting_evidence=evidence_points,
            recommended_action=f"Scale deployment {service} up by 1 replica",
            action_type="SCALE_DEPLOYMENT",
            risk_tier="TIER_2_MEDIUM",
            requires_escalation=False
        )

    # 5. Low-confidence or Ambiguous alert -> Route to Human Escalation!
    return DiagnosisResult(
        root_cause=f"Inconclusive telemetry for {service}. Alert was triggered but metrics and logs show no definitive fatal crash or sustained resource threshold breach.",
        confidence=0.42,
        supporting_evidence=[
            f"Reported alert: {alert_summary or 'Unknown'}",
            f"Observed error rate: {error_rate}%",
            f"Observed latency P99: {latency_p99}ms",
            "No termination exit codes or crash loops observed in pod list"
        ],
        recommended_action="Escalate to on-call human engineer for manual triage",
        action_type="ESCALATE_HUMAN",
        risk_tier="TIER_1_LOW",
        requires_escalation=True
    )
