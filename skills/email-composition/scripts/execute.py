"""Email-draft implementation owned by the email-composition skill."""

from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent.parent
EMAIL_TEMPLATE = SKILL_ROOT / "templates" / "email.txt"


def compose_email(analysis, pdf_path, manager_name="Manager"):
    if not isinstance(analysis, dict):
        raise ValueError("Sales analysis must be provided as a dictionary.")

    required_keys = (
        "total_revenue",
        "total_quantity",
        "highest_performing_product",
        "lowest_performing_product",
    )
    missing_keys = [key for key in required_keys if key not in analysis]
    if missing_keys:
        raise ValueError(f"Missing analysis fields: {', '.join(missing_keys)}")

    if not pdf_path:
        raise ValueError("A PDF report path is required.")

    report_path = Path(pdf_path)
    if not report_path.is_file():
        raise FileNotFoundError(f"PDF report not found: {pdf_path}")

    manager = str(manager_name).strip() if manager_name else "Manager"
    template = EMAIL_TEMPLATE.read_text(encoding="utf-8") if EMAIL_TEMPLATE.is_file() else ""

    if template:
        body = template.format(
            manager=manager,
            total_revenue=f"${float(analysis['total_revenue']):,.2f}",
            total_quantity=analysis["total_quantity"],
            highest_performing_product=analysis["highest_performing_product"],
            lowest_performing_product=analysis["lowest_performing_product"],
        )
    else:
        body = (
            f"Hello {manager},\n\n"
            f"The sales analysis is complete. Total revenue is "
            f"${float(analysis['total_revenue']):,.2f}, and total quantity sold is "
            f"{analysis['total_quantity']}.\n\n"
            f"The highest-performing product is {analysis['highest_performing_product']}, "
            f"while the lowest-performing product is {analysis['lowest_performing_product']}.\n\n"
            "The professional PDF report is attached for your review.\n\n"
            "Kind regards,\n"
            "Sales Reporting Assistant"
        )

    return {
        "subject": "Sales Performance Report",
        "body": body,
        "attachment_path": str(report_path),
    }


def execute(state, context=None):
    context = context or {}
    analysis = state.get("sales_analysis")
    pdf_path = state.get("pdf_path")

    if analysis is None:
        raise ValueError("Email draft was not created because sales analysis is unavailable.")
    if not pdf_path:
        raise ValueError("Email draft was not created because the PDF report is unavailable.")

    try:
        draft = compose_email(
            analysis,
            pdf_path,
            manager_name=context.get("manager_name", "Manager"),
        )
    except Exception as error:
        raise ValueError(f"Email composition failed: {error}") from error

    return {"email_draft": draft}
