"""
CATERYA Agentic Enterprise — PDF Exporter
=========================================
Generate PDF profesional dari hasil pipeline run menggunakan reportlab.
Dipanggil dari pipeline_page.py saat user klik "Export PDF".

© 2026 Caterya Tech. All Rights Reserved.
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .engine import PipelineRun, Pipeline


def generate_run_pdf(run: "PipelineRun", pipe: "Pipeline") -> bytes:
    """
    Generate PDF report dari hasil pipeline run.
    Returns bytes yang bisa langsung di-pass ke st.download_button().

    Raises ImportError jika reportlab tidak terinstall.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib.colors import HexColor, white, black
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, PageBreak, KeepTogether,
    )
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

    # ── Warna tema CATERYA ───────────────────────────────────────────────────
    PURPLE      = HexColor("#6366f1")
    DARK_BG     = HexColor("#1e1e2e")
    LIGHT_GRAY  = HexColor("#f1f5f9")
    MID_GRAY    = HexColor("#94a3b8")
    SUCCESS_GRN = HexColor("#22c55e")
    FAIL_RED    = HexColor("#ef4444")
    TEXT_DARK   = HexColor("#1e293b")

    # ── Styles ───────────────────────────────────────────────────────────────
    styles = getSampleStyleSheet()

    def _style(name, parent="Normal", **kw) -> ParagraphStyle:
        return ParagraphStyle(name, parent=styles[parent], **kw)

    s_title = _style("CTitle", "Title",
        fontSize=22, textColor=PURPLE, spaceAfter=4, spaceBefore=0, leading=28)
    s_subtitle = _style("CSubtitle",
        fontSize=11, textColor=MID_GRAY, spaceAfter=16, leading=14)
    s_h1 = _style("CH1", "Heading1",
        fontSize=14, textColor=PURPLE, spaceBefore=18, spaceAfter=6,
        borderPadding=(0,0,4,0))
    s_h2 = _style("CH2", "Heading2",
        fontSize=11, textColor=TEXT_DARK, spaceBefore=12, spaceAfter=4, fontName="Helvetica-Bold")
    s_body = _style("CBody",
        fontSize=9, textColor=TEXT_DARK, leading=14, spaceAfter=6)
    s_code = _style("CCode",
        fontSize=8, fontName="Courier", textColor=HexColor("#334155"),
        backColor=LIGHT_GRAY, leading=12, leftIndent=8, rightIndent=8,
        spaceBefore=4, spaceAfter=4, borderPadding=6)
    s_caption = _style("CCaption",
        fontSize=8, textColor=MID_GRAY, leading=11, spaceAfter=2)
    s_center = _style("CCenter",
        fontSize=9, textColor=TEXT_DARK, leading=14, alignment=TA_CENTER)

    # ── Buffer ───────────────────────────────────────────────────────────────
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2.5*cm, bottomMargin=2*cm,
        title=f"Pipeline Report — {pipe.name}",
        author="CATERYA Agentic Enterprise",
    )
    W = A4[0] - 4*cm  # usable width

    story = []

    # ── Header ───────────────────────────────────────────────────────────────
    # Logo / brand bar via table
    brand_table = Table(
        [["⚡ CATERYA", "Pipeline Run Report"]],
        colWidths=[W * 0.5, W * 0.5],
    )
    brand_table.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,-1), DARK_BG),
        ("TEXTCOLOR",    (0,0), (0,0),   PURPLE),
        ("TEXTCOLOR",    (1,0), (1,0),   white),
        ("FONTNAME",     (0,0), (-1,-1), "Helvetica-Bold"),
        ("FONTSIZE",     (0,0), (-1,-1), 11),
        ("ALIGN",        (0,0), (0,0),   "LEFT"),
        ("ALIGN",        (1,0), (1,0),   "RIGHT"),
        ("TOPPADDING",   (0,0), (-1,-1), 10),
        ("BOTTOMPADDING",(0,0), (-1,-1), 10),
        ("LEFTPADDING",  (0,0), (-1,-1), 12),
        ("RIGHTPADDING", (0,0), (-1,-1), 12),
        ("ROUNDEDCORNERS", [6]),
    ]))
    story.append(brand_table)
    story.append(Spacer(1, 16))

    # Title
    story.append(Paragraph(pipe.name, s_title))
    story.append(Paragraph(pipe.description or "", s_subtitle))
    story.append(HRFlowable(width="100%", thickness=1, color=PURPLE, spaceAfter=8))

    # ── Run Metadata table ───────────────────────────────────────────────────
    def _fmt_ts(ts: str) -> str:
        if not ts:
            return "-"
        try:
            return datetime.fromisoformat(ts).strftime("%d %b %Y, %H:%M:%S UTC")
        except Exception:
            return ts[:19]

    status_color = SUCCESS_GRN if run.status.value == "completed" else FAIL_RED
    status_icon  = "COMPLETED" if run.status.value == "completed" else run.status.value.upper()

    meta_data = [
        ["Run ID",       run.run_id,           "Status",      status_icon],
        ["Pipeline",     pipe.pipeline_id,     "Category",    pipe.category.title()],
        ["Started",      _fmt_ts(run.started_at), "Finished", _fmt_ts(run.finished_at)],
        ["Duration",     f"{run.duration_sec:.1f}s", "Triggered by", run.triggered_by],
        ["Total Tokens", f"{run.total_tokens:,}", "Steps",    str(len(run.steps))],
        ["Est. Cost",    f"${run.total_cost_usd:.4f} USD", "Tags", ", ".join(pipe.tags) or "-"],
    ]

    meta_table = Table(meta_data, colWidths=[W*0.18, W*0.32, W*0.18, W*0.32])
    ts = TableStyle([
        ("FONTNAME",   (0,0), (-1,-1), "Helvetica"),
        ("FONTSIZE",   (0,0), (-1,-1), 8),
        ("FONTNAME",   (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTNAME",   (2,0), (2,-1), "Helvetica-Bold"),
        ("TEXTCOLOR",  (0,0), (0,-1), PURPLE),
        ("TEXTCOLOR",  (2,0), (2,-1), PURPLE),
        ("BACKGROUND", (0,0), (-1,-1), LIGHT_GRAY),
        ("BACKGROUND", (0,0), (0,-1), HexColor("#ede9fe")),
        ("BACKGROUND", (2,0), (2,-1), HexColor("#ede9fe")),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [LIGHT_GRAY, white]),
        ("GRID",       (0,0), (-1,-1), 0.3, MID_GRAY),
        ("TOPPADDING", (0,0), (-1,-1), 6),
        ("BOTTOMPADDING",(0,0),(-1,-1),6),
        ("LEFTPADDING",(0,0),(-1,-1),8),
        ("RIGHTPADDING",(0,0),(-1,-1),8),
        ("ROUNDEDCORNERS", [4]),
    ])
    # Highlight status cell
    status_row = 0
    ts.add("TEXTCOLOR",  (3, status_row), (3, status_row), status_color)
    ts.add("FONTNAME",   (3, status_row), (3, status_row), "Helvetica-Bold")
    meta_table.setStyle(ts)
    story.append(Paragraph("Run Summary", s_h1))
    story.append(meta_table)
    story.append(Spacer(1, 12))

    # ── Input ────────────────────────────────────────────────────────────────
    story.append(Paragraph("Input", s_h1))
    _add_code_block(story, run.initial_input, s_code, s_body, W)

    # ── Step-by-step ─────────────────────────────────────────────────────────
    story.append(Paragraph("Pipeline Steps", s_h1))

    for i, step in enumerate(run.steps):
        node      = pipe.get_node(step.node_id)
        node_lbl  = node.label if node else step.node_id
        step_ok   = step.status.value == "completed"
        step_clr  = SUCCESS_GRN if step_ok else (
                    HexColor("#f97316") if step.status.value == "blocked" else FAIL_RED)

        step_block = []

        # Step header row
        step_header = Table(
            [[f"{i+1}. {node_lbl}", step.status.value.upper()]],
            colWidths=[W * 0.80, W * 0.20],
        )
        step_header.setStyle(TableStyle([
            ("BACKGROUND",   (0,0), (-1,-1), DARK_BG),
            ("TEXTCOLOR",    (0,0), (0,0),   white),
            ("TEXTCOLOR",    (1,0), (1,0),   step_clr),
            ("FONTNAME",     (0,0), (-1,-1), "Helvetica-Bold"),
            ("FONTSIZE",     (0,0), (-1,-1), 9),
            ("ALIGN",        (1,0), (1,0),   "RIGHT"),
            ("TOPPADDING",   (0,0), (-1,-1), 7),
            ("BOTTOMPADDING",(0,0), (-1,-1), 7),
            ("LEFTPADDING",  (0,0), (0,0),   10),
            ("RIGHTPADDING", (0,0), (-1,-1), 10),
        ]))
        step_block.append(step_header)

        # Step meta
        agent_label = step.agent_id.replace("_", " ").title()
        meta_row = Table(
            [[
                f"Agent: {agent_label}",
                f"Model: {step.model_used or 'N/A'}",
                f"Tokens: {step.tokens_in + step.tokens_out:,}",
                f"Latency: {step.latency_ms:.0f}ms",
                f"Ethics: {'OK' if step.ethics_passed else 'BLOCKED'}",
            ]],
            colWidths=[W*0.22, W*0.25, W*0.16, W*0.18, W*0.19],
        )
        meta_row.setStyle(TableStyle([
            ("FONTNAME",     (0,0), (-1,-1), "Helvetica"),
            ("FONTSIZE",     (0,0), (-1,-1), 7.5),
            ("TEXTCOLOR",    (0,0), (-1,-1), TEXT_DARK),
            ("BACKGROUND",   (0,0), (-1,-1), HexColor("#f8fafc")),
            ("TOPPADDING",   (0,0), (-1,-1), 5),
            ("BOTTOMPADDING",(0,0), (-1,-1), 5),
            ("LEFTPADDING",  (0,0), (-1,-1), 8),
            ("GRID",         (0,0), (-1,-1), 0.2, MID_GRAY),
        ]))
        step_block.append(meta_row)

        # Error (if any)
        if step.error:
            step_block.append(Spacer(1, 4))
            err_table = Table([[f"Error: {step.error}"]], colWidths=[W])
            err_table.setStyle(TableStyle([
                ("BACKGROUND",   (0,0), (-1,-1), HexColor("#fef2f2")),
                ("TEXTCOLOR",    (0,0), (-1,-1), FAIL_RED),
                ("FONTNAME",     (0,0), (-1,-1), "Helvetica-BoldOblique"),
                ("FONTSIZE",     (0,0), (-1,-1), 8),
                ("TOPPADDING",   (0,0), (-1,-1), 5),
                ("BOTTOMPADDING",(0,0), (-1,-1), 5),
                ("LEFTPADDING",  (0,0), (-1,-1), 8),
            ]))
            step_block.append(err_table)

        # Output
        step_block.append(Spacer(1, 6))
        step_block.append(Paragraph("Output:", s_h2))
        _add_code_block(step_block, step.output_text or "(no output)", s_code, s_body, W)
        step_block.append(Spacer(1, 8))

        story.append(KeepTogether(step_block[:3]))  # keep header + meta together
        for elem in step_block[3:]:
            story.append(elem)

        story.append(HRFlowable(width="100%", thickness=0.5, color=LIGHT_GRAY, spaceAfter=6))

    # ── Final Output ─────────────────────────────────────────────────────────
    if run.final_output:
        story.append(PageBreak())
        story.append(Paragraph("Final Output", s_h1))
        story.append(HRFlowable(width="100%", thickness=2, color=PURPLE, spaceAfter=10))
        _add_code_block(story, run.final_output, s_code, s_body, W, is_final=True)

    # ── Error summary ────────────────────────────────────────────────────────
    if run.error:
        story.append(Paragraph("Run Error", s_h1))
        err_block = Table([[run.error]], colWidths=[W])
        err_block.setStyle(TableStyle([
            ("BACKGROUND",   (0,0), (-1,-1), HexColor("#fef2f2")),
            ("TEXTCOLOR",    (0,0), (-1,-1), FAIL_RED),
            ("FONTNAME",     (0,0), (-1,-1), "Helvetica"),
            ("FONTSIZE",     (0,0), (-1,-1), 9),
            ("TOPPADDING",   (0,0), (-1,-1), 10),
            ("BOTTOMPADDING",(0,0), (-1,-1), 10),
            ("LEFTPADDING",  (0,0), (-1,-1), 12),
        ]))
        story.append(err_block)

    # ── Footer via page template ──────────────────────────────────────────────
    def _footer(canvas_obj, doc_obj):
        canvas_obj.saveState()
        canvas_obj.setFont("Helvetica", 7)
        canvas_obj.setFillColor(MID_GRAY)
        w, h = A4
        footer_text = (
            f"CATERYA Agentic Enterprise  |  Run {run.run_id}  |  "
            f"Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
        )
        canvas_obj.drawCentredString(w / 2, 1.2*cm, footer_text)
        canvas_obj.drawRightString(w - 2*cm, 1.2*cm, f"Page {doc_obj.page}")
        canvas_obj.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    buf.seek(0)
    return buf.read()


def _add_code_block(story, text: str, s_code, s_body, W: float, is_final: bool = False):
    """
    Render text ke story dengan aman — split per CHUNK baris agar tidak
    pernah melebihi satu halaman (fix untuk LayoutError).

    Root cause: satu Table/Paragraph raksasa tidak bisa di-split antar halaman
    oleh reportlab. Fix: pisahkan setiap 40 baris menjadi Paragraph tersendiri.
    """
    from reportlab.platypus import Paragraph, Spacer
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.colors import HexColor

    if not text:
        return

    bg = HexColor("#f0fdf4") if is_final else HexColor("#f8fafc")

    def _esc(s: str) -> str:
        return (s.replace("&", "&amp;")
                  .replace("<", "&lt;")
                  .replace(">", "&gt;")
                  .replace('"', "&quot;"))

    # Wrap baris panjang supaya tidak melebar keluar halaman
    MAX_CHAR = 110
    raw_lines = text.splitlines()
    wrapped_lines = []
    for line in raw_lines:
        if not line:
            wrapped_lines.append("")
            continue
        while len(line) > MAX_CHAR:
            wrapped_lines.append(line[:MAX_CHAR])
            line = line[MAX_CHAR:]
        wrapped_lines.append(line)

    # Potong jika terlalu panjang
    MAX_TOTAL = 300
    if len(wrapped_lines) > MAX_TOTAL:
        wrapped_lines = wrapped_lines[:MAX_TOTAL]
        wrapped_lines.append(f"... [{len(raw_lines) - MAX_TOTAL} baris dipotong untuk PDF]")

    # Bagi menjadi chunk kecil — KUNCI FIX LayoutError
    # Setiap Paragraph < 1 halaman sehingga reportlab bisa break dengan benar
    CHUNK = 35
    chunks = [wrapped_lines[i:i+CHUNK] for i in range(0, len(wrapped_lines), CHUNK)]

    chunk_style = ParagraphStyle(
        "CodeChunk",
        parent=s_code,
        backColor=bg,
        leftIndent=10,
        rightIndent=10,
        spaceBefore=0,
        spaceAfter=0,
        fontName="Courier",
        fontSize=8,
        leading=11,
        wordWrap="CJK",  # lebih agresif dalam wrap
    )

    for chunk in chunks:
        chunk_text = _esc("\n".join(chunk)).replace("\n", "<br/>")
        story.append(Paragraph(chunk_text, chunk_style))

    story.append(Spacer(1, 6))



def generate_pipeline_spec_pdf(pipe: "Pipeline") -> bytes:
    """
    Generate PDF spesifikasi pipeline (tanpa run data).
    Berguna untuk dokumentasi dan sharing pipeline design.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib.colors import HexColor, white
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable,
    )
    from reportlab.lib.enums import TA_LEFT

    PURPLE  = HexColor("#6366f1")
    DARK_BG = HexColor("#1e1e2e")
    GRAY    = HexColor("#94a3b8")
    LIGHT   = HexColor("#f1f5f9")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm, topMargin=2.5*cm, bottomMargin=2*cm,
        title=f"Pipeline Spec — {pipe.name}")
    W = A4[0] - 4*cm
    styles = getSampleStyleSheet()

    s_h1    = ParagraphStyle("H1",    parent=styles["Heading1"], fontSize=14, textColor=PURPLE)
    s_h2    = ParagraphStyle("H2",    parent=styles["Heading2"], fontSize=10, textColor=DARK_BG)
    s_body  = ParagraphStyle("Body",  parent=styles["Normal"],   fontSize=9,  leading=13)
    s_small = ParagraphStyle("Small", parent=styles["Normal"],   fontSize=7.5, textColor=GRAY)
    s_code  = ParagraphStyle("Code",  parent=styles["Code"],     fontSize=8,
                              fontName="Courier", leading=11)

    story = []

    # Header
    story.append(Paragraph(f"Pipeline Specification", s_h1))
    story.append(Paragraph(pipe.name, ParagraphStyle("Title2",
        parent=styles["Title"], fontSize=20, textColor=DARK_BG, spaceAfter=4)))
    story.append(Paragraph(pipe.description or "", ParagraphStyle("Desc",
        parent=styles["Normal"], fontSize=10, textColor=GRAY)))
    story.append(HRFlowable(width="100%", thickness=1, color=PURPLE, spaceAfter=12))

    # Meta
    meta = [
        ["Category",  pipe.category.title(),  "Version", pipe.version],
        ["Nodes",     str(len(pipe.nodes)),   "Edges",   str(len(pipe.edges))],
        ["Template",  str(pipe.is_template),  "Tags",    ", ".join(pipe.tags) or "-"],
        ["Created",   pipe.created_at[:10] if pipe.created_at else "-",
         "Updated",   pipe.updated_at[:10] if pipe.updated_at else "-"],
    ]
    mt = Table(meta, colWidths=[W*0.2, W*0.3, W*0.2, W*0.3])
    mt.setStyle(TableStyle([
        ("FONTNAME",     (0,0), (-1,-1), "Helvetica"),
        ("FONTNAME",     (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTNAME",     (2,0), (2,-1), "Helvetica-Bold"),
        ("FONTSIZE",     (0,0), (-1,-1), 8),
        ("TEXTCOLOR",    (0,0), (0,-1), PURPLE),
        ("TEXTCOLOR",    (2,0), (2,-1), PURPLE),
        ("ROWBACKGROUNDS",(0,0),(-1,-1), [LIGHT, white]),
        ("GRID",         (0,0), (-1,-1), 0.3, GRAY),
        ("TOPPADDING",   (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0), (-1,-1), 5),
        ("LEFTPADDING",  (0,0), (-1,-1), 8),
    ]))
    story.append(mt)
    story.append(Spacer(1, 16))

    # Nodes
    story.append(Paragraph("Nodes", s_h1))
    node_rows = [["#", "Node ID", "Agent", "Label", "Pass Mode", "Ethics", "Tokens"]]
    for i, n in enumerate(pipe.nodes):
        node_rows.append([
            str(i+1), n.node_id, n.agent_id, n.label,
            n.pass_mode.value if hasattr(n.pass_mode, 'value') else str(n.pass_mode),
            "yes" if n.ethics_check else "no",
            str(n.max_tokens),
        ])
    nt = Table(node_rows, colWidths=[W*0.05, W*0.15, W*0.15, W*0.25, W*0.12, W*0.1, W*0.08])
    nt.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,0),  DARK_BG),
        ("TEXTCOLOR",    (0,0), (-1,0),  white),
        ("FONTNAME",     (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTNAME",     (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE",     (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [LIGHT, white]),
        ("GRID",         (0,0), (-1,-1), 0.3, GRAY),
        ("TOPPADDING",   (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0), (-1,-1), 5),
        ("LEFTPADDING",  (0,0), (-1,-1), 6),
        ("ALIGN",        (0,0), (0,-1),  "CENTER"),
    ]))
    story.append(nt)
    story.append(Spacer(1, 12))

    # Task Templates
    story.append(Paragraph("Task Templates", s_h1))
    for i, n in enumerate(pipe.nodes):
        story.append(Paragraph(f"{i+1}. {n.label} ({n.node_id})", s_h2))
        _add_code_block(story, n.task_template or "-", s_code, s_body, W)

    # Edges
    story.append(Paragraph("Edges / Flow", s_h1))
    edge_rows = [["From Node", "Type", "To Node", "Label"]]
    for e in pipe.edges:
        edge_rows.append([
            e.from_node,
            e.edge_type.value if hasattr(e.edge_type,'value') else str(e.edge_type),
            e.to_node,
            e.label or "-",
        ])
    et = Table(edge_rows, colWidths=[W*0.3, W*0.2, W*0.3, W*0.2])
    et.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,0),  DARK_BG),
        ("TEXTCOLOR",    (0,0), (-1,0),  white),
        ("FONTNAME",     (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTNAME",     (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE",     (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [LIGHT, white]),
        ("GRID",         (0,0), (-1,-1), 0.3, GRAY),
        ("TOPPADDING",   (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0), (-1,-1), 5),
        ("LEFTPADDING",  (0,0), (-1,-1), 8),
    ]))
    story.append(et)

    def _footer(canvas_obj, doc_obj):
        canvas_obj.saveState()
        canvas_obj.setFont("Helvetica", 7)
        canvas_obj.setFillColor(GRAY)
        w, _ = A4
        canvas_obj.drawCentredString(w/2, 1.2*cm,
            f"CATERYA Agentic Enterprise  |  {pipe.pipeline_id}  |  "
            f"Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
        canvas_obj.drawRightString(w-2*cm, 1.2*cm, f"Page {doc_obj.page}")
        canvas_obj.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    buf.seek(0)
    return buf.read()
