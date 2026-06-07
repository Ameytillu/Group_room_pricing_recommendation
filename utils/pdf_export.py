"""
pdf_export.py
─────────────
Generates a clean one-page PDF pricing summary that the revenue manager
can attach to a group proposal or email to the sales team.
Uses only the reportlab library (pure Python, no system dependencies).
"""

from __future__ import annotations
from io import BytesIO
from datetime import date
from typing import Any

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


# ── Brand colours ─────────────────────────────────────────────────────────────
NAVY   = colors.HexColor("#1a3a5c")
BLUE   = colors.HexColor("#2563a8")
GREEN  = colors.HexColor("#15803D")
ORANGE = colors.HexColor("#EA580C")
LIGHT  = colors.HexColor("#F8F9FB")
GRAY   = colors.HexColor("#64748B")
LGRAY  = colors.HexColor("#E2E8F0")


def generate_pdf_report(
    sales_data: dict[str, Any],
    market_data: dict[str, Any],
    results: dict[str, Any],
) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()

    def s(name, **kw):
        return ParagraphStyle(name, parent=styles["Normal"], **kw)

    h1   = s("H1",   fontSize=20, textColor=colors.white,  fontName="Helvetica-Bold", alignment=TA_LEFT,   leading=24)
    h2   = s("H2",   fontSize=11, textColor=NAVY,           fontName="Helvetica-Bold", alignment=TA_LEFT,   leading=14, spaceAfter=4)
    body = s("body", fontSize=9,  textColor=colors.HexColor("#222222"), fontName="Helvetica", leading=13)
    sm   = s("sm",   fontSize=8,  textColor=GRAY,           fontName="Helvetica",      leading=11)
    bold = s("bold", fontSize=9,  textColor=colors.HexColor("#222222"), fontName="Helvetica-Bold", leading=13)
    ctr  = s("ctr",  fontSize=9,  alignment=TA_CENTER)
    rt   = s("rt",   fontSize=8,  textColor=GRAY, alignment=TA_RIGHT)

    story = []

    # ── Header banner ──────────────────────────────────────────────────────
    header_data = [[
        Paragraph("<font color='white'><b>🏨  Group Pricing Report</b></font>", h1),
        Paragraph(
            f"<font color='white' size='8'>Generated: {date.today().strftime('%B %d, %Y')}</font>",
            s("hdr_rt", fontSize=8, textColor=colors.white, alignment=TA_RIGHT, fontName="Helvetica")
        )
    ]]
    header_table = Table(header_data, colWidths=[4.5 * inch, 2.5 * inch])
    header_table.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, -1), NAVY),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",  (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LEFTPADDING", (0, 0), (0, -1), 16),
        ("RIGHTPADDING", (-1, 0), (-1, -1), 16),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.2 * inch))

    # ── Group details ──────────────────────────────────────────────────────
    story.append(Paragraph("Group Details", h2))
    story.append(HRFlowable(width="100%", thickness=1.5, color=BLUE, spaceAfter=6))

    sd = sales_data
    detail_rows = [
        ["Group / Company",  sd["group_name"],         "Sales Contact",  sd.get("contact_name", "—")],
        ["Arrival Date",     sd["arrival_date"].strftime("%B %d, %Y"),
         "Departure Date",   sd["departure_date"].strftime("%B %d, %Y")],
        ["Room Block",       f"{sd['room_block']} rooms/night",
         "Nights",           str(sd["nights"])],
        ["Total Room-Nights", str(results["total_room_nights"]),
         "Meal Plan",        sd.get("meal_plan", "—")],
    ]
    det_table = Table(detail_rows, colWidths=[1.5*inch, 2*inch, 1.5*inch, 2*inch])
    det_table.setStyle(TableStyle([
        ("FONTNAME",    (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE",    (0, 0), (-1, -1), 8.5),
        ("FONTNAME",    (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",    (2, 0), (2, -1), "Helvetica-Bold"),
        ("TEXTCOLOR",   (0, 0), (0, -1), NAVY),
        ("TEXTCOLOR",   (2, 0), (2, -1), NAVY),
        ("BACKGROUND",  (0, 0), (-1, -1), LIGHT),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [LIGHT, colors.white]),
        ("TOPPADDING",  (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("GRID",        (0, 0), (-1, -1), 0.3, LGRAY),
    ]))
    story.append(det_table)
    story.append(Spacer(1, 0.18 * inch))

    # ── Rate recommendations ───────────────────────────────────────────────
    story.append(Paragraph("Rate Recommendations", h2))
    story.append(HRFlowable(width="100%", thickness=1.5, color=BLUE, spaceAfter=6))

    r = results
    rate_rows = [
        ["Scenario", "Rate / Night", "Total Group Revenue", "vs. Displaced Transient Rev"],
        ["🟢  Minimum Acceptable",
         f"${r['rate_min']:,.0f}",
         f"${r['group_rev_min']:,.0f}",
         f"${r['group_rev_min'] - r['displaced_revenue']:+,.0f}"],
        ["🔵  Recommended Rate",
         f"${r['rate_rec']:,.0f}",
         f"${r['group_rev_rec']:,.0f}",
         f"${r['group_rev_rec'] - r['displaced_revenue']:+,.0f}"],
        ["🔴  Stretch Rate",
         f"${r['rate_stretch']:,.0f}",
         f"${r['group_rev_str']:,.0f}",
         f"${r['group_rev_str'] - r['displaced_revenue']:+,.0f}"],
    ]
    rate_table = Table(rate_rows, colWidths=[2.3*inch, 1.2*inch, 1.8*inch, 1.7*inch])
    rate_table.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
        ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, -1), 8.5),
        ("FONTNAME",    (0, 1), (-1, -1), "Helvetica"),
        ("FONTNAME",    (1, 1), (1, -1), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [LIGHT, colors.white, colors.HexColor("#FFF7ED")]),
        ("TOPPADDING",  (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("GRID",        (0, 0), (-1, -1), 0.3, LGRAY),
        ("ALIGN",       (1, 0), (-1, -1), "CENTER"),
    ]))
    story.append(rate_table)
    story.append(Spacer(1, 0.18 * inch))

    # ── Key metrics ────────────────────────────────────────────────────────
    story.append(Paragraph("Market & Displacement Analysis", h2))
    story.append(HRFlowable(width="100%", thickness=1.5, color=BLUE, spaceAfter=6))

    md = market_data
    metric_rows = [
        ["Projected Transient ADR",  f"${r['proj_transient_adr']:,.2f}",
         "Displacement Risk",         r["displacement_risk"]],
        ["3-Yr Avg Occupancy",        f"{r['avg_hist_occ']:.1f}%",
         "Displaced Room-Nights",     str(r["displaced_room_nights"])],
        ["3-Yr Avg ADR",              f"${r['avg_hist_adr']:,.2f}",
         "Displaced Rev (transient)", f"${r['displaced_revenue']:,.0f}"],
        ["Historical YoY ADR Trend",  f"{r['yoy_trend']:+.1f}%",
         "Manager Growth Assumption", f"{md['adr_growth_pct']:+.1f}%"],
        ["STR MPI",                   f"{md['str_mpi']:.1f}",
         "STR ARI",                   f"{md['str_ari']:.1f}"],
        ["Pace vs STLY",              f"{r['pace_variance']:+.0f} rooms",
         "Forecasted Occupancy",      f"{md['curr_occ']:.1f}%"],
    ]
    met_table = Table(metric_rows, colWidths=[1.8*inch, 1.4*inch, 1.8*inch, 2*inch])
    met_table.setStyle(TableStyle([
        ("FONTNAME",    (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE",    (0, 0), (-1, -1), 8.5),
        ("FONTNAME",    (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",    (2, 0), (2, -1), "Helvetica-Bold"),
        ("TEXTCOLOR",   (0, 0), (0, -1), NAVY),
        ("TEXTCOLOR",   (2, 0), (2, -1), NAVY),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [LIGHT, colors.white]),
        ("TOPPADDING",  (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("GRID",        (0, 0), (-1, -1), 0.3, LGRAY),
    ]))
    story.append(met_table)
    story.append(Spacer(1, 0.15 * inch))

    # ── Displacement alert ─────────────────────────────────────────────────
    if r["displacement_risk"] == "HIGH":
        alert_color = colors.HexColor("#FFF1F2")
        border_color = colors.HexColor("#E11D48")
        alert_text = (
            f"⚠️  <b>High Displacement Risk:</b> Accepting this group at minimum rate displaces "
            f"an estimated <b>{r['displaced_room_nights']} transient room-nights</b> "
            f"(${r['displaced_revenue']:,.0f} transient revenue). "
            f"Recommend negotiating at or above the Recommended Rate."
        )
    else:
        alert_color = colors.HexColor("#F0FDF4")
        border_color = GREEN
        alert_text = (
            f"✅  <b>Low Displacement Risk:</b> Current occupancy forecast ({md['curr_occ']:.1f}%) "
            f"provides sufficient transient headroom. Group can be accommodated with minimal displacement impact."
        )

    alert_data = [[Paragraph(alert_text, s("alert", fontSize=8.5, fontName="Helvetica", leading=12))]]
    alert_table = Table(alert_data, colWidths=[7 * inch])
    alert_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), alert_color),
        ("LINEAFTER",     (0, 0), (0, -1), 3, border_color),
        ("LINEBEFORE",    (0, 0), (0, -1), 3, border_color),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
    ]))
    story.append(alert_table)
    story.append(Spacer(1, 0.15 * inch))

    # ── Notes ──────────────────────────────────────────────────────────────
    if sd.get("special_notes"):
        story.append(Paragraph("Special Notes / Concessions", h2))
        story.append(HRFlowable(width="100%", thickness=1, color=LGRAY, spaceAfter=4))
        story.append(Paragraph(sd["special_notes"], body))
        story.append(Spacer(1, 0.1 * inch))

    # ── Footer ─────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=LGRAY))
    story.append(Spacer(1, 0.05 * inch))
    story.append(Paragraph(
        "This report is generated by the Group Pricing Intelligence Tool. "
        "Rates are recommendations based on historical data and managerial inputs — "
        "final pricing decisions remain with the Revenue Manager.",
        s("footer", fontSize=7, textColor=GRAY, alignment=TA_CENTER)
    ))

    doc.build(story)
    return buf.getvalue()
