"""
Resilience & Chaos Engineering REST API.
"""
from fastapi import APIRouter, HTTPException
from backend.resilience import resilience_engine

router = APIRouter(prefix="/resilience", tags=["resilience"])

@router.get("/scorecard", summary="Get cluster resilience scorecard and reliability index")
async def get_resilience_scorecard():
    return resilience_engine.get_scorecard().model_dump()

@router.get("/experiments", summary="List all chaos experiments")
async def list_experiments():
    return {"experiments": [e.model_dump() for e in resilience_engine.list_experiments()]}

@router.post("/experiments/{experiment_id}/launch", summary="Launch chaos fault injection experiment")
async def launch_experiment(experiment_id: str):
    try:
        exp = resilience_engine.launch_experiment(experiment_id)
        return exp.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/experiments/{experiment_id}/stop", summary="Emergency abort chaos experiment")
async def stop_experiment(experiment_id: str):
    try:
        exp = resilience_engine.stop_experiment(experiment_id)
        return exp.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
