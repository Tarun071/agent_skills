from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import agent.workflow as workflow
import main


client = TestClient(main.app)


@pytest.fixture(autouse=True)
def mock_gemini(monkeypatch):
    """Mock Gemini for API tests; no real API key or network call is used."""
    class MockModel:
        def invoke(self, prompt):
            if "Available skills" in prompt:
                content = '{"skills":[{"name":"sales-analysis","reason":"Analyze sales data."},{"name":"report-generation","reason":"Generate a PDF report."},{"name":"email-composition","reason":"Prepare the manager email draft."}]}'
                return SimpleNamespace(content=content)

            content = '{"insights":["Laptop is the strongest product.","North is the strongest region."]}'
            return SimpleNamespace(content=content)

    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "test-model")
    monkeypatch.setattr(workflow, "create_gemini_model", lambda: MockModel())


def sales_dataframe():
    return pd.DataFrame([
        {"date": "2026-01-01", "product": "Laptop", "region": "North", "quantity": 5, "unit_price": 1000},
        {"date": "2026-01-02", "product": "Mouse", "region": "South", "quantity": 10, "unit_price": 25},
    ])


def test_api_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_skills():
    response = client.get("/skills")

    assert response.status_code == 200
    names = {skill["name"] for skill in response.json()["skills"]}
    assert names == {"sales-analysis", "report-generation", "email-composition"}


def test_successful_csv_upload_and_cleanup(tmp_path, monkeypatch):
    csv_bytes = sales_dataframe().to_csv(index=False).encode("utf-8")

    response = client.post(
        "/process",
        data={"request": "Analyze sales and generate a PDF report and email draft"},
        files={"file": ("sales.csv", csv_bytes, "text/csv")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["sales_analysis"]["total_revenue"] == 5250.0
    assert body["pdf_path"] is not None
    assert body["email_draft"]["attachment_path"] == body["pdf_path"]

    assert Path(body["pdf_path"]).is_file()


def test_successful_xlsx_upload(tmp_path):
    xlsx_path = tmp_path / "sales.xlsx"
    sales_dataframe().to_excel(xlsx_path, index=False, engine="openpyxl")

    response = client.post(
        "/process",
        data={"request": "Analyze sales, generate a PDF report, and prepare an email draft"},
        files={"file": ("sales.xlsx", xlsx_path.read_bytes(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["sales_analysis"] is not None
    assert body["pdf_path"] is not None


def test_missing_file():
    response = client.post(
        "/process",
        data={"request": "Analyze sales"},
    )

    assert response.status_code == 400
    assert "CSV or XLSX" in response.json()["detail"]


def test_unsupported_file_extension():
    response = client.post(
        "/process",
        data={"request": "Analyze sales"},
        files={"file": ("sales.txt", b"not a sales file", "text/plain")},
    )

    assert response.status_code == 400
    assert "Unsupported file extension" in response.json()["detail"]


def test_empty_uploaded_file():
    response = client.post(
        "/process",
        data={"request": "Analyze sales"},
        files={"file": ("sales.csv", b"", "text/csv")},
    )

    assert response.status_code == 400
    assert "empty" in response.json()["detail"]


def test_workflow_errors(monkeypatch):
    monkeypatch.setattr(main, "run_sales_workflow", lambda request, file_path: {
        "selected_skills": {},
        "execution_steps": [],
        "sales_analysis": None,
        "business_insights": [],
        "pdf_path": None,
        "email_draft": None,
        "errors": ["Sales analysis failed: missing required columns"],
    })

    response = client.post(
        "/process",
        data={"request": "Analyze sales"},
        files={"file": ("sales.csv", b"date,product\n2026-01-01,Laptop", "text/csv")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "error"
    assert body["errors"]
    assert body["pdf_path"] is None


def test_unexpected_workflow_exception_is_returned(monkeypatch):
    def failing_workflow(request, file_path):
        raise RuntimeError("workflow crashed")

    monkeypatch.setattr(main, "run_sales_workflow", failing_workflow)

    response = client.post(
        "/process",
        data={"request": "Analyze sales"},
        files={"file": ("sales.csv", b"date,product,region,quantity,unit_price\n2026-01-01,Laptop,North,1,100", "text/csv")},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "error"
    assert "Workflow execution failed" in response.json()["errors"][0]


def test_temporary_upload_is_removed(monkeypatch):
    captured = {}

    def fake_workflow(request, file_path):
        captured["path"] = file_path
        assert Path(file_path).is_file()
        return {
            "selected_skills": {"sales-analysis": "Analyze sales."},
            "execution_steps": ["Executed sales-analysis"],
            "sales_analysis": {"total_revenue": 100.0},
            "business_insights": [],
            "pdf_path": None,
            "email_draft": None,
            "errors": [],
        }

    monkeypatch.setattr(main, "run_sales_workflow", fake_workflow)

    response = client.post(
        "/process",
        data={"request": "Analyze sales"},
        files={"file": ("sales.csv", b"date,product,region,quantity,unit_price\n2026-01-01,Laptop,North,1,100", "text/csv")},
    )

    assert response.status_code == 200
    assert not Path(captured["path"]).exists()


def test_empty_skill_selection_returns_error(monkeypatch):
    monkeypatch.setattr(main, "run_sales_workflow", lambda request, file_path: {
        "selected_skills": {},
        "execution_steps": [],
        "sales_analysis": None,
        "business_insights": [],
        "pdf_path": None,
        "email_draft": None,
        "errors": ["Gemini skill selection returned no valid skills for the request."],
    })

    response = client.post(
        "/process",
        data={"request": "Analyze sales"},
        files={"file": ("sales.csv", b"date,product,region,quantity,unit_price\n2026-01-01,Laptop,North,1,100", "text/csv")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "error"
    assert body["selected_skills"] == {}
    assert body["execution_steps"] == []
    assert body["errors"]


def test_meaningful_request_validation():
    response = client.post(
        "/process",
        data={"request": "!!!"},
        files={"file": ("sales.csv", b"date,product,region,quantity,unit_price\n2026-01-01,Laptop,North,1,100", "text/csv")},
    )

    assert response.status_code == 400
    assert "meaningful user request" in response.json()["detail"]


def test_partial_success_is_returned_when_execution_has_errors(monkeypatch):
    monkeypatch.setattr(main, "run_sales_workflow", lambda request, file_path: {
        "selected_skills": {"sales-analysis": "Analyze sales."},
        "execution_steps": ["Executed sales-analysis"],
        "sales_analysis": {"total_revenue": 100.0},
        "business_insights": [],
        "pdf_path": None,
        "email_draft": None,
        "errors": ["PDF report generation failed: template unavailable"],
    })

    response = client.post(
        "/process",
        data={"request": "Analyze sales"},
        files={"file": ("sales.csv", b"date,product,region,quantity,unit_price\n2026-01-01,Laptop,North,1,100", "text/csv")},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "partial_success"
