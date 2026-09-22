from typing import Dict, Any, Optional, TypedDict, List
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from backend.tools.investigator import collect_evidence
from backend.agent.diagnose import diagnose_incident_evidence
from backend.remediation.catalog import build_remediation_action, RiskTier
from backend.remediation.executor import execute_remediation, SafetyGateError

class IncidentGraphState(TypedDict, total=False):
    incident_id: str
    service: str
    namespace: str
    alert_summary: str
    evidence: Dict[str, Any]
    diagnosis: Dict[str, Any]
    action: Dict[str, Any]
    remediation_result: Dict[str, Any]
    is_approved: bool
    approver: Optional[str]
    status: str
    requires_human_approval: bool
    error: Optional[str]

# 1. Investigate Node
async def investigate_node(state: IncidentGraphState) -> IncidentGraphState:
    service = state.get("service", "unknown")
    namespace = state.get("namespace", "production")
    evidence = await collect_evidence(service, namespace)
    return {
        "evidence": evidence,
        "status": "INVESTIGATED"
    }

# 2. Diagnose Node
async def diagnose_node(state: IncidentGraphState) -> IncidentGraphState:
    evidence = state.get("evidence", {})
    alert_summary = state.get("alert_summary", "")
    diagnosis = diagnose_incident_evidence(evidence, alert_summary)
    
    # Propose remediation action based on diagnosis
    action = build_remediation_action(
        action_type=diagnosis.action_type,
        service=state.get("service", "app"),
        namespace=state.get("namespace", "production")
    )

    return {
        "diagnosis": diagnosis.to_dict(),
        "action": action.to_dict(),
        "requires_human_approval": action.requires_human_approval,
        "status": "DIAGNOSED"
    }

# 3. Router Condition
def route_after_diagnosis(state: IncidentGraphState) -> str:
    diagnosis = state.get("diagnosis", {})
    if diagnosis.get("requires_escalation"):
        return "escalate"
    
    action = state.get("action", {})
    if action.get("requires_human_approval") and not state.get("is_approved", False):
        return "await_approval"

    return "act"

# 4. Await Approval (Safety Gate Interruption) Node
async def await_approval_node(state: IncidentGraphState) -> IncidentGraphState:
    """Safety Gate: Pauses graph execution until signed human approval is registered."""
    return {
        "status": "ACTION_REQUIRED"
    }

# 5. Act Node
async def act_node(state: IncidentGraphState) -> IncidentGraphState:
    action_dict = state.get("action", {})
    action = build_remediation_action(
        action_type=action_dict.get("action_type", "RESTART_POD"),
        service=state.get("service", "app"),
        namespace=state.get("namespace", "production")
    )
    is_approved = state.get("is_approved", False)
    approver = state.get("approver")

    try:
        res = await execute_remediation(
            action=action,
            is_approved_by_human=is_approved,
            approver=approver
        )
        return {
            "remediation_result": res,
            "status": "RESOLVED"
        }
    except SafetyGateError as e:
        return {
            "error": str(e),
            "status": "ACTION_REQUIRED"
        }

# 6. Escalate Node
async def escalate_node(state: IncidentGraphState) -> IncidentGraphState:
    return {
        "status": "ESCALATED"
    }

def create_incident_response_graph():
    builder = StateGraph(IncidentGraphState)

    builder.add_node("investigate", investigate_node)
    builder.add_node("diagnose", diagnose_node)
    builder.add_node("await_approval", await_approval_node)
    builder.add_node("act", act_node)
    builder.add_node("escalate", escalate_node)

    builder.set_entry_point("investigate")
    builder.add_edge("investigate", "diagnose")

    builder.add_conditional_edges(
        "diagnose",
        route_after_diagnosis,
        {
            "escalate": "escalate",
            "await_approval": "await_approval",
            "act": "act"
        }
    )

    builder.add_edge("await_approval", END)
    builder.add_edge("act", END)
    builder.add_edge("escalate", END)

    memory = MemorySaver()
    return builder.compile(checkpointer=memory)

incident_graph = create_incident_response_graph()
