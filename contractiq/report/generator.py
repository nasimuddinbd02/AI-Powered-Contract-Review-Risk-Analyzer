"""PDF report builder (SRS FR-9).

Produces a branded report with: cover page, executive summary, overall risk
score, clause-by-clause analysis table, negotiation suggestions, and an appendix
of original clause text. Uses ReportLab when installed; otherwise emits a clean
HTML report (also browser-printable to PDF) so export always works.
"""
from __future__ import annotations

import html
import io

from ..core.logging import get_logger, trace
from ..core.models import Contract, RiskLevel

log = get_logger("report.generator")

_RISK_HEX = {RiskLevel.HIGH: "#c0392b", RiskLevel.MEDIUM: "#d4ac0d", RiskLevel.LOW: "#27ae60"}


def generate_report(contract: Contract) -> tuple[bytes, str]:
    """Return ``(bytes, media_type)`` for the analysis report."""
    with trace("report.generate", contract_id=contract.contract_id):
        try:
            return _reportlab_pdf(contract), "application/pdf"
        except Exception as exc:  # pragma: no cover - missing reportlab
            log.warning("ReportLab unavailable, falling back to HTML report: %s", exc)
            return _html_report(contract).encode("utf-8"), "text/html"


# --- ReportLab PDF ----------------------------------------------------------

