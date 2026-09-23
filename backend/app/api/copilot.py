"""SRE Copilot chat API endpoints."""
import uuid
from typing import Dict, Optional, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.copilot.copilot import (
    CopilotSession, CopilotMessage, CopilotRequest, CopilotResponse, chat
)

router = APIRouter(prefix="/copilot", tags=["copilot"])
_sessions: Dict[str, CopilotSession] = {}

class NewSessionRequest(BaseModel):
    incident_id: Optional[str] = None
    incident_context: Optional[Dict[str, Any]] = None

@router.post("/sessions", summary="Create a new copilot session")
async def create_session(req: NewSessionRequest):
    sid = f"sess-{uuid.uuid4().hex[:10]}"
    session = CopilotSession(session_id=sid, incident_id=req.incident_id,
                              incident_context=req.incident_context)
    _sessions[sid] = session
    return {"session_id": sid, "incident_id": req.incident_id, "message": "Session ready."}

@router.post("/chat", summary="Send a message to the SRE Copilot")
async def copilot_chat(req: CopilotRequest) -> CopilotResponse:
    session = _sessions.get(req.session_id)
    if not session:
        # Auto-create session for convenience
        session = CopilotSession(session_id=req.session_id, incident_context=req.incident_context)
        _sessions[req.session_id] = session

    if req.incident_context:
        session.incident_context = req.incident_context

    # Append user message to history
    session.messages.append(CopilotMessage(role="user", content=req.message))

    # Get copilot response
    response = await chat(session, req.message, req.incident_context)

    # Append assistant reply to history
    session.messages.append(CopilotMessage(role="assistant", content=response.reply))
    return response

@router.get("/sessions/{session_id}", summary="Get session history")
async def get_session(session_id: str):
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(404, f"Session {session_id!r} not found.")
    return session.model_dump()

@router.delete("/sessions/{session_id}", summary="Clear a session")
async def clear_session(session_id: str):
    if session_id not in _sessions:
        raise HTTPException(404, f"Session {session_id!r} not found.")
    del _sessions[session_id]
    return {"message": f"Session {session_id} cleared."}
