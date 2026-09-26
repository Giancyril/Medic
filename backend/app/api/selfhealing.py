"""
Autonomous Closed-Loop Self-Healing REST API.
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.selfhealing import selfhealing_engine

router = APIRouter(prefix="/selfhealing", tags=["selfhealing"])

class TogglePolicyRequest(BaseModel):
    enabled: bool

class ExecutePolicyRequest(BaseModel):
    incident_id: str
    initial_metrics: Optional[Dict[str, float]] = None

@router.get("/policies", summary="List all autonomous self-healing policies")
async def list_policies():
    return {"policies": [p.model_dump() for p in selfhealing_engine.list_policies()]}

@router.post("/policies/{policy_id}/toggle", summary="Enable or disable a self-healing policy")
async def toggle_policy(policy_id: str, req: TogglePolicyRequest):
    try:
        policy = selfhealing_engine.toggle_policy(policy_id, req.enabled)
        return policy.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/policies/{policy_id}/execute", summary="Trigger closed-loop self-healing policy execution")
async def execute_policy(policy_id: str, req: ExecutePolicyRequest):
    try:
        execution = selfhealing_engine.execute_policy(
            policy_id=policy_id,
            incident_id=req.incident_id,
            initial_metrics=req.initial_metrics,
        )
        return execution.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/executions", summary="List closed-loop execution audit history")
async def list_executions():
    return {"executions": [e.model_dump() for e in selfhealing_engine.list_executions()]}

@router.get("/guardrails", summary="Get self-healing velocity limiters and safety guardrails")
async def get_guardrail_status():
    return selfhealing_engine.get_guardrail_status().model_dump()
