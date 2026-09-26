"""
FinOps & Incident Financial Impact REST API.
"""
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.finops import finops_engine

router = APIRouter(prefix="/finops", tags=["finops"])

class CalculateImpactRequest(BaseModel):
    service: str
    duration_minutes: float
    error_rate_pct: float
    incident_id: Optional[str] = ""

class AddRemediationCostRequest(BaseModel):
    incident_id: str
    action_type: str
    resources: str
    hourly_usd: float

@router.get("/summaries", summary="List all active incident financial impact summaries")
async def list_summaries():
    return {"summaries": [s.model_dump() for s in finops_engine.list_summaries()]}

@router.get("/impact/{incident_id}", summary="Get business impact and FinOps report for incident")
async def get_incident_impact(incident_id: str):
    summary = finops_engine.get_summary(incident_id)
    if not summary:
        # Fallback to computing on demand for checkout-api default
        summary = finops_engine.calculate_impact(
            service="checkout-api",
            duration_minutes=5.0,
            error_rate_pct=8.0,
            incident_id=incident_id,
        )
    return summary.model_dump()

@router.post("/calculate", summary="Calculate business impact based on telemetry parameters")
async def calculate_impact(req: CalculateImpactRequest):
    summary = finops_engine.calculate_impact(
        service=req.service,
        duration_minutes=req.duration_minutes,
        error_rate_pct=req.error_rate_pct,
        incident_id=req.incident_id or "",
    )
    return summary.model_dump()

@router.post("/remediation-cost", summary="Log remediation infrastructure cost delta")
async def add_remediation_cost(req: AddRemediationCostRequest):
    delta = finops_engine.add_remediation_cost(
        incident_id=req.incident_id,
        action_type=req.action_type,
        resources=req.resources,
        hourly_usd=req.hourly_usd,
    )
    return delta.model_dump()