def _reportlab_pdf(contract: Contract) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, PageBreak,
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, title=f"ContractIQ Report — {contract.filename}")
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("Brand", parent=styles["Title"], textColor=colors.HexColor("#1f3a93")))
    flow = []

    # Cover
    flow += [
        Spacer(1, 1.5 * inch),
        Paragraph("ContractIQ", styles["Brand"]),
        Paragraph("AI-Powered Contract Review &amp; Risk Analysis", styles["Heading2"]),
        Spacer(1, 0.5 * inch),
        Paragraph(f"<b>File:</b> {html.escape(contract.filename)}", styles["Normal"]),
        Paragraph(f"<b>Type:</b> {html.escape(contract.contract_type)}", styles["Normal"]),
        Paragraph(f"<b>Parties:</b> {html.escape(', '.join(contract.parties) or 'Not detected')}", styles["Normal"]),
        Paragraph(f"<b>Governing law:</b> {html.escape(contract.governing_law)}", styles["Normal"]),
        Paragraph(f"<b>Overall risk score:</b> {contract.overall_risk_score}/100", styles["Normal"]),
        PageBreak(),
    ]

    # Executive summary
    flow += [Paragraph("Executive Summary", styles["Heading1"])]
    counts = _risk_counts(contract)
    flow += [Paragraph(
        f"This contract was analysed across {len(contract.clauses)} standard clause types. "
        f"It contains {counts['HIGH']} high-risk, {counts['MEDIUM']} medium-risk, and "
        f"{counts['LOW']} low-risk clauses, with an overall weighted risk score of "
        f"<b>{contract.overall_risk_score}/100</b>.", styles["Normal"])]
    flow += [Spacer(1, 0.3 * inch)]

    # Clause-by-clause table
    flow += [Paragraph("Clause-by-Clause Analysis", styles["Heading1"])]
    data = [["Clause Type", "Risk", "Score", "Plain-English Summary"]]
    for c in contract.clauses:
        data.append([
            c.clause_type.value,
            c.risk_level.value if c.risk_level else "—",
            f"{c.risk_score:.0f}" if c.risk_score is not None else "—",
            Paragraph(html.escape(c.plain_english_summary or ""), styles["Normal"]),
        ])
    table = Table(data, colWidths=[1.4 * inch, 0.7 * inch, 0.6 * inch, 3.5 * inch], repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3a93")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]
    for i, c in enumerate(contract.clauses, start=1):
        if c.risk_level:
            style.append(("TEXTCOLOR", (1, i), (1, i), colors.HexColor(_RISK_HEX[c.risk_level])))
    table.setStyle(TableStyle(style))
    flow += [table, Spacer(1, 0.3 * inch)]

    # Negotiation suggestions
    flow += [Paragraph("Negotiation Suggestions", styles["Heading1"])]
    suggestions = [c for c in contract.clauses if c.negotiation_suggestion]
    if not suggestions:
        flow += [Paragraph("No high or medium risk clauses required suggestions.", styles["Normal"])]
    for c in suggestions:
        flow += [
            Paragraph(f"<b>{c.clause_type.value}</b> ({c.risk_level.value})", styles["Heading3"]),
            Paragraph(html.escape(c.negotiation_suggestion), styles["Normal"]),
            Spacer(1, 0.1 * inch),
        ]

    # Appendix
    flow += [PageBreak(), Paragraph("Appendix — Original Clause Text", styles["Heading1"])]
    for c in contract.clauses:
        flow += [
            Paragraph(f"<b>{c.clause_type.value}</b> (pages {c.page_references or '—'})", styles["Heading3"]),
            Paragraph(html.escape(c.original_text[:1500]), styles["Normal"]),
            Spacer(1, 0.15 * inch),
        ]

    doc.build(flow)
    return buf.getvalue()


# --- HTML fallback ----------------------------------------------------------

def _html_report(contract: Contract) -> str:
    rows = "".join(
        f"<tr><td>{html.escape(c.clause_type.value)}</td>"
        f"<td style='color:{_RISK_HEX.get(c.risk_level, '#333')}'>"
        f"{c.risk_level.value if c.risk_level else '—'}</td>"
        f"<td>{f'{c.risk_score:.0f}' if c.risk_score is not None else '—'}</td>"
        f"<td>{html.escape(c.plain_english_summary or '')}</td></tr>"
        for c in contract.clauses
    )
    suggestions = "".join(
        f"<h3>{html.escape(c.clause_type.value)} ({c.risk_level.value})</h3>"
        f"<p>{html.escape(c.negotiation_suggestion)}</p>"
        for c in contract.clauses if c.negotiation_suggestion
    ) or "<p>No high or medium risk clauses required suggestions.</p>"
    appendix = "".join(
        f"<h3>{html.escape(c.clause_type.value)}</h3>"
        f"<pre>{html.escape(c.original_text[:1500])}</pre>"
        for c in contract.clauses
    )
    return f"""<!doctype html><html><head><meta charset="utf-8">
                <title>ContractIQ Report — {html.escape(contract.filename)}</title>
                <style>body{{font-family:Arial,sans-serif;margin:40px;color:#222}}
                h1{{color:#1f3a93}} table{{border-collapse:collapse;width:100%}}
                td,th{{border:1px solid #ccc;padding:6px;font-size:13px;text-align:left}}
                th{{background:#1f3a93;color:#fff}} pre{{white-space:pre-wrap;background:#f6f6f6;padding:8px}}</style>
                </head><body>
                <h1>ContractIQ</h1><p>AI-Powered Contract Review &amp; Risk Analysis</p>
                <h2>Cover</h2>
                <p><b>File:</b> {html.escape(contract.filename)}<br>
                <b>Type:</b> {html.escape(contract.contract_type)}<br>
                <b>Parties:</b> {html.escape(', '.join(contract.parties) or 'Not detected')}<br>
                <b>Governing law:</b> {html.escape(contract.governing_law)}<br>
                <b>Overall risk score:</b> {contract.overall_risk_score}/100</p>
                <h1>Clause-by-Clause Analysis</h1>
                <table><tr><th>Clause Type</th><th>Risk</th><th>Score</th><th>Plain-English Summary</th></tr>{rows}</table>
                <h1>Negotiation Suggestions</h1>{suggestions}
                <h1>Appendix — Original Clause Text</h1>{appendix}
                </body></html>"""


def _risk_counts(contract: Contract) -> dict[str, int]:
    counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for c in contract.clauses:
        if c.risk_level:
            counts[c.risk_level.value] += 1
    return counts
