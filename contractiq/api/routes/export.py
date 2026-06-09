"""Report export endpoint (SRS FR-9)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response

from ...auth import get_current_user
from ...auth.models import Role, User
from ...core.logging import get_logger
from ...report import generate_report
from ...service import AccessDenied, sessions

log = get_logger("api.export")
router = APIRouter(tags=["export"])


@router.get("/export/{contract_id}")
def export_report(contract_id: str, user: User = Depends(get_current_user)) -> Response:
    try:
        contract = sessions.get_contract(contract_id, owner_id=user.id, is_admin=user.role == Role.ADMIN)
    except KeyError:
        raise HTTPException(404, f"Unknown contract_id: {contract_id}")
    except AccessDenied:
        raise HTTPException(403, "You do not have access to this contract.")

    content, media_type = generate_report(contract)
    ext = "pdf" if media_type == "application/pdf" else "html"
    filename = f"ContractIQ_{contract.filename.rsplit('.', 1)[0]}.{ext}"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
