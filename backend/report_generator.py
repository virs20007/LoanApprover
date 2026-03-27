"""
PDF report generator for investment portfolio recommendations.
Uses ReportLab to create a downloadable PDF report.
"""

import io
import math
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

# Asset colours (RGB 0-1 range) matching the frontend palette
ASSET_COLORS_RGB: dict[str, tuple[float, float, float]] = {
    "Stocks": (0.937, 0.267, 0.267),
    "Bonds": (0.133, 0.773, 0.365),
    "Cash": (0.231, 0.510, 0.965),
    "Real Estate": (0.976, 0.451, 0.086),
    "Commodities": (0.659, 0.333, 0.969),
    "Alternative Investments": (0.580, 0.639, 0.722),
}

PAGE_WIDTH, PAGE_HEIGHT = A4


def _draw_pie_chart(allocation: dict[str, float], canvas_obj: Any, x: float, y: float, radius: float) -> None:
    """Draw a simple pie chart on the canvas at (x, y) with given radius."""
    total = sum(allocation.values())
    if total == 0:
        return

    start_angle = 90.0  # start at top
    for asset, pct in sorted(allocation.items(), key=lambda kv: -kv[1]):
        if pct <= 0:
            continue
        sweep = 360.0 * (pct / total)
        r, g, b = ASSET_COLORS_RGB.get(asset, (0.5, 0.5, 0.5))
        canvas_obj.setFillColor(colors.Color(r, g, b))
        canvas_obj.setStrokeColor(colors.white)
        canvas_obj.setLineWidth(1)
        canvas_obj.wedge(x - radius, y - radius, x + radius, y + radius,
                         start_angle, sweep, fill=1)
        start_angle += sweep


