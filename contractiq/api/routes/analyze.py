"""Analyze endpoint (SRS FR-2..FR-5).

Runs the full multi-agent pipeline and returns the analysed contract, including
clauses, risk scores, summaries, and negotiation suggestions. Requires auth;
users may only access their own contracts (admins may access any).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ...auth import get_current_user
from ...auth.models import Role, User
from ...core.logging import get_logger
from ...core.models import Contract
from ...service import AccessDenied, sessions

log = get_logger("api.analyze")
router = APIRouter(tags=["analyze"])


def _is_admin(user: User) -> bool:
    return user.role == Role.ADMIN


@router.post("/analyze/{contract_id}", response_model=Contract)
def analyze_contract(contract_id: str, user: User = Depends(get_current_user)) -> Contract:
    try:
        return sessions.analyze(contract_id, owner_id=user.id, is_admin=_is_admin(user))
    except KeyError:
        raise HTTPException(404, f"Unknown contract_id: {contract_id}")
    except AccessDenied:
        raise HTTPException(403, "You do not have access to this contract.")


@router.get("/contracts", response_model=list[Contract])
def list_contracts(user: User = Depends(get_current_user)) -> list[Contract]:
    """List the contracts owned by the current user (all, for admins)."""
    return sessions.list_for_owner(user.id, is_admin=_is_admin(user))


@router.get("/contract/{contract_id}", response_model=Contract)
def get_contract(contract_id: str, user: User = Depends(get_current_user)) -> Contract:
    try:
        return sessions.get_contract(contract_id, owner_id=user.id, is_admin=_is_admin(user))
    except KeyError:
        raise HTTPException(404, f"Unknown contract_id: {contract_id}")
    except AccessDenied:
        raise HTTPException(403, "You do not have access to this contract.")


@router.delete("/contract/{contract_id}")
def delete_contract(contract_id: str, user: User = Depends(get_current_user)) -> dict:
    """Purge the contract from memory (SRS 4.4 — user-controlled deletion)."""
    try:
        sessions.delete(contract_id, owner_id=user.id, is_admin=_is_admin(user))
    except AccessDenied:
        raise HTTPException(403, "You do not have access to this contract.")
    return {"deleted": contract_id}
