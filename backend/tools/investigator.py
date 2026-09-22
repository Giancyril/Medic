import asyncio
from typing import Dict, Any, List
from datetime import datetime, timezone
from backend.tools.prometheus import get_golden_signals
from backend.tools.kubernetes import inspect_pods, inspect_events, inspect_deployment
from backend.tools.log_tailer import tail_pod_logs

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

async def collect_evidence(service: str, namespace: str = "production") -> Dict[str, Any]:
    """
    Gathers comprehensive infrastructure and application evidence concurrently:
    - Prometheus Golden Signals
    - Kubernetes Pod states & restarts
    - Recent cluster warning events
    - Deployment rollout status
    - Container logs & error signatures
    """
    signals_task = get_golden_signals(service, namespace)
    pods_task = inspect_pods(service, namespace)
    events_task = inspect_events(service, namespace)
    deploy_task = inspect_deployment(service, namespace)
    logs_task = tail_pod_logs(service, namespace)

    signals, pods, events, deployment, logs = await asyncio.gather(
        signals_task, pods_task, events_task, deploy_task, logs_task
    )

    # Anomaly synthesis
    oom_killed = any(p.get("exit_code") == 137 or p.get("reason") == "OOMKilled" for p in pods)
    crash_loop = any(p.get("status") == "CrashLoopBackOff" or p.get("restart_count", 0) > 3 for p in pods)
    high_error = signals["signals"]["error_rate_pct"] > 5.0
    high_latency = signals["signals"]["latency_p99_ms"] > 1000.0
    mem_saturated = signals["signals"]["memory_saturation_pct"] > 90.0
    cpu_saturated = signals["signals"]["cpu_saturation_pct"] > 85.0

    anomalies = []
    if oom_killed:
        anomalies.append("Pod terminated with OOMKilled (Exit Code 137)")
    if crash_loop:
        anomalies.append("Pod in CrashLoopBackOff with elevated restart count")
    if high_error:
        anomalies.append(f"Elevated HTTP 5xx error rate: {signals['signals']['error_rate_pct']}%")
    if high_latency:
        anomalies.append(f"P99 latency spike: {signals['signals']['latency_p99_ms']}ms")
    if mem_saturated:
        anomalies.append(f"Critical memory saturation: {signals['signals']['memory_saturation_pct']}%")
    if cpu_saturated:
        anomalies.append(f"Critical CPU throttling: {signals['signals']['cpu_saturation_pct']}%")

    return {
        "service": service,
        "namespace": namespace,
        "collected_at": utc_now().isoformat(),
        "golden_signals": signals,
        "pods": pods,
        "events": events,
        "deployment": deployment,
        "logs": logs,
        "anomalies": anomalies,
        "health_score": max(0, 100 - len(anomalies) * 25)
    }
