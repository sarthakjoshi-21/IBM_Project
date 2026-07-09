"""
Export Blueprint — /api/export
Generates a downloadable, print-ready PDF itinerary travel guide
using ReportLab.
"""
import os
import logging
from datetime import datetime
from io import BytesIO

from flask import Blueprint, jsonify, session, send_file, current_app

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

export_bp = Blueprint("export", __name__)
logger = logging.getLogger(__name__)

# ── Colour palette matching the dark-mode UI ──────────────────────────────────
DEEP_RED = colors.HexColor("#c0392b")
MATTE_BLACK = colors.HexColor("#1a1a1a")
LIGHT_GREY = colors.HexColor("#f5f5f5")
DARK_GREY = colors.HexColor("#333333")


def _build_pdf(trip: dict) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Title"],
        fontSize=22,
        textColor=DEEP_RED,
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
    )
    subtitle_style = ParagraphStyle(
        "SubTitle",
        parent=styles["Normal"],
        fontSize=11,
        textColor=DARK_GREY,
        alignment=TA_CENTER,
        spaceAfter=14,
    )
    heading_style = ParagraphStyle(
        "Heading",
        parent=styles["Heading2"],
        fontSize=13,
        textColor=DEEP_RED,
        spaceBefore=12,
        spaceAfter=4,
        fontName="Helvetica-Bold",
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=9.5,
        textColor=DARK_GREY,
        leading=15,
        spaceAfter=6,
    )
    meta_style = ParagraphStyle(
        "Meta",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.grey,
        alignment=TA_CENTER,
    )

    params = trip.get("params", {})
    itinerary_text = trip.get("itinerary", "No itinerary content available.")
    created_at = trip.get("created_at", datetime.utcnow().isoformat())

    story = []

    # ── Cover block ───────────────────────────────────────────────────────────
    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph("VoyageIntel AI", title_style))
    story.append(Paragraph("Travel Intelligence &amp; Itinerary Guide", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=DEEP_RED, spaceAfter=10))

    # ── Trip metadata table ───────────────────────────────────────────────────
    meta_data = [
        ["Trip ID", trip.get("id", "—")],
        ["Generated", created_at[:19].replace("T", " ") + " UTC"],
        ["Destination", params.get("destination", "—")],
        ["Origin", params.get("origin", "—")],
        ["Duration", f"{params.get('duration_days', '—')} days"],
        ["Persona", params.get("persona", "—").title()],
        ["Group Size", str(params.get("group_size", "—"))],
        ["Budget", f"{params.get('budget_currency','₹')}{params.get('budget_total','flexible')}"],
        ["Optimisation", params.get("optimisation_mode", "balanced").replace("_", " ").title()],
    ]
    meta_table = Table(meta_data, colWidths=[4 * cm, 12 * cm])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), LIGHT_GREY),
        ("TEXTCOLOR", (0, 0), (0, -1), DEEP_RED),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (1, 0), (1, -1), [colors.white, LIGHT_GREY]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 0.6 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#dddddd"), spaceAfter=10))

    # ── Itinerary content ─────────────────────────────────────────────────────
    story.append(Paragraph("Full Itinerary", heading_style))

    for line in itinerary_text.split("\n"):
        line = line.strip()
        if not line:
            story.append(Spacer(1, 0.15 * cm))
            continue
        if line.startswith("## ") or line.startswith("# "):
            clean = line.lstrip("#").strip()
            story.append(Paragraph(clean, heading_style))
        elif line.startswith("**") and line.endswith("**"):
            story.append(Paragraph(f"<b>{line[2:-2]}</b>", body_style))
        elif line.startswith("- ") or line.startswith("* "):
            story.append(Paragraph(f"• {line[2:]}", body_style))
        else:
            safe_line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            story.append(Paragraph(safe_line, body_style))

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 1 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#dddddd"), spaceAfter=6))
    story.append(Paragraph(
        "Generated by VoyageIntel AI &bull; Powered by IBM Watsonx.ai &amp; Granite",
        meta_style,
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer


@export_bp.get("/<trip_id>/pdf")
def export_pdf(trip_id: str):
    trips = session.get("trips", [])
    trip = next((t for t in trips if t["id"] == trip_id), None)
    if not trip:
        return jsonify({"error": "Trip not found"}), 404

    try:
        pdf_buffer = _build_pdf(trip)
    except Exception as exc:
        logger.exception("PDF generation failed for trip %s: %s", trip_id, exc)
        return jsonify({"error": "PDF generation failed"}), 500

    dest = trip["params"].get("destination", "trip").replace(" ", "_")
    filename = f"VoyageIntel_{dest}_{trip_id}.pdf"

    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf",
    )
