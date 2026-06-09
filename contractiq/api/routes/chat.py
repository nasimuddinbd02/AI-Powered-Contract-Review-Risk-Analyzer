"""Chat / Q&A endpoint (SRS FR-6)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ...auth import get_current_user
from ...auth.models import Role, User
from ...core.logging import get_logger
from ...core.models import QATurn
from ...service import AccessDenied, sessions

log = get_logger("api.chat")
router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    query: str


@router.post("/chat/{contract_id}", response_model=QATurn)
def chat(contract_id: str, req: ChatRequest, user: User = Depends(get_current_user)) -> QATurn:
    if not req.query.strip():
        raise HTTPException(400, "query must not be empty.")
    try:
        return sessions.ask(contract_id, req.query, owner_id=user.id, is_admin=user.role == Role.ADMIN)
    except KeyError:
        raise HTTPException(404, f"Unknown contract_id: {contract_id}")
    except AccessDenied:
        raise HTTPException(403, "You do not have access to this contract.")
