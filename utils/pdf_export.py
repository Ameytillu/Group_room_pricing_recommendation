"""
pdf_export.py
-------------
PDF export for the daily group displacement analysis.
"""

from __future__ import annotations

from datetime import date
from html import escape
from io import BytesIO
from typing import Any

from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


NAVY = colors.HexColor("#1a3a5c")
BLUE = colors.HexColor("#2563a8")
GREEN = colors.HexColor("#15803D")
LIGHT = colors.HexColor("#F8F9FB")
GRAY = colors.HexColor("#64748B")
LGRAY = colors.HexColor("#E2E8F0")


def _fmt_date(value: Any) -> str:
    if hasattr(value, "strftime"):
        return value.strftime("%m/%d/%Y")
    return str(value)


def _money(value: Any) -> str:
    return f"${float(value or 0):,.0f}"


def _safe_text(value: Any) -> str:
    text = str(value or "-").strip() or "-"
    return escape(text)


def _ancillary_summary(ancillary_data: dict[str, Any] | None) -> dict[str, Any]:
    data = ancillary_data or {}
    banquet_revenue = float(data.get("banquet_revenue", 0.0) or 0.0)
    fb_items = []
    for item in data.get("fb_items", []):
        attendees = int(item.get("attendees", 0) or 0)
        price_per_head = float(item.get("price_per_head", 0.0) or 0.0)
        revenue = float(item.get("revenue", attendees * price_per_head) or 0.0)
        fb_items.append({
            "item": item.get("item", ""),
            "attendees": attendees,
            "price_per_head": price_per_head,
            "revenue": revenue,
            "notes": item.get("notes", ""),
        })
    fb_revenue = sum(item["revenue"] for item in fb_items)
    return {
        "banquet_required": data.get("banquet_required", "No"),
        "banquet_count": int(data.get("banquet_count", 0) or 0),
        "banquet_descriptions": data.get("banquet_descriptions", ""),
        "banquet_revenue": banquet_revenue,
        "banquet_notes": data.get("banquet_notes", ""),
        "fb_required": data.get("fb_required", "No"),
        "fb_items": fb_items,
        "fb_revenue": fb_revenue,
        "total_ancillary_revenue": banquet_revenue + fb_revenue,
    }


def _revenue_mix_chart(room_revenue: float, fb_revenue: float, banquet_revenue: float) -> Drawing:
    drawing = Drawing(360, 180)
    revenue_mix_data = [
        ("Rooms Revenue", "Rooms", room_revenue, BLUE),
        ("F&B Revenue", "F&B", fb_revenue, GREEN),
        ("Banquet Hall Revenue", "Banquet", banquet_revenue, colors.HexColor("#EA580C")),
    ]
    revenue_mix_data = [row for row in revenue_mix_data if row[2] > 0]
    if not revenue_mix_data:
        revenue_mix_data = [("No revenue", "No revenue", 1, LGRAY)]

    pie = Pie()
    pie.x = 30
    pie.y = 20
    pie.width = 140
    pie.height = 140
    pie.data = [row[2] for row in revenue_mix_data]
    pie.labels = [row[1] for row in revenue_mix_data]
    pie.slices.strokeWidth = 0.5
    for idx, row in enumerate(revenue_mix_data):
        pie.slices[idx].fillColor = row[3]
    drawing.add(pie)

    y = 125
    for label, _, value, color in revenue_mix_data:
        drawing.add(Rect(205, y - 2, 8, 8, fillColor=color, strokeColor=color))
        display_value = _money(value) if label != "No revenue" else "$0"
        drawing.add(String(220, y, f"{label}: {display_value}", fontSize=8, fillColor=NAVY))
        y -= 22
    return drawing


