"""
Runbook Automation Engine API
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
import uuid
import logging

from backend.runbooks.matcher import load_runbook_catalog, match_runbook, load_runbook_by_id
from backend.runbooks.runner import run_runbook
from backend.runbooks.schema import RunbookExecutionState, StepStatus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/runbooks", tags=["runbooks"])

_executions: Dict[str, RunbookExecutionState] = {}


class RunbookMatchRequest(BaseModel):
    incident: Dict[str, Any]
    evidence: Optional[Dict[str, Any]] = None

class RunbookMatchResult(BaseModel):
    runbook_id: str
    runbook_name: str
    runbook_description: str
    confidence_score: float
    severity: str
    estimated_duration_minutes: int
    step_count: int
    automated_step_count: int
    tags: List[str]

class RunbookTriggerRequest(BaseModel):
    runbook_id: str
    incident: Dict[str, Any]
    evidence: Optional[Dict[str, Any]] = None

class StepApprovalRequest(BaseModel):
    execution_id: str
    step_index: int
    approved: bool
    approver: str = "operator"
    reason: Optional[str] = None


@router.get("/catalog", summary="List all runbooks")
async def list_catalog():
    catalog = load_runbook_catalog()
    return {
        "count": len(catalog),
        "runbooks": [
            {
                "id": rb.id, "name": rb.name, "description": rb.description,
                "severity": rb.severity, "tags": rb.tags,
                "step_count": len(rb.steps),
                "automated_step_count": sum(1 for s in rb.steps if s.is_automated),
                "estimated_duration_minutes": rb.estimated_duration_minutes,
            } for rb in catalog
        ]
    }

@router.get("/catalog/{runbook_id}", summary="Get runbook detail")
async def get_runbook(runbook_id: str):
    rb = load_runbook_by_id(runbook_id)
    if not rb:
        raise HTTPException(404, f"Runbook {runbook_id!r} not found.")
    return rb.model_dump()

@router.post("/match", summary="Match incident to best runbook")
async def match_incident(req: RunbookMatchRequest) -> RunbookMatchResult:
    result = match_runbook(req.incident, req.evidence or {})
    if not result:
        raise HTTPException(404, "No suitable runbook found.")
    rb, score = result
    return RunbookMatchResult(
        runbook_id=rb.id, runbook_name=rb.name,
        runbook_description=rb.description,
        confidence_score=round(score, 3), severity=rb.severity,
        estimated_duration_minutes=rb.estimated_duration_minutes,
        step_count=len(rb.steps),
        automated_step_count=sum(1 for s in rb.steps if s.is_automated),
        tags=rb.tags,
    )

@router.post("/trigger", summary="Trigger runbook execution")
async def trigger_runbook(req: RunbookTriggerRequest, background_tasks: BackgroundTasks):
    rb = load_runbook_by_id(req.runbook_id)
    if not rb:
        raise HTTPException(404, f"Runbook {req.runbook_id!r} not found.")
    execution_id = f"exec-{uuid.uuid4().hex[:12]}"
    _executions[execution_id] = RunbookExecutionState(
        runbook_id=rb.id, incident_id=req.incident.get("id", "unknown"),
        runbook_name=rb.name, steps=[s.model_copy(deep=True) for s in rb.steps],
    )
    async def _run():
        state = await run_runbook(rb, req.incident, req.evidence)
        state.runbook_id = rb.id
        _executions[execution_id] = state
    background_tasks.add_task(_run)
    return {
        "execution_id": execution_id, "runbook_id": rb.id,
        "runbook_name": rb.name, "incident_id": req.incident.get("id"),
        "status": "running",
        "message": f"Execution started. Poll /runbooks/status/{execution_id}",
    }

@router.get("/status/{execution_id}", summary="Poll execution status")
async def get_status(execution_id: str):
    state = _executions.get(execution_id)
    if not state:
        raise HTTPException(404, f"Execution {execution_id!r} not found.")
    return state.model_dump()

@router.post("/approve", summary="Approve/reject a human gate step")
async def approve_step(req: StepApprovalRequest):
    state = _executions.get(req.execution_id)
    if not state:
        raise HTTPException(404, f"Execution {req.execution_id!r} not found.")
    idx = req.step_index
    if idx < 0 or idx >= len(state.steps):
        raise HTTPException(400, f"Step index {idx} out of range.")
    step = state.steps[idx]
    if step.status not in [StepStatus.PENDING, StepStatus.RUNNING]:
        raise HTTPException(409, f"Step {idx} status {step.status!r} cannot be approved.")
    if req.approved:
        step.status = StepStatus.PASSED
        step.output = f"Approved by {req.approver}. {req.reason or ''}"
    else:
        step.status = StepStatus.FAILED
        step.output = f"Rejected by {req.approver}. {req.reason or ''}"
        for j in range(idx + 1, len(state.steps)):
            state.steps[j].status = StepStatus.SKIPPED
            state.steps[j].output = "Skipped: human gate rejected."
    state.steps[idx] = step
    return {"execution_id": req.execution_id, "step_index": idx, "new_status": step.status}

@router.get("/executions", summary="List all executions")
async def list_executions():
    return {
        "count": len(_executions),
        "executions": [
            {
                "execution_id": eid, "runbook_name": st.runbook_name,
                "incident_id": st.incident_id, "is_completed": st.is_completed,
                "success": st.success, "completed_at": st.completed_at,
            } for eid, st in _executions.items()
        ]
    }
