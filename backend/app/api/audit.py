"""
Audit Trail & Incident Replay REST API.
"""
from fastapi import APIRouter
from backend.audit import audit_replay_engine

router = APIRouter(prefix="/audit", tags=["audit"])

@router.get("/ledger", summary="Get cryptographically hashed immutable audit ledger")
async def get_audit_ledger():
    valid = audit_replay_engine.verify_audit_integrity()
    return {
        "integrity_verified": valid,
        "count": len(audit_replay_engine.ledger),
        "ledger": [e.model_dump() for e in audit_replay_engine.ledger],
    }

@router.get("/compliance/{incident_id}", summary="Get SOC-2 / SOX compliance report for incident")
async def get_compliance_report(incident_id: str):
    report = audit_replay_engine.generate_compliance_report(incident_id)
    return report.model_dump()

@router.get("/replay/{incident_id}", summary="Get sequential time-travel incident replay frames")
async def get_incident_replay(incident_id: str):
    frames = audit_replay_engine.get_replay_timeline(incident_id)
    return {
        "incident_id": incident_id,
        "frames_count": len(frames),
        "frames": [f.model_dump() for f in frames],
    }