def generate_pdf_report(
    sales_data: dict[str, Any],
    market_data: dict[str, Any],
    results: dict[str, Any],
    ancillary_data: dict[str, Any] | None = None,
) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(letter),
        leftMargin=0.45 * inch,
        rightMargin=0.45 * inch,
        topMargin=0.45 * inch,
        bottomMargin=0.45 * inch,
    )

    styles = getSampleStyleSheet()

    def s(name, **kw):
        return ParagraphStyle(name, parent=styles["Normal"], **kw)

    h1 = s("H1", fontSize=18, textColor=colors.white, fontName="Helvetica-Bold", alignment=TA_LEFT, leading=22)
    h2 = s("H2", fontSize=11, textColor=NAVY, fontName="Helvetica-Bold", alignment=TA_LEFT, leading=14, spaceAfter=4)
    sm = s("sm", fontSize=7, textColor=GRAY, fontName="Helvetica", leading=9)
    footer = s("footer", fontSize=7, textColor=GRAY, alignment=TA_CENTER)

    story = []

    header = Table([[
        Paragraph("<font color='white'><b>Group Pricing Daily Displacement Report</b></font>", h1),
        Paragraph(
            f"<font color='white' size='8'>Generated: {date.today().strftime('%B %d, %Y')}</font>",
            s("hdr_rt", fontSize=8, textColor=colors.white, alignment=TA_RIGHT, fontName="Helvetica"),
        ),
    ]], colWidths=[7.0 * inch, 3.0 * inch])
    header.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
    ]))
    story.append(header)
    story.append(Spacer(1, 0.16 * inch))

    sd = sales_data
    md = market_data
    r = results
    ancillary = _ancillary_summary(ancillary_data)
    room_revenue = float(r["group_rev_recommended"])
    banquet_revenue = ancillary["banquet_revenue"]
    fb_revenue = ancillary["fb_revenue"]
    total_ancillary_revenue = ancillary["total_ancillary_revenue"]
    total_group_revenue_with_ancillaries = room_revenue + total_ancillary_revenue
    total_net_revenue_with_ancillaries = float(r["net_revenue_position"]) + total_ancillary_revenue

    story.append(Paragraph("Group Details", h2))
    story.append(HRFlowable(width="100%", thickness=1.3, color=BLUE, spaceAfter=5))
    detail_rows = [
        ["Group / Company", sd["group_name"], "Sales Contact", sd.get("contact_name", "-")],
        ["Arrival Date", sd["arrival_date"].strftime("%B %d, %Y"), "Departure Date", sd["departure_date"].strftime("%B %d, %Y")],
        ["Stay Nights", str(sd["nights"]), "Total Room-Nights", str(r["total_room_nights"])],
        ["Recommended Rate", f"${r['recommended_rate']:,.0f}", "Meal Plan", sd.get("meal_plan", "-")],
    ]
    detail_table = Table(detail_rows, colWidths=[1.35 * inch, 3.2 * inch, 1.35 * inch, 3.2 * inch])
    detail_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 0), (0, -1), NAVY),
        ("TEXTCOLOR", (2, 0), (2, -1), NAVY),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [LIGHT, colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.25, LGRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(detail_table)
    story.append(Spacer(1, 0.12 * inch))

    story.append(Paragraph("Summary", h2))
    story.append(HRFlowable(width="100%", thickness=1.3, color=BLUE, spaceAfter=5))
    summary_rows = [
        ["Weighted PMS Forecast ADR", f"${r['weighted_pms_forecast_adr']:,.0f}", "Rate vs PMS Forecast ADR", f"{r['rate_vs_forecast_adr_pct']:.1f}%"],
        ["Group Revenue", f"${r['group_rev_recommended']:,.0f}", "Displaced Revenue", f"${r['displaced_revenue']:,.0f}"],
        ["Net Revenue Position", f"${r['net_revenue_position']:+,.0f}", "Displacement Risk", r["displacement_risk"]],
        ["3-Yr Avg Group ADR", f"${r['avg_hist_adr']:,.0f}", "3-Yr Avg Group Occupancy", f"{r['avg_hist_occ']:.1f}%"],
        ["Pace vs STLY", f"{r['pace_variance']:+.0f} rooms", "STR Comp Occupancy", f"{md['str_comp_occ']:.1f}%"],
        ["MPI / ARI", f"{md['str_mpi']:.1f} / {md['str_ari']:.1f}", "Desired Group ADR Growth", f"{md['adr_growth_pct']:+.1f}%"],
    ]
    summary_table = Table(summary_rows, colWidths=[1.7 * inch, 2.1 * inch, 1.7 * inch, 2.1 * inch])
    summary_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 0), (0, -1), NAVY),
        ("TEXTCOLOR", (2, 0), (2, -1), NAVY),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [LIGHT, colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.25, LGRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.12 * inch))

    story.append(Paragraph("Ancillary Revenue", h2))
    story.append(HRFlowable(width="100%", thickness=1.3, color=BLUE, spaceAfter=5))
    ancillary_rows = [
        ["Banquet hall required", ancillary["banquet_required"], "Number of banquet halls", str(ancillary["banquet_count"])],
        ["Banquet hall names/descriptions", Paragraph(_safe_text(ancillary["banquet_descriptions"]), sm), "Banquet hall revenue", _money(banquet_revenue)],
        ["F&B required", ancillary["fb_required"], "F&B revenue", _money(fb_revenue)],
        ["Banquet notes", Paragraph(_safe_text(ancillary["banquet_notes"]), sm), "", ""],
    ]
    ancillary_table = Table(ancillary_rows, colWidths=[1.55 * inch, 3.0 * inch, 1.55 * inch, 3.0 * inch])
    ancillary_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 0), (0, -1), NAVY),
        ("TEXTCOLOR", (2, 0), (2, -1), NAVY),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [LIGHT, colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.25, LGRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(ancillary_table)
    story.append(Spacer(1, 0.12 * inch))

    story.append(Paragraph("F&amp;B Breakdown", h2))
    story.append(HRFlowable(width="100%", thickness=1.3, color=BLUE, spaceAfter=5))
    fb_rows = [["F&B Item", "Attendees", "Price Per Head", "Revenue", "Notes"]]
    if ancillary["fb_items"]:
        for item in ancillary["fb_items"]:
            fb_rows.append([
                _safe_text(item["item"]),
                f"{item['attendees']:,}",
                _money(item["price_per_head"]),
                _money(item["revenue"]),
                Paragraph(_safe_text(item["notes"]), sm),
            ])
    else:
        fb_rows.append(["-", "0", "$0", "$0", "-"])
    fb_table = Table(
        fb_rows,
        colWidths=[1.4 * inch, 0.9 * inch, 1.1 * inch, 1.0 * inch, 4.0 * inch],
        repeatRows=1,
    )
    fb_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("ALIGN", (1, 0), (3, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [LIGHT, colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.25, LGRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(fb_table)
    story.append(Spacer(1, 0.12 * inch))

    story.append(Paragraph("Total Group Revenue", h2))
    story.append(HRFlowable(width="100%", thickness=1.3, color=BLUE, spaceAfter=5))
    total_rows = [
        ["Room Revenue", _money(room_revenue), "Banquet Hall Revenue", _money(banquet_revenue)],
        ["F&B Revenue", _money(fb_revenue), "Total Ancillary Revenue", _money(total_ancillary_revenue)],
        ["Total Group Revenue Including Ancillaries", _money(total_group_revenue_with_ancillaries), "Displaced Revenue", _money(r["displaced_revenue"])],
        ["Total Net Revenue Including Ancillaries", f"${total_net_revenue_with_ancillaries:+,.0f}", "", ""],
    ]
    total_table = Table(total_rows, colWidths=[2.35 * inch, 1.45 * inch, 2.35 * inch, 1.45 * inch])
    total_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 0), (0, -1), NAVY),
        ("TEXTCOLOR", (2, 0), (2, -1), NAVY),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [LIGHT, colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.25, LGRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(total_table)
    story.append(Spacer(1, 0.08 * inch))
    story.append(Paragraph(
        "Room revenue and displacement are calculated using the existing PMS forecast logic. Banquet and F&amp;B revenue are added separately as ancillary group revenue and do not affect room displacement.",
        sm,
    ))
    story.append(Spacer(1, 0.12 * inch))

    story.append(Paragraph("Daily Displacement Table", h2))
    story.append(HRFlowable(width="100%", thickness=1.3, color=BLUE, spaceAfter=5))
    daily_rows = [[
        "Stay Date", "Group", "PMS Rooms", "Displaced", "PMS ADR",
        "Indicated Group", "Group Rev", "Disp Rev", "Net",
    ]]
    for row in r["daily_results"]:
        daily_rows.append([
            _fmt_date(row["stay_date"]),
            row["group_rooms"],
            row["pms_forecast_rooms"],
            row["displaced_rooms"],
            f"${row['pms_forecast_adr']:,.0f}",
            f"${row['daily_indicated_group_rate']:,.0f}",
            f"${row['group_revenue']:,.0f}",
            f"${row['displaced_revenue']:,.0f}",
            f"${row['net_revenue_position']:+,.0f}",
        ])
    daily_table = Table(
        daily_rows,
        colWidths=[0.95 * inch, 0.6 * inch, 0.75 * inch, 0.75 * inch, 0.75 * inch,
                   1.05 * inch, 0.95 * inch, 0.9 * inch, 0.85 * inch],
        repeatRows=1,
    )
    daily_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [LIGHT, colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.25, LGRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(daily_table)
    story.append(Spacer(1, 0.12 * inch))

    story.append(Paragraph("Revenue Mix Chart", h2))
    story.append(HRFlowable(width="100%", thickness=1.3, color=BLUE, spaceAfter=5))
    story.append(_revenue_mix_chart(room_revenue, fb_revenue, banquet_revenue))
    story.append(Spacer(1, 0.12 * inch))

    if sd.get("special_notes"):
        story.append(Paragraph("Special Notes / Concessions", h2))
        story.append(Paragraph(sd["special_notes"], sm))
        story.append(Spacer(1, 0.08 * inch))

    story.append(HRFlowable(width="100%", thickness=0.5, color=LGRAY))
    story.append(Spacer(1, 0.05 * inch))
    story.append(Paragraph(
        "Displacement is calculated per stay date as max((PMS forecast rooms + daily group rooms) - hotel capacity, 0). Displaced revenue equals displaced rooms times PMS forecast ADR.",
        footer,
    ))

    doc.build(story)
    return buf.getvalue()
