from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

import agent.workflow as workflow
from agent.workflow import (
    discover_skills,
    execute_skills,
    run_sales_workflow,
    select_skills,
)


def empty_state(request, file_path=None):
    return {
        "request": request,
        "file_path": str(file_path) if file_path else None,
        "selected_skills": {},
        "loaded_instructions": {},
        "sales_analysis": None,
        "business_insights": [],
        "pdf_path": None,
        "email_draft": None,
        "execution_steps": [],
        "errors": [],
    }


def create_sales_file(tmp_path):
    sales_file = tmp_path / "sales.csv"
    pd.DataFrame([
        {"date": "2026-01-01", "product": "Laptop", "region": "North", "quantity": 5, "unit_price": 1000},
        {"date": "2026-01-02", "product": "Mouse", "region": "South", "quantity": 10, "unit_price": 25},
    ]).to_csv(sales_file, index=False)
    return sales_file


def test_full_request_selects_all_three_skills():
    state = empty_state("Analyze sales, generate a PDF report, and prepare an email draft for my manager")
    state = select_skills(state)

    assert set(state["selected_skills"]) == {
        "sales-analysis",
        "report-generation",
        "email-composition",
    }


def test_sales_analysis_skill_is_selected():
    state = empty_state("Analyze this CSV revenue data")
    state = select_skills(state)

    assert "sales-analysis" in state["selected_skills"]
    assert "report-generation" not in state["selected_skills"]
    assert "email-composition" not in state["selected_skills"]


def test_skills_are_loaded_from_skill_files():
    discovered = discover_skills()

    assert set(discovered) == {
        "sales-analysis",
        "report-generation",
        "email-composition",
    }

    state = empty_state("Analyze sales and generate a PDF report and email draft")
    state = select_skills(state)

    # Use execute_skills with a missing file to verify instructions are loaded first.
    state = execute_skills(state)

    assert set(state["loaded_instructions"]) == set(state["selected_skills"])
    for instructions in state["loaded_instructions"].values():
        assert "## Purpose" in instructions


def test_full_workflow_executes_in_correct_order(tmp_path):
    sales_file = create_sales_file(tmp_path)
    request = "Analyze sales, generate a PDF report, and prepare an email draft"

    state = run_sales_workflow(request, sales_file)

    assert state["execution_steps"] == [
        "Loaded instructions: sales-analysis",
        "Loaded instructions: report-generation",
        "Loaded instructions: email-composition",
        "Executed sales-analysis",
        "Executed report-generation",
        "Executed email-composition",
    ]


def test_pdf_is_generated(tmp_path):
    sales_file = create_sales_file(tmp_path)
    state = run_sales_workflow("Generate a PDF sales report", sales_file)

    assert state["pdf_path"] is not None
    assert Path(state["pdf_path"]).is_file()
    assert state["pdf_path"].endswith(".pdf")


def test_email_draft_is_created(tmp_path):
    sales_file = create_sales_file(tmp_path)
    state = run_sales_workflow("Analyze sales and prepare an email for the manager", sales_file)

    assert state["email_draft"] is not None
    assert state["email_draft"]["subject"]
    assert state["email_draft"]["body"]
    assert state["email_draft"]["attachment_path"]


def test_missing_file_produces_useful_error():
    state = run_sales_workflow(
        "Analyze sales, generate a PDF report, and prepare an email draft",
        "missing-sales.csv",
    )

    assert any("requires an uploaded CSV or XLSX file" in error for error in state["errors"])
    assert state["sales_analysis"] is None
    assert state["pdf_path"] is None
    assert state["email_draft"] is None


def test_analysis_failure_prevents_report_and_email(tmp_path):
    bad_file = tmp_path / "bad_sales.csv"
    pd.DataFrame({"date": ["2026-01-01"], "product": ["Laptop"]}).to_csv(bad_file, index=False)

    state = run_sales_workflow(
        "Analyze sales, generate a PDF report, and prepare an email draft",
        bad_file,
    )

    assert any("Sales analysis failed" in error for error in state["errors"])
    assert "Executed report-generation" not in state["execution_steps"]
    assert "Executed email-composition" not in state["execution_steps"]
    assert state["pdf_path"] is None
    assert state["email_draft"] is None


