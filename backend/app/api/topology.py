"""
Topology REST API.
Exposes endpoints for querying service graph dependency topology, health states, and blast radius.
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.topology import topology_engine, NodeHealth

router = APIRouter(prefix="/topology", tags=["topology"])

class BlastRadiusRequest(BaseModel):
    service_id: str

class HealthUpdateRequest(BaseModel):
    health: NodeHealth
    incident_id: Optional[str] = None
    error_rate_pct: Optional[float] = None
    p99_latency_ms: Optional[float] = None

@router.get("/graph", summary="Retrieve full cluster service dependency topology")
async def get_topology_graph():
    return topology_engine.get_graph().model_dump()

@router.post("/blast-radius", summary="Compute blast radius impact for a given service")
async def compute_blast_radius(req: BlastRadiusRequest):
    report = topology_engine.calculate_blast_radius(req.service_id)
    return report.model_dump()

@router.post("/nodes/{service_id}/health", summary="Update service health state")
async def update_service_health(service_id: str, req: HealthUpdateRequest):
    topology_engine.set_service_health(
        service_id=service_id,
        health=req.health,
        incident_id=req.incident_id,
        error_rate_pct=req.error_rate_pct,
        p99_latency_ms=req.p99_latency_ms,
    )
    return {"status": "ok", "service_id": service_id, "new_health": req.health.value}
