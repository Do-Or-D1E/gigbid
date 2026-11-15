"""Builds the R&D report PDF from docs/report/report.md.

Every number in the report is a placeholder resolved from evals/results/ at build time:
  {{decisions_main:summary.bid_skip.f1|.3f}}   value from evals/results/decisions_main.json
  {{table:decisions}}                         a table from evals/runners/make_tables.py
so numbers cannot drift from the result files. Unresolvable placeholders render as "n/a"
and are listed on stderr.

    uv run python docs/report/build_report.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (Image, KeepTogether, ListFlowable, ListItem, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "evals" / "results"
sys.path.insert(0, str(ROOT))
from evals.runners import make_tables  # noqa: E402

MISSING: list[str] = []


def resolve(expr: str) -> str:
    fmt = None
    if "|" in expr:
        expr, fmt = expr.split("|", 1)
    if expr.startswith("table:"):
        return "\x00TABLE:" + expr[6:] + "\x00"
    fname, _, path = expr.partition(":")
    p = RES / f"{fname}.json"
    try:
        node = json.loads(p.read_text(encoding="utf-8"))
        for part in path.split("."):
            node = node[int(part)] if isinstance(node, list) else node[part]
    except Exception:  # noqa: BLE001
        MISSING.append(expr)
        return "n/a"
    if node is None:
        return "n/a"
    if fmt and isinstance(node, (int, float)):
        if fmt.endswith("%"):
            return f"{node * 100:.{int(fmt[1:-1] or 0)}f}%"
        return format(node, fmt)
    return str(node)


def md_inline(text: str) -> str:
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", text)
    text = re.sub(r"`([^`]+)`", r"<font face='Courier'>\1</font>", text)
    return text


def md_table(lines: list[str], styles) -> Table:
    rows = [[c.strip() for c in ln.strip().strip("|").split("|")] for ln in lines if not re.match(r"^\s*\|?\s*-", ln)]
    cell = ParagraphStyle("cell", parent=styles["BodyText"], fontSize=7.2, leading=8.6)
    head = ParagraphStyle("head", parent=cell, fontName="Helvetica-Bold")
    data = [[Paragraph(md_inline(c), head if i == 0 else cell) for c in r] for i, r in enumerate(rows)]
    n = max(len(r) for r in data)
    data = [r + [""] * (n - len(r)) for r in data]
    t = Table(data, repeatRows=1, colWidths=[(17.0 * cm) / n] * n)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#999999")),
                           ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8ecef")),
                           ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 3),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 3)]))
    return t


def build(src: Path, out: Path) -> None:
    styles = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.4, leading=12.2,
                          alignment=TA_JUSTIFY, spaceAfter=4)
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=13.5, spaceBefore=8, spaceAfter=4)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=11, spaceBefore=6, spaceAfter=3)
    title = ParagraphStyle("title", parent=styles["Title"], fontSize=17, spaceAfter=4)
    small = ParagraphStyle("small", parent=body, fontSize=8, leading=10, alignment=0)
    raw = src.read_text(encoding="utf-8")
    text = re.sub(r"\{\{(.+?)\}\}", lambda m: resolve(m.group(1).strip()), raw)
    tables = {k: fn() for k, fn in make_tables.SECTIONS.items()}
    text = re.sub(r"\x00TABLE:(\w+)\x00", lambda m: tables.get(m.group(1), "_table missing_"), text)
    story: list = []
    lines = text.split("\n")
    i = 0
    para: list[str] = []

    def flush():
        if para:
            story.append(Paragraph(md_inline(" ".join(para)), body))
            para.clear()

    while i < len(lines):
        ln = lines[i]
        if ln.startswith("% "):
            flush()
            story.append(Paragraph(md_inline(ln[2:]), title))
        elif ln.startswith("%% "):
            flush()
            story.append(Paragraph(md_inline(ln[3:]), small))
        elif ln.startswith("# "):
            flush()
            story.append(Paragraph(md_inline(ln[2:]), h1))
        elif ln.startswith("## "):
            flush()
            story.append(Paragraph(md_inline(ln[3:]), h2))
        elif ln.strip() == "\\newpage":
            flush()
            story.append(PageBreak())
        elif ln.startswith("![") and "](" in ln:
            flush()
            m = re.match(r"!\[(.*?)\]\((.+?)\)(?:\{width=(\d+)\})?", ln)
            path = ROOT / m.group(2)
            width = float(m.group(3) or 12) * cm
            if path.exists():
                img = Image(str(path))
                ratio = img.imageHeight / img.imageWidth
                img.drawWidth, img.drawHeight = width, width * ratio
                story.append(KeepTogether([img, Paragraph(md_inline(m.group(1)), small)]))
        elif ln.lstrip().startswith("|"):
            flush()
            block = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                block.append(lines[i])
                i += 1
            story.append(md_table(block, styles))
            story.append(Spacer(1, 4))
            continue
        elif re.match(r"^\s*([-*]|\d+\.)\s+", ln):
            flush()
            items = []
            while i < len(lines) and re.match(r"^\s*([-*]|\d+\.)\s+", lines[i]):
                items.append(ListItem(Paragraph(md_inline(re.sub(r"^\s*([-*]|\d+\.)\s+", "", lines[i])), body),
                                      leftIndent=10))
                i += 1
            story.append(ListFlowable(items, bulletType="bullet", start="•", leftIndent=12, bulletFontSize=7))
            continue
        elif not ln.strip():
            flush()
        else:
            para.append(ln.strip())
        i += 1
    flush()

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(2 * cm, 1.1 * cm, "GigBid R&D report, Abdul Majeed (23P-3038), AI-4016")
        canvas.drawRightString(19 * cm, 1.1 * cm, f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(str(out), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.6 * cm,
                            bottomMargin=1.6 * cm, title="GigBid R&D report", author="Abdul Majeed")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    src = ROOT / "docs" / "report" / "report.md"
    out = ROOT / "docs" / "report" / "GigBid_RnD_Report_23P-3038.pdf"
    build(src, out)
    if MISSING:
        print("unresolved placeholders:", sorted(set(MISSING)), file=sys.stderr)
    print("wrote", out)
