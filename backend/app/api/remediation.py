from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json

from backend.app.core.database import get_db
from backend.app.models.incident import Incident, IncidentEvent, IncidentStatus
from backend.app.schemas.incident import IncidentRead
from backend.app.core.incident_manager import broadcaster, utc_now
from backend.agent.graph import incident_graph
from backend.agent.escalate import dispatcher
from backend.remediation.catalog import build_remediation_action
from backend.remediation.executor import execute_remediation, SafetyGateError

router = APIRouter(prefix="/incidents", tags=["remediation"])

class ApprovalRequest(BaseModel):
    approver: str
    comment: Optional[str] = None

class RejectionRequest(BaseModel):
    rejector: str
    reason: str

class EscalationRequest(BaseModel):
    reason: str
    channel: Optional[str] = "slack"  # "slack", "pagerduty", "all"

@router.post("/{incident_id}/investigate", response_model=IncidentRead)
async def trigger_investigation(
    incident_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Triggers the LangGraph Investigate & Diagnose cycle for an incident.
    Collects metrics, pod state, logs, generates root cause diagnosis,
    and proposes a remediation action.
    """
    stmt = select(Incident).options(selectinload(Incident.events)).where(Incident.id == incident_id)
    result = await db.execute(stmt)
    incident = result.scalars().first()
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Incident {incident_id} not found")

    # Run LangGraph pipeline
    initial_state = {
        "incident_id": incident.id,
        "service": incident.service,
        "namespace": incident.namespace,
        "alert_summary": incident.summary,
        "is_approved": False
    }

    config = {"configurable": {"thread_id": incident.id}}
    final_state = await incident_graph.ainvoke(initial_state, config=config)

    now = utc_now()
    incident.evidence_json = json.dumps(final_state.get("evidence", {}))
    incident.diagnosis_json = json.dumps(final_state.get("diagnosis", {}))
    incident.remediation_json = json.dumps(final_state.get("action", {}))
    incident.status = final_state.get("status", IncidentStatus.INVESTIGATING.value)
    incident.last_seen_at = now

    diag = final_state.get("diagnosis", {})
    action = final_state.get("action", {})

    # Record event
    event = IncidentEvent(
        incident_id=incident.id,
        event_type="DIAGNOSIS_COMPLETED",
        message=f"Root cause diagnosed (confidence {diag.get('confidence', 0)*100}%): {diag.get('root_cause', '')}",
        payload_json=json.dumps({"diagnosis": diag, "action": action}),
        created_at=now
    )
    db.add(event)
    await db.commit()
    await db.refresh(incident)

    await broadcaster.broadcast("incident_diagnosed", {
        "id": incident.id,
        "status": incident.status,
        "confidence": diag.get("confidence"),
        "root_cause": diag.get("root_cause"),
        "action": action.get("name"),
        "risk_tier": action.get("risk_tier")
    })

    return incident

@router.get("/{incident_id}/diff")
async def get_remediation_diff(
    incident_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Retrieves the declarative diff preview for the proposed remediation action."""
    stmt = select(Incident).where(Incident.id == incident_id)
    result = await db.execute(stmt)
    incident = result.scalars().first()
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Incident {incident_id} not found")

    action_data = incident.remediation
    if not action_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No remediation action currently proposed")

    action = build_remediation_action(
        action_type=action_data.get("action_type", "RESTART_POD"),
        service=incident.service,
        namespace=incident.namespace,
        extra_params=action_data.get("parameters", {})
    )

    return {
        "incident_id": incident.id,
        "action": action.name,
        "risk_tier": action.risk_tier.value,
        "target_resource": action.target_resource,
        "diff": action.generate_diff()
    }

@router.post("/{incident_id}/approve", response_model=IncidentRead)
async def approve_remediation(
    incident_id: str,
    body: ApprovalRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Human-in-the-Loop Safety Gate: Registers human approval and executes the gated action.
    """
    stmt = select(Incident).options(selectinload(Incident.events)).where(Incident.id == incident_id)
    result = await db.execute(stmt)
    incident = result.scalars().first()
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Incident {incident_id} not found")

    action_data = incident.remediation
    if not action_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No action pending approval")

    action = build_remediation_action(
        action_type=action_data.get("action_type", "RESTART_POD"),
        service=incident.service,
        namespace=incident.namespace,
        extra_params=action_data.get("parameters", {})
    )

    now = utc_now()
    try:
        exec_res = await execute_remediation(
            action=action,
            is_approved_by_human=True,
            approver=body.approver
        )
    except SafetyGateError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    incident.status = IncidentStatus.RESOLVED.value
    incident.resolved_at = now
    incident.last_seen_at = now

    event = IncidentEvent(
        incident_id=incident.id,
        event_type="ACTION_EXECUTED",
        message=f"Action '{action.name}' approved by {body.approver} and executed successfully. {body.comment or ''}".strip(),
        payload_json=json.dumps(exec_res),
        created_at=now
    )
    db.add(event)
    await db.commit()
    await db.refresh(incident)

    await broadcaster.broadcast("incident_resolved", {
        "id": incident.id,
        "status": incident.status,
        "approver": body.approver,
        "result": exec_res
    })

    return incident

@router.post("/{incident_id}/reject", response_model=IncidentRead)
async def reject_remediation(
    incident_id: str,
    body: RejectionRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Human-in-the-Loop Safety Gate: Human rejects proposed action, escalating incident.
    """
    stmt = select(Incident).options(selectinload(Incident.events)).where(Incident.id == incident_id)
    result = await db.execute(stmt)
    incident = result.scalars().first()
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Incident {incident_id} not found")

    now = utc_now()
    incident.status = IncidentStatus.ESCALATED.value
    incident.last_seen_at = now

    event = IncidentEvent(
        incident_id=incident.id,
        event_type="ACTION_REJECTED",
        message=f"Proposed remediation rejected by {body.rejector}. Reason: {body.reason}",
        payload_json=json.dumps({"rejector": body.rejector, "reason": body.reason}),
        created_at=now
    )
    db.add(event)
    await db.commit()
    await db.refresh(incident)

    await broadcaster.broadcast("incident_escalated", {
        "id": incident.id,
        "status": incident.status,
        "rejector": body.rejector,
        "reason": body.reason
    })

    return incident

@router.post("/{incident_id}/escalate", response_model=IncidentRead)
async def escalate_incident(
    incident_id: str,
    body: EscalationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Explicitly escalates incident to on-call engineers via Slack or PagerDuty,
    attaching full investigation context.
    """
    stmt = select(Incident).options(selectinload(Incident.events)).where(Incident.id == incident_id)
    result = await db.execute(stmt)
    incident = result.scalars().first()
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Incident {incident_id} not found")

    now = utc_now()
    incident.status = IncidentStatus.ESCALATED.value
    incident.last_seen_at = now

    diag = incident.diagnosis
    action = incident.remediation

    dispatch_res = []
    if body.channel in ["slack", "all"]:
        slack_res = await dispatcher.dispatch_slack(
            incident={"id": incident.id, "service": incident.service, "severity": incident.severity},
            diagnosis=diag,
            action=action
        )
        dispatch_res.append(slack_res)

    if body.channel in ["pagerduty", "all"]:
        pd_res = await dispatcher.dispatch_pagerduty(
            incident={"id": incident.id, "service": incident.service, "severity": incident.severity, "fingerprint": incident.fingerprint},
            diagnosis=diag
        )
        dispatch_res.append(pd_res)

    event = IncidentEvent(
        incident_id=incident.id,
        event_type="ESCALATED",
        message=f"Incident escalated via {body.channel}. Reason: {body.reason}",
        payload_json=json.dumps({"reason": body.reason, "dispatches": dispatch_res}),
        created_at=now
    )
    db.add(event)
    await db.commit()
    await db.refresh(incident)

    await broadcaster.broadcast("incident_escalated", {
        "id": incident.id,
        "status": incident.status,
        "channel": body.channel,
        "reason": body.reason
    })

    return incident
