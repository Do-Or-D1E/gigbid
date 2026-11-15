"""Render cv.md to a plain, parseable PDF with reportlab (deterministic via invariant=1)."""
from __future__ import annotations

import re
from xml.sax.saxutils import escape


def _clean(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = text.replace("`", "")
    # keep ASCII only (no unicode sub/superscripts)
    return text.encode("ascii", "replace").decode("ascii")


def render_cv_pdf(md_text: str, out_path) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer

    body = ParagraphStyle("body", fontName="Helvetica", fontSize=10, leading=13)
    h1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=18, leading=22, spaceAfter=2)
    h2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=12, leading=15, spaceBefore=8, spaceAfter=3)
    h3 = ParagraphStyle("h3", fontName="Helvetica-Bold", fontSize=10.5, leading=13, spaceBefore=4)
    flow = []
    bullets = []

    def flush():
        nonlocal bullets
        if bullets:
            flow.append(ListFlowable([ListItem(Paragraph(escape(b), body), leftIndent=12) for b in bullets],
                                     bulletType="bullet", start="-", leftIndent=12))
            bullets = []

    for raw in md_text.splitlines():
        line = _clean(raw.rstrip())
        if not line.strip():
            flush()
            flow.append(Spacer(1, 3))
            continue
        if line.startswith("### "):
            flush()
            flow.append(Paragraph(escape(line[4:]), h3))
        elif line.startswith("## "):
            flush()
            flow.append(Paragraph(escape(line[3:]), h2))
        elif line.startswith("# "):
            flush()
            flow.append(Paragraph(escape(line[2:]), h1))
        elif line.startswith("- "):
            bullets.append(line[2:])
        else:
            flush()
            flow.append(Paragraph(escape(line), body))
    flush()
    doc = SimpleDocTemplate(str(out_path), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm, title="CV", author="", invariant=1)
    doc.build(flow)
