"""
API endpoints for generating and retrieving automated incident post-mortems.
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from backend.postmortem.generator import PostMortemData, generate_postmortem, PostMortemDocument

router = APIRouter(prefix="/postmortems", tags=["postmortems"])

# In-memory store for generated post-mortems
_postmortems: Dict[str, PostMortemDocument] = {}

@router.post("/generate", response_model=PostMortemDocument, summary="Generate an incident post-mortem")
async def create_postmortem(data: PostMortemData):
    doc = generate_postmortem(data)
    _postmortems[data.incident_id] = doc
    return doc

@router.get("/{incident_id}", response_model=PostMortemDocument, summary="Get post-mortem by incident ID")
async def get_postmortem(incident_id: str):
    doc = _postmortems.get(incident_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Post-mortem for incident '{incident_id}' not found.")
    return doc

@router.get("/", summary="List all generated post-mortems")
async def list_postmortems():
    return {
        "count": len(_postmortems),
        "postmortems": [
            {
                "incident_id": doc.incident_id,
                "title": doc.title,
                "generated_at": doc.generated_at,
                "word_count": doc.word_count,
            }
            for doc in _postmortems.values()
        ]
    }
