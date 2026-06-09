"""Upload endpoint (SRS FR-1.1).

Validates the uploaded file is a non-corrupted PDF within the size limit, then
ingests it (parse → chunk → embed). Contract text is held in memory only.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from ...auth import get_current_user
from ...auth.models import User
from ...core.config import get_settings
from ...core.logging import get_logger
from ...service import sessions

log = get_logger("api.upload")
router = APIRouter(tags=["upload"])

_PDF_MAGIC = b"%PDF-"


@router.post("/upload")
async def upload_contract(
    file: UploadFile = File(...), user: User = Depends(get_current_user)
) -> dict:
    settings = get_settings()
    data = await file.read()

    # --- validation (SRS FR-1.1 / 4.4) ---
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(413, f"File exceeds {settings.max_upload_mb} MB limit.")
    if not data:
        raise HTTPException(400, "Empty file.")
    name = (file.filename or "").lower()
    is_pdf_mime = (file.content_type or "").lower() in {"application/pdf", "application/x-pdf"}
    is_pdf_magic = data[:5] == _PDF_MAGIC
    is_txt_demo = name.endswith(".txt")  # allowed for offline demos

    # A claimed PDF (by mime or extension) must have valid PDF magic bytes.
    if (is_pdf_mime or name.endswith(".pdf")) and not is_pdf_magic:
        raise HTTPException(422, "File is not a valid, non-corrupted PDF.")
    if not (is_pdf_magic or is_txt_demo):
        raise HTTPException(415, "Only PDF files are accepted.")

    contract = sessions.ingest(data, filename=file.filename or "upload.pdf", owner_id=user.id)
    return {
        "contract_id": contract.contract_id,
        "filename": contract.filename,
        "page_count": contract.page_count,
        "chunk_count": contract.chunk_count,
        "status": contract.status,
    }