@pytest.fixture(autouse=True)
def mock_gemini(monkeypatch):
    """Mock Gemini so workflow tests never require an API key or network call."""
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "test-model")

    class MockModel:
        def invoke(self, prompt):
            if "Available skills" in prompt:
                if "only analyze" in prompt.lower() or "analyze this csv" in prompt.lower():
                    content = '{"skills":[{"name":"sales-analysis","reason":"The request only asks for sales analysis."}]}'
                else:
                    content = '{"skills":[{"name":"sales-analysis","reason":"Analyze the sales data."},{"name":"report-generation","reason":"Generate the PDF report."},{"name":"email-composition","reason":"Prepare the manager email draft."}]}'
                return SimpleNamespace(content=content)

            content = '{"insights":["Laptop is the highest-performing product by revenue.","North is the strongest region by revenue."]}'
            return SimpleNamespace(content=content)

    monkeypatch.setattr(workflow, "create_gemini_model", lambda: MockModel())


def test_unknown_gemini_skill_names_are_rejected(monkeypatch):
    class UnknownModel:
        def invoke(self, prompt):
            return SimpleNamespace(content='{"skills":[{"name":"unknown-skill","reason":"Not available."},{"name":"sales-analysis","reason":"Available and relevant."}]}')

    monkeypatch.setattr(workflow, "create_gemini_model", lambda: UnknownModel())
    state = empty_state("Analyze sales")
    state = select_skills(state)

    assert set(state["selected_skills"]) == {"sales-analysis"}


def test_gemini_selection_failure_is_handled(monkeypatch):
    def failing_model():
        raise RuntimeError("Gemini unavailable")

    monkeypatch.setattr(workflow, "create_gemini_model", failing_model)
    state = empty_state("Analyze sales")
    state = select_skills(state)

    assert state["selected_skills"] == {}
    assert any("Gemini skill selection failed" in error for error in state["errors"])


def test_business_insights_use_actual_analysis(monkeypatch, tmp_path):
    analysis = {
        "total_revenue": 5250.0,
        "total_quantity": 15,
        "product_performance": {
            "Laptop": {"revenue": 5000.0, "quantity": 5},
            "Mouse": {"revenue": 250.0, "quantity": 10},
        },
        "region_performance": {
            "North": {"revenue": 5000.0, "quantity": 5},
            "South": {"revenue": 250.0, "quantity": 10},
        },
        "highest_performing_product": "Laptop",
        "lowest_performing_product": "Mouse",
    }

    class InsightModel:
        def invoke(self, prompt):
            assert '"total_revenue": 5250.0' in prompt
            assert "Laptop" in prompt
            assert "North" in prompt
            return SimpleNamespace(content='{"insights":["Laptop generated $5,000 in revenue.","North was the strongest region."]}')

    monkeypatch.setattr(workflow, "create_gemini_model", lambda: InsightModel())

    insights = workflow.generate_business_insights(analysis)

    assert "Laptop generated $5,000 in revenue." in insights
    assert "North was the strongest region." in insights


def test_full_workflow_with_mocked_gemini_executes_correctly(tmp_path, mock_gemini):
    sales_file = create_sales_file(tmp_path)
    request = "Analyze sales, generate a PDF report, and prepare an email draft"

    state = run_sales_workflow(request, sales_file)

    assert state["execution_steps"] == [
        "Loaded instructions: sales-analysis",
        "Loaded instructions: report-generation",
        "Loaded instructions: email-composition",
        "Executed sales-analysis",
        "Executed report-generation",
        "Executed email-composition",
    ]
    assert state["pdf_path"] is not None
    assert Path(state["pdf_path"]).is_file()
    assert state["email_draft"] is not None
    assert state["email_draft"]["attachment_path"] == state["pdf_path"]


def test_empty_gemini_skill_selection_is_rejected(monkeypatch):
    class EmptyModel:
        def invoke(self, prompt):
            return SimpleNamespace(content='{"skills": []}')

    monkeypatch.setattr(workflow, "create_gemini_model", lambda: EmptyModel())
    state = empty_state("Analyze sales")
    state = select_skills(state)

    assert state["selected_skills"] == {}
    assert any("no valid skills" in error for error in state["errors"])


def test_no_execution_when_no_skills_are_selected():
    state = empty_state("Analyze sales")
    state["errors"] = ["Gemini skill selection returned no valid skills for the request."]

    state = execute_skills(state)

    assert state["execution_steps"] == []
    assert state["sales_analysis"] is None


def test_meaningful_request_text_is_required():
    state = empty_state("!!!")
    state = select_skills(state)

    assert state["selected_skills"] == {}
    assert any("meaningful request" in error for error in state["errors"])
