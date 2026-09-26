"""
Canary Deployment & Automated Analysis REST API.
"""
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.canary import canary_orchestrator

router = APIRouter(prefix="/canary", tags=["canary"])

class RollbackRequest(BaseModel):
    reason: Optional[str] = "Manual rollback from console"

@router.get("/deployments", summary="List all active and recent canary deployments")
async def list_canary_deployments():
    deps = canary_orchestrator.list_deployments()
    return {"deployments": [d.model_dump() for d in deps.values()]}

@router.get("/deployments/{deployment_id}", summary="Get canary deployment details and report")
async def get_canary_deployment(deployment_id: str):
    dep = canary_orchestrator.get_deployment(deployment_id)
    if not dep:
        raise HTTPException(status_code=404, detail=f"Canary deployment '{deployment_id}' not found")
    return dep.model_dump()

@router.post("/deployments/{deployment_id}/evaluate", summary="Run on-demand canary analysis")
async def evaluate_canary(deployment_id: str):
    try:
        report = canary_orchestrator.evaluate_deployment(deployment_id)
        dep = canary_orchestrator.get_deployment(deployment_id)
        return {"deployment": dep.model_dump(), "report": report.model_dump()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/deployments/{deployment_id}/advance", summary="Advance canary traffic split weight")
async def advance_canary_traffic(deployment_id: str):
    try:
        dep, report = canary_orchestrator.advance_traffic(deployment_id)
        return {"deployment": dep.model_dump(), "report": report.model_dump()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/deployments/{deployment_id}/promote", summary="Promote canary directly to 100% traffic")
async def promote_canary(deployment_id: str):
    try:
        dep = canary_orchestrator.promote_canary(deployment_id)
        return dep.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/deployments/{deployment_id}/rollback", summary="Trigger automated or manual canary rollback")
async def rollback_canary(deployment_id: str, req: RollbackRequest):
    try:
        dep = canary_orchestrator.rollback_canary(deployment_id, reason=req.reason or "Rollback requested")
        return dep.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
