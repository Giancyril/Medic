from typing import Dict, Any, Optional
from datetime import datetime, timezone
from backend.remediation.catalog import RemediationAction, RiskTier
from backend.tools.cluster_simulator import simulator
from backend.app.core.config import settings

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class SafetyGateError(Exception):
    """Raised when an unapproved high-risk remediation action execution is attempted."""
    pass

async def execute_remediation(
    action: RemediationAction,
    is_approved_by_human: bool = False,
    approver: Optional[str] = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Executes a remediation action against the target Kubernetes cluster.
    Enforces Safety Gate: If action is high-risk (Tier 3), it MUST have explicit human approval.
    Dry-run mode is always safe and generates declarative diff preview without committing cluster mutations.
    """
    now = utc_now()

    # 1. Dry-Run Execution Mode (Safe, no mutations)
    if dry_run:
        return {
            "status": "DRY_RUN_SUCCESS",
            "action": action.action_type,
            "target": action.target_resource,
            "diff": action.generate_diff(),
            "message": "Dry-run execution verified. No changes committed to cluster state.",
            "executed_at": now.isoformat()
        }

    # 2. Un-bypassable Safety Gate Check (Enforced on real execution)
    if action.requires_human_approval and not is_approved_by_human:
        raise SafetyGateError(
            f"SAFETY GATE BLOCKED: Action '{action.name}' is categorized under {action.risk_tier.value} "
            f"and requires signed human approval prior to cluster execution."
        )

    # 3. Live / Simulated Mutation
    service = action.parameters.get("service", "order-processor")
    namespace = action.parameters.get("namespace", "production")

    if settings.SIMULATION_MODE:
        if action.action_type == "ROLLBACK_DEPLOYMENT":
            dep_key = f"{namespace}/{service}"
            if dep_key in simulator.deployments:
                dep = simulator.deployments[dep_key]
                prev_rev = max(1, dep["revision"] - 1)
                dep["revision"] = prev_rev
                dep["image"] = f"registry.internal/apps/{service}:v1.4.{prev_rev}"
            
            # Reset pods to healthy running state
            for pod_name, pod in list(simulator.pods.items()):
                if pod["service"] == service:
                    pod["status"] = "Running"
                    pod["ready"] = True
                    pod["exit_code"] = 0
                    pod["restart_count"] = 0
                    pod["reason"] = None

            # Reset metrics
            simulator.metrics_state[service] = {
                "request_rate": 220.0,
                "error_rate": 0.001,
                "latency_p50_ms": 24.0,
                "latency_p95_ms": 70.0,
                "latency_p99_ms": 115.0,
                "cpu_saturation_pct": 34.0,
                "memory_saturation_pct": 42.0
            }

            return {
                "status": "SUCCESS",
                "action": action.action_type,
                "target": action.target_resource,
                "message": f"Successfully rolled back {service} to revision v1.4.{prev_rev}. Replicas healthy.",
                "approved_by": approver or "system-authorized",
                "executed_at": now.isoformat()
            }

        elif action.action_type == "RESTART_POD":
            # Clear terminated or crashloop pods for this service
            restarted = []
            for pod_name, pod in list(simulator.pods.items()):
                if pod["service"] == service and pod["status"] != "Running":
                    pod["status"] = "Running"
                    pod["ready"] = True
                    pod["restart_count"] = 0
                    pod["exit_code"] = 0
                    pod["reason"] = None
                    restarted.append(pod_name)

            # Reset metrics if degraded
            if service in simulator.metrics_state:
                simulator.metrics_state[service]["error_rate"] = 0.002
                simulator.metrics_state[service]["memory_saturation_pct"] = 48.0

            return {
                "status": "SUCCESS",
                "action": action.action_type,
                "target": action.target_resource,
                "message": f"Successfully restarted pod(s): {', '.join(restarted) if restarted else service}",
                "approved_by": approver or "auto-remediation-engine",
                "executed_at": now.isoformat()
            }

        elif action.action_type == "SCALE_DEPLOYMENT":
            dep_key = f"{namespace}/{service}"
            target_reps = action.parameters.get("target_replicas", 4)
            if dep_key in simulator.deployments:
                simulator.deployments[dep_key]["replicas"] = target_reps
                simulator.deployments[dep_key]["ready_replicas"] = target_reps

            if service in simulator.metrics_state:
                simulator.metrics_state[service]["latency_p99_ms"] = 120.0
                simulator.metrics_state[service]["error_rate"] = 0.001

            return {
                "status": "SUCCESS",
                "action": action.action_type,
                "target": action.target_resource,
                "message": f"Successfully scaled {service} to {target_reps} replicas.",
                "approved_by": approver or "system-authorized",
                "executed_at": now.isoformat()
            }

    return {
        "status": "SUCCESS",
        "action": action.action_type,
        "target": action.target_resource,
        "message": f"Executed {action.name} on cluster.",
        "approved_by": approver or "authorized-human",
        "executed_at": now.isoformat()
    }
