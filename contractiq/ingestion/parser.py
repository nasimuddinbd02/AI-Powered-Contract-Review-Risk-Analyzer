"""PDF text extraction (SRS FR-1.2).

Uses PyMuPDF (``fitz``) to extract selectable text while preserving page numbers
and section headers as metadata. Falls back to ``pytesseract`` OCR for
scanned/image-only pages. When neither library is available (e.g. a minimal
offline environment) a plain-text fallback keeps the pipeline runnable.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass

from ..core.logging import get_logger, trace

log = get_logger("ingestion.parser")

# A "section header" heuristic: short, mostly-uppercase or numbered lines.
_HEADER_RE = re.compile(r"^\s*(\d+(\.\d+)*\.?\s+[A-Z].{0,60}|[A-Z][A-Z \-]{3,60})\s*$")


@dataclass
class PageText:
    """Extracted text for a single page (SRS FR-1.2 metadata)."""

    page_num: int  # 1-indexed
    text: str
    section_header: str | None = None


def _detect_header(text: str) -> str | None:
    for line in text.splitlines():
        m = _HEADER_RE.match(line)
        if m:
            return line.strip()
    return None


def parse_pdf_bytes(data: bytes, filename: str = "upload.pdf") -> list[PageText]:
    """Extract text from in-memory PDF bytes (ephemeral; SRS 4.4)."""
    with trace("ingestion.parse", filename=filename, size=len(data)):
        # Non-PDF input (e.g. a .txt demo contract) → decode as text directly.
        if not data.startswith(b"%PDF-"):
            return _parse_as_text(data)
        try:
            import fitz  # PyMuPDF
        except Exception:
            log.warning("PyMuPDF unavailable; treating input as UTF-8 text.")
            return _parse_as_text(data)

        pages: list[PageText] = []
        with fitz.open(stream=data, filetype="pdf") as doc:
            for i, page in enumerate(doc, start=1):
                text = page.get_text("text").strip()
                if not text:  # scanned page → OCR fallback
                    text = _ocr_page(page)
                pages.append(PageText(page_num=i, text=text, section_header=_detect_header(text)))
        return pages


def parse_pdf(path: str) -> list[PageText]:
    """Extract text from a PDF file path."""
    with open(path, "rb") as f:
        return parse_pdf_bytes(f.read(), filename=path)


def _ocr_page(page) -> str:  # pragma: no cover - requires tesseract + image
    """OCR a single rendered page using pytesseract (SRS FR-1.2 fallback)."""
    try:
        import fitz  # noqa: F401
        import pytesseract
        from PIL import Image

        pix = page.get_pixmap(dpi=200)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        return pytesseract.image_to_string(img).strip()
    except Exception as exc:
        log.warning("OCR fallback failed: %s", exc)
        return ""


def _parse_as_text(data: bytes) -> list[PageText]:
    """Fallback: decode bytes as text and split on form-feeds into pages."""
    raw = data.decode("utf-8", errors="ignore")
    parts = raw.split("\f") if "\f" in raw else [raw]
    return [
        PageText(page_num=i, text=p.strip(), section_header=_detect_header(p))
        for i, p in enumerate(parts, start=1)
        if p.strip()
    ] or [PageText(page_num=1, text=raw.strip())]
