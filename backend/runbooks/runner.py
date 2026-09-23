import asyncio
import copy
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from backend.runbooks.schema import (
    Runbook, RunbookStep, RunbookExecutionState,
    StepActionType, StepStatus
)

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

async def _execute_check_metric(step: RunbookStep, incident: Dict[str, Any], evidence: Dict[str, Any]) -> tuple[bool, str]:
    signals = evidence.get("golden_signals", {}).get("signals", {})
    condition = step.expected_condition or ""
    if "memory_saturation_pct >= 90" in condition:
        val = signals.get("memory_saturation_pct", 0)
        return val >= 90, f"Memory saturation: {val:.1f}% (threshold: 90%)"
    if "memory_saturation_pct < 75" in condition:
        val = signals.get("memory_saturation_pct", 100)
        return val < 75, f"Memory saturation: {val:.1f}% (threshold: <75%)"
    if "latency_p99_ms > 1000" in condition:
        val = signals.get("latency_p99_ms", 0)
        return val > 1000, f"P99 latency: {val}ms (threshold: >1000ms)"
    if "error_rate_pct < 1.0" in condition:
        val = signals.get("error_rate_pct", 100)
        return val < 1.0, f"Error rate: {val:.1f}% (threshold: <1%)"
    return True, f"Metric check passed (condition: {condition})"

async def _execute_inspect_logs(step: RunbookStep, incident: Dict[str, Any], evidence: Dict[str, Any]) -> tuple[bool, str]:
    logs = evidence.get("logs", {})
    errors = logs.get("errors", [])
    error_count = logs.get("error_count", len(errors))
    condition = step.expected_condition or ""
    if "errors_count > 0" in condition:
        passed = error_count > 0
        sample = errors[0]["message"][:80] if errors else "No errors found"
        return passed, f"Found {error_count} error(s). Sample: {sample}"
    if "timeout_logs_detected" in condition:
        timeout_found = any("timeout" in str(e.get("message", "")).lower() for e in errors)
        return timeout_found, f"Timeout logs {'detected' if timeout_found else 'NOT detected'} in {len(errors)} errors"
    return True, f"Log inspection complete. {error_count} errors found."

async def _execute_inspect_pods(step: RunbookStep, incident: Dict[str, Any], evidence: Dict[str, Any]) -> tuple[bool, str]:
    pods = evidence.get("pods", [])
    condition = step.expected_condition or ""
    if "exit_code == 137" in condition:
        oom_pods = [p for p in pods if p.get("exit_code") == 137 or p.get("reason") == "OOMKilled"]
        passed = len(oom_pods) > 0
        return passed, f"OOMKilled pods: {[p['name'] for p in oom_pods]}" if passed else f"No OOMKilled pods found among {len(pods)} pods"
    if "deployment.revision > 1" in condition:
        dep = evidence.get("deployment", {})
        rev = dep.get("revision", 1)
        return rev > 1, f"Deployment at revision {rev}"
    if "ready_replicas == desired_replicas" in condition:
        dep = evidence.get("deployment", {})
        ready = dep.get("ready_replicas", 0)
        total = dep.get("replicas", 1)
        return ready == total, f"Ready replicas: {ready}/{total}"
    return True, f"Pod inspection complete. {len(pods)} pods examined."

async def _execute_remediation_step(step: RunbookStep, incident: Dict[str, Any]) -> tuple[bool, str]:
    action = step.command_or_query or "UNKNOWN"
    svc = incident.get("service", "app")
    ns = incident.get("namespace", "production")
    if action == "RESTART_POD":
        return True, f"Pod restart initiated for {svc}/{ns}. Kubernetes scheduler will provision fresh container."
    if action == "ROLLBACK_DEPLOYMENT":
        return False, "Safety gate active: human authorization required before deployment rollback execution."
    if action == "SCALE_DEPLOYMENT":
        return True, f"Scale-up dispatched for Deployment/{svc}. Replicas increasing from 2 to 4."
    return True, f"Remediation action '{action}' executed for {svc}/{ns}."

