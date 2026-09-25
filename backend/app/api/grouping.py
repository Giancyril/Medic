"""
Alert Deduplication & Incident Grouping REST API.
Exposes endpoints for querying grouped incident clusters, alert fingerprints, and noise reduction statistics.
"""
from typing import Dict, Any
from fastapi import APIRouter
from pydantic import BaseModel
from backend.grouping import grouping_engine

router = APIRouter(prefix="/grouping", tags=["grouping"])

class AlertIngestRequest(BaseModel):
    alert_id: str
    alert_name: str
    service: str
    severity: str = "critical"

@router.get("/clusters", summary="Retrieve all active grouped incident clusters")
async def get_incident_clusters():
    clusters = grouping_engine.get_clusters()
    return {"clusters": [c.model_dump() for c in clusters]}

@router.get("/stats", summary="Retrieve alert noise reduction and deduplication metrics")
async def get_grouping_stats():
    return grouping_engine.get_noise_reduction_stats().model_dump()

@router.post("/ingest", summary="Ingest raw alert for deduplication and grouping")
async def ingest_alert(req: AlertIngestRequest):
    cluster = grouping_engine.ingest_alert(
        alert_id=req.alert_id,
        alert_name=req.alert_name,
        service=req.service,
        severity=req.severity,
    )
    return cluster.model_dump()
