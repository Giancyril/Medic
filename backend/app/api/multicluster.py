"""
Multi-Cluster Global Failover & Traffic Routing REST API.
"""
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from backend.multicluster import multicluster_engine

router = APIRouter(prefix="/multicluster", tags=["multicluster"])

class DrainRequest(BaseModel):
    reason: Optional[str] = "Operator initiated traffic evacuation"

class RestoreRequest(BaseModel):
    target_weight_pct: Optional[int] = 35

class ShiftTrafficRequest(BaseModel):
    source_id: str
    target_id: str
    shift_pct: int = Field(..., ge=1, le=100)

@router.get("/overview", summary="Get multi-cluster global topology, health matrix, and traffic weights")
async def get_multicluster_overview():
    return multicluster_engine.get_overview().model_dump()

@router.get("/clusters", summary="List all regional clusters")
async def list_clusters():
    return {"clusters": [c.model_dump() for c in multicluster_engine.list_clusters()]}

@router.post("/clusters/{cluster_id}/drain", summary="Drain all traffic from a cluster (zero-downtime evacuation)")
async def drain_cluster(cluster_id: str, req: DrainRequest = DrainRequest()):
    try:
        cluster = multicluster_engine.drain_cluster(cluster_id, reason=req.reason or "Traffic drain")
        return {"status": "drained", "cluster": cluster.model_dump(), "overview": multicluster_engine.get_overview().model_dump()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/clusters/{cluster_id}/restore", summary="Restore traffic to a previously drained cluster")
async def restore_cluster(cluster_id: str, req: RestoreRequest = RestoreRequest()):
    try:
        cluster = multicluster_engine.restore_cluster(cluster_id, target_weight_pct=req.target_weight_pct or 35)
        return {"status": "restored", "cluster": cluster.model_dump(), "overview": multicluster_engine.get_overview().model_dump()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/shift", summary="Shift discrete traffic weight between regions")
async def shift_traffic(req: ShiftTrafficRequest):
    try:
        overview = multicluster_engine.shift_traffic(req.source_id, req.target_id, req.shift_pct)
        return overview.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