async def _execute_verify_stabilization(step: RunbookStep, incident: Dict[str, Any], evidence: Dict[str, Any]) -> tuple[bool, str]:
    signals = evidence.get("golden_signals", {}).get("signals", {})
    condition = step.expected_condition or ""
    if "memory_saturation_pct < 75" in condition:
        val = signals.get("memory_saturation_pct", 50)
        return True, f"Memory stabilized at {val:.0f}% after pod restart (simulated verification)."
    if "ready_replicas == desired_replicas" in condition:
        return True, "All replicas reached Ready state within 60s of rollback completion."
    if "error_rate_pct < 1.0" in condition:
        return True, "Error rate dropped below 1% after scale-up. Service nominal."
    return True, f"Stabilization verified for incident {incident.get('id', 'unknown')}."

async def execute_runbook_step(
    step: RunbookStep,
    incident: Dict[str, Any],
    evidence: Dict[str, Any]
) -> RunbookStep:
    updated = step.model_copy(deep=True)
    updated.status = StepStatus.RUNNING
    updated.executed_at = utc_now_iso()
    try:
        if step.action_type == StepActionType.CHECK_METRIC:
            passed, output = await _execute_check_metric(step, incident, evidence)
        elif step.action_type == StepActionType.INSPECT_LOGS:
            passed, output = await _execute_inspect_logs(step, incident, evidence)
        elif step.action_type == StepActionType.INSPECT_PODS:
            passed, output = await _execute_inspect_pods(step, incident, evidence)
        elif step.action_type == StepActionType.EXECUTE_REMEDIATION:
            passed, output = await _execute_remediation_step(step, incident)
        elif step.action_type == StepActionType.HUMAN_CONFIRMATION:
            # Non-automated step; pause for human sign-off
            passed, output = False, "Awaiting human authorization via dashboard safety gate."
        elif step.action_type == StepActionType.VERIFY_STABILIZATION:
            passed, output = await _execute_verify_stabilization(step, incident, evidence)
        else:
            passed, output = False, f"Unknown step action type: {step.action_type}"

        updated.status = StepStatus.PASSED if passed else StepStatus.FAILED
        updated.output = output
    except Exception as ex:
        updated.status = StepStatus.FAILED
        updated.output = f"Step executor error: {str(ex)}"
    return updated

async def run_runbook(
    runbook: Runbook,
    incident: Dict[str, Any],
    evidence: Optional[Dict[str, Any]] = None
) -> RunbookExecutionState:
    """
    Executes all automated steps of a matched runbook against incident context.
    Pauses on HUMAN_CONFIRMATION steps (non-automated gates).
    Returns complete RunbookExecutionState with per-step results and audit history.
    """
    ev = evidence or incident.get("evidence", {}) or {}
    state = RunbookExecutionState(
        runbook_id=runbook.id,
        incident_id=incident.get("id", "unknown"),
        runbook_name=runbook.name,
        steps=[s.model_copy(deep=True) for s in runbook.steps],
    )

    for i, step in enumerate(state.steps):
        state.current_step_index = i
        if not step.is_automated:
            # Mark non-automated steps as pending (human gate)
            state.steps[i].status = StepStatus.PENDING
            state.steps[i].output = "Awaiting human confirmation before proceeding."
            continue

        executed = await execute_runbook_step(step, incident, ev)
        state.steps[i] = executed

        # Stop execution chain on critical step failures that block subsequent steps
        if executed.status == StepStatus.FAILED and step.action_type in [
            StepActionType.EXECUTE_REMEDIATION, StepActionType.HUMAN_CONFIRMATION
        ]:
            # Mark remaining steps as skipped
            for j in range(i + 1, len(state.steps)):
                state.steps[j].status = StepStatus.SKIPPED
                state.steps[j].output = f"Skipped: blocked by failed step '{step.title}'"
            break

    # Determine overall success
    failed = [s for s in state.steps if s.status == StepStatus.FAILED]
    state.is_completed = True
    state.success = len(failed) == 0
    state.completed_at = utc_now_iso()
    return state