def generate_pdf_report(
    country: str,
    age: int,
    monthly_income: float,
    monthly_expenses: float,
    risk_level: str,
    financial_goal: str,
    currency_symbol: str,
    allocation: dict[str, float],
    investment_amounts: dict[str, float],
    total_investable: float,
    expected_return: float,
    volatility: float,
    sharpe_ratio: float,
    ai_explanation: str,
    country_products: dict[str, str],
    market_data_source: str,
) -> bytes:
    """
    Generate a PDF report and return it as bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="AI Investment Planner — Portfolio Report",
        author="AI Investment Planner",
    )

    styles = getSampleStyleSheet()
    story = []

    # -----------------------------------------------------------------------
    # Custom styles
    # -----------------------------------------------------------------------
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontSize=22,
        textColor=colors.HexColor("#1e3a5f"),
        spaceAfter=6,
        alignment=TA_CENTER,
    )
    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.HexColor("#2563eb"),
        spaceAfter=12,
        alignment=TA_CENTER,
    )
    section_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading2"],
        fontSize=13,
        textColor=colors.HexColor("#1e3a5f"),
        spaceBefore=14,
        spaceAfter=6,
        borderPad=4,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=10,
        leading=15,
        alignment=TA_JUSTIFY,
    )
    disclaimer_style = ParagraphStyle(
        "Disclaimer",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#64748b"),
        leading=12,
        alignment=TA_CENTER,
        spaceBefore=10,
    )

    # -----------------------------------------------------------------------
    # Title section
    # -----------------------------------------------------------------------
    story.append(Paragraph("AI Investment Planner", title_style))
    story.append(Paragraph("Personalised Portfolio Report", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#2563eb")))
    story.append(Spacer(1, 0.4 * cm))

    # -----------------------------------------------------------------------
    # User Profile
    # -----------------------------------------------------------------------
    story.append(Paragraph("User Profile", section_style))
    country_display = country.title()
    profile_data = [
        ["Country", country_display, "Risk Level", risk_level],
        ["Age", str(age), "Financial Goal", financial_goal],
        ["Monthly Income", f"{currency_symbol}{monthly_income:,.2f}",
         "Monthly Expenses", f"{currency_symbol}{monthly_expenses:,.2f}"],
        ["Annual Investable", f"{currency_symbol}{total_investable:,.2f}",
         "Market Data", market_data_source.capitalize()],
    ]
    profile_table = Table(profile_data, colWidths=[3.5 * cm, 5.5 * cm, 4 * cm, 4.5 * cm])
    profile_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f0f4f8")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#f0f4f8")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    story.append(profile_table)
    story.append(Spacer(1, 0.4 * cm))

    # -----------------------------------------------------------------------
    # Portfolio Metrics
    # -----------------------------------------------------------------------
    story.append(Paragraph("Portfolio Performance Metrics", section_style))
    metrics_data = [
        ["Metric", "Value"],
        ["Expected Annual Return", f"{expected_return:.2f}%"],
        ["Expected Annual Volatility", f"{volatility:.2f}%"],
        ["Sharpe Ratio", f"{sharpe_ratio:.4f}"],
    ]
    metrics_table = Table(metrics_data, colWidths=[9 * cm, 8.5 * cm])
    metrics_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f4f8")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(metrics_table)
    story.append(Spacer(1, 0.4 * cm))

    # -----------------------------------------------------------------------
    # Portfolio Allocation Table
    # -----------------------------------------------------------------------
    story.append(Paragraph("Recommended Portfolio Allocation", section_style))
    alloc_rows = [["Asset Class", "Allocation (%)", f"Amount ({currency_symbol})"]]
    for asset, pct in sorted(allocation.items(), key=lambda kv: -kv[1]):
        amount = investment_amounts.get(asset, 0.0)
        alloc_rows.append([asset, f"{pct:.0f}%", f"{currency_symbol}{amount:,.2f}"])

    alloc_table = Table(alloc_rows, colWidths=[8 * cm, 5 * cm, 4.5 * cm])
    alloc_style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
    ]
    # Colour-code asset rows
    for row_idx, (asset, _) in enumerate(sorted(allocation.items(), key=lambda kv: -kv[1]), start=1):
        r, g, b = ASSET_COLORS_RGB.get(asset, (0.5, 0.5, 0.5))
        alloc_style.append(
            ("LEFTPADDING", (0, row_idx), (0, row_idx), 10)
        )
        alloc_style.append(
            ("FONTNAME", (1, row_idx), (1, row_idx), "Helvetica-Bold")
        )
    alloc_table.setStyle(TableStyle(alloc_style))
    story.append(alloc_table)
    story.append(Spacer(1, 0.4 * cm))

    # -----------------------------------------------------------------------
    # AI Explanation
    # -----------------------------------------------------------------------
    if ai_explanation:
        story.append(Paragraph("AI-Generated Investment Explanation", section_style))
        for para in ai_explanation.split("\n\n"):
            para = para.strip()
            if para:
                story.append(Paragraph(para, body_style))
                story.append(Spacer(1, 0.2 * cm))
        story.append(Spacer(1, 0.2 * cm))

    # -----------------------------------------------------------------------
    # Country-specific products
    # -----------------------------------------------------------------------
    if country_products:
        story.append(Paragraph(
            f"Recommended Investment Products — {country_display}",
            section_style
        ))
        prod_rows = [["Product", "Description"]]
        for prod_name, prod_desc in country_products.items():
            prod_rows.append([prod_name, prod_desc])

        prod_table = Table(prod_rows, colWidths=[5 * cm, 12.5 * cm])
        prod_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(prod_table)
        story.append(Spacer(1, 0.4 * cm))

    # -----------------------------------------------------------------------
    # Disclaimer
    # -----------------------------------------------------------------------
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0")))
    story.append(Paragraph(
        "DISCLAIMER: This report is generated for educational purposes only and does not "
        "constitute professional financial advice. Investment decisions involve risk, and past "
        "performance is not indicative of future results. Always consult a qualified financial "
        "advisor before making any investment decisions.",
        disclaimer_style
    ))

    doc.build(story)
    return buffer.getvalue()
