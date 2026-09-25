"""
On-Call Schedule & Escalation REST API.
Exposes endpoints for querying current shifts, dispatching pages, and managing escalation states.
"""
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.oncall import oncall_engine

router = APIRouter(prefix="/oncall", tags=["oncall"])

class PageDispatchRequest(BaseModel):
    incident_id: str
    tier: int = 1
    notes: Optional[str] = ""

class PageEscalateRequest(BaseModel):
    reason: Optional[str] = "Manual escalation from dashboard"

@router.get("/status", summary="Retrieve active on-call shift, pages, and MTTA metrics")
async def get_oncall_status():
    return oncall_engine.get_status().model_dump()

@router.post("/page", summary="Dispatch page to on-call responder")
async def dispatch_page(req: PageDispatchRequest):
    event = oncall_engine.dispatch_page(
        incident_id=req.incident_id,
        tier=req.tier,
        notes=req.notes or "",
    )
    return event.model_dump()

@router.post("/page/{page_id}/ack", summary="Acknowledge active page")
async def acknowledge_page(page_id: str):
    event = oncall_engine.acknowledge_page(page_id)
    if not event:
        raise HTTPException(status_code=404, detail=f"Page '{page_id}' not found")
    return event.model_dump()

@router.post("/page/{page_id}/escalate", summary="Escalate page to next tier responder")
async def escalate_page(page_id: str, req: PageEscalateRequest):
    new_event = oncall_engine.escalate_page(page_id, reason=req.reason or "Escalated")
    if not new_event:
        raise HTTPException(status_code=404, detail=f"Page '{page_id}' not found")
    return new_event.model_dump()
