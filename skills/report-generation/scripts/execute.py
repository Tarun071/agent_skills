"""Report-generation implementation owned by the report-generation skill."""

import re
from html.parser import HTMLParser
from pathlib import Path
from uuid import uuid4

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


SKILL_ROOT = Path(__file__).resolve().parent.parent
HTML_TEMPLATE = SKILL_ROOT / "templates" / "report.html"
CSS_TEMPLATE = SKILL_ROOT / "templates" / "report.css"


def _format_currency(value):
    return f"${float(value):,.2f}"


def _hex_color(value):
    return colors.HexColor(value)


def _css_variables(css_text):
    return {
        name.strip(): value.strip()
        for name, value in re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", css_text)
    }


def _replace_placeholders(template, values):
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", str(value))
    return template


def _strip_html(html_text):
    class TextExtractor(HTMLParser):
        def __init__(self):
            super().__init__()
            self.parts = []

        def handle_data(self, data):
            if data.strip():
                self.parts.append(data.strip())

    extractor = TextExtractor()
    extractor.feed(html_text)
    return extractor.parts


def generate_sales_report(analysis, insights, output_dir):
    if not isinstance(analysis, dict):
        raise ValueError("Sales analysis must be provided as a dictionary.")

    required_keys = (
        "total_revenue",
        "total_quantity",
        "product_performance",
        "region_performance",
        "highest_performing_product",
        "lowest_performing_product",
    )
    missing_keys = [key for key in required_keys if key not in analysis]
    if missing_keys:
        raise ValueError(f"Missing analysis fields: {', '.join(missing_keys)}")

    if insights is None:
        raise ValueError("Business insights are required.")

    if isinstance(insights, str):
        insight_items = [insights] if insights.strip() else []
    elif isinstance(insights, (list, tuple)):
        insight_items = [str(item) for item in insights if str(item).strip()]
    else:
        raise ValueError("Business insights must be a string or list.")

    if not HTML_TEMPLATE.is_file():
        raise ValueError("Report HTML template was not found.")
    if not CSS_TEMPLATE.is_file():
        raise ValueError("Report CSS template was not found.")

    html_template = HTML_TEMPLATE.read_text(encoding="utf-8")
    css_text = CSS_TEMPLATE.read_text(encoding="utf-8")
    css = _css_variables(css_text)

    page_width = float(css["--page-width"])
    page_height = float(css["--page-height"])

    styles = {
        "title": ParagraphStyle(
            "Title",
            fontName=css["--title-font"],
            fontSize=float(css["--title-size"]),
            textColor=_hex_color(css["--title-color"]),
            leading=float(css["--title-leading"]),
            alignment=TA_LEFT,
            spaceAfter=float(css["--title-space-after"]),
        ),
        "heading": ParagraphStyle(
            "Heading",
            fontName=css["--heading-font"],
            fontSize=float(css["--heading-size"]),
            textColor=_hex_color(css["--heading-color"]),
            leading=float(css["--heading-leading"]),
            alignment=TA_LEFT,
            spaceAfter=float(css["--heading-space-after"]),
        ),
        "body": ParagraphStyle(
            "Body",
            fontName=css["--body-font"],
            fontSize=float(css["--body-size"]),
            textColor=_hex_color(css["--body-color"]),
            leading=float(css["--body-leading"]),
            alignment=TA_LEFT,
            spaceAfter=float(css["--body-space-after"]),
        ),
    }

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    pdf_path = destination / f"sales_report_{uuid4().hex}.pdf"

    document = SimpleDocTemplate(
        str(pdf_path),
        pagesize=(page_width, page_height),
        leftMargin=float(css["--margin-left"]),
        rightMargin=float(css["--margin-right"]),
        topMargin=float(css["--margin-top"]),
        bottomMargin=float(css["--margin-bottom"]),
    )

    template_values = {
        "title": "Sales Performance Report",
        "summary_heading": "Reporting Summary",
        "summary_text": "This report summarizes revenue and quantity performance across products and regions.",
        "product_heading": "Product Performance",
        "region_heading": "Regional Performance",
        "insights_heading": "Business Insights",
        "recommendations_heading": "Recommendations",
    }
    rendered_template = _replace_placeholders(html_template, template_values)
    template_parts = _strip_html(rendered_template)

    content = []
    title = template_parts[0] if template_parts else template_values["title"]
    content.append(Paragraph(title, styles["title"]))
    content.append(Spacer(1, float(css["--title-space-after"])))

    content.append(Paragraph(template_values["summary_heading"], styles["heading"]))
    content.append(Paragraph(template_values["summary_text"], styles["body"]))
    content.append(Spacer(1, float(css["--section-spacing"])))

    table_style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _hex_color(css["--table-header-background"])),
        ("TEXTCOLOR", (0, 0), (-1, 0), _hex_color(css["--table-header-color"])),
        ("GRID", (0, 0), (-1, -1), float(css["--table-grid-width"]), _hex_color(css["--table-grid-color"])),
        ("FONTNAME", (0, 0), (-1, 0), css["--table-header-font"]),
        ("FONTNAME", (0, 1), (-1, -1), css["--table-body-font"]),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
            colors.white,
            _hex_color(css["--table-alternate-background"]),
        ]),
        ("TOPPADDING", (0, 0), (-1, 0), float(css["--table-header-top-padding"])),
        ("BOTTOMPADDING", (0, 0), (-1, 0), float(css["--table-header-bottom-padding"])),
        ("TOPPADDING", (0, 1), (-1, -1), float(css["--table-body-top-padding"])),
        ("BOTTOMPADDING", (0, 1), (-1, -1), float(css["--table-body-bottom-padding"])),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
    ])

    summary_rows = [
        ["Metric", "Value"],
        ["Total Revenue", _format_currency(analysis["total_revenue"])],
        ["Total Quantity", str(analysis["total_quantity"])],
        ["Highest-Performing Product", str(analysis["highest_performing_product"])],
        ["Lowest-Performing Product", str(analysis["lowest_performing_product"])],
    ]
    summary_table = Table(summary_rows, colWidths=[220, 220])
    summary_table.setStyle(table_style)
    content.append(summary_table)
    content.append(Spacer(1, float(css["--section-spacing"])))

    def performance_table(title, performance):
        rows = [[title, "Revenue", "Quantity"]]
        for name, metrics in performance.items():
            if not isinstance(metrics, dict):
                raise ValueError(f"Invalid performance metrics for {name}.")
            rows.append([
                str(name),
                _format_currency(metrics.get("revenue", 0)),
                str(metrics.get("quantity", 0)),
            ])

        table = Table(rows, colWidths=[220, 110, 110], repeatRows=1)
        table.setStyle(table_style)
        return [
            Paragraph(title, styles["heading"]),
            Spacer(1, float(css["--table-spacing"])),
            table,
            Spacer(1, float(css["--section-spacing"])),
        ]

    content.extend(performance_table(template_values["product_heading"], analysis["product_performance"]))
    content.extend(performance_table(template_values["region_heading"], analysis["region_performance"]))

    content.append(Paragraph(template_values["insights_heading"], styles["heading"]))
    if insight_items:
        for insight in insight_items:
            content.append(Paragraph(f"• {insight}", styles["body"]))
    else:
        content.append(Paragraph("No business insights were provided.", styles["body"]))

    content.append(Spacer(1, float(css["--insights-spacing"])))
    content.append(Paragraph(template_values["recommendations_heading"], styles["heading"]))
    recommendations = [
        f"Continue to protect and support {analysis['highest_performing_product']} as the leading product.",
        f"Review pricing, promotion, or inventory for {analysis['lowest_performing_product']}.",
        "Allocate additional sales support to the strongest-performing regions.",
    ]
    for recommendation in recommendations:
        content.append(Paragraph(f"• {recommendation}", styles["body"]))

    footer_enabled = css["--footer-enabled"].lower() == "true"

    def draw_footer(canvas, doc):
        if not footer_enabled:
            return
        canvas.saveState()
        canvas.setFont(css["--footer-font"], float(css["--footer-size"]))
        canvas.setFillColor(_hex_color(css["--footer-color"]))
        y = float(css["--footer-y"])
        canvas.drawString(doc.leftMargin, y, css["--footer-left-text"])
        canvas.drawRightString(
            doc.pagesize[0] - doc.rightMargin,
            y,
            f"Page {doc.page}",
        )
        canvas.restoreState()

    document.build(content, onFirstPage=draw_footer, onLaterPages=draw_footer)
    return str(pdf_path)


def execute(state, context=None):
    context = context or {}
    analysis = state.get("sales_analysis")
    if analysis is None:
        raise ValueError("PDF report was not generated because sales analysis is unavailable.")

    try:
        pdf_path = generate_sales_report(
            analysis,
            state.get("business_insights", []),
            context.get("output_dir"),
        )
    except Exception as error:
        raise ValueError(f"PDF report generation failed: {error}") from error

    return {"pdf_path": pdf_path}
