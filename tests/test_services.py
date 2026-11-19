import importlib.util
from pathlib import Path

import pandas as pd
import pytest


def load_skill_module(skill_name):
    script = Path(__file__).resolve().parents[1] / "skills" / skill_name / "scripts" / "execute.py"
    spec = importlib.util.spec_from_file_location(f"test_{skill_name.replace('-', '_')}", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sales_module = load_skill_module("sales-analysis")
report_module = load_skill_module("report-generation")
email_module = load_skill_module("email-composition")

load_sales_data = sales_module.load_sales_data
validate_sales_data = sales_module.validate_sales_data
analyze_sales_data = sales_module.analyze_sales_data
generate_sales_report = report_module.generate_sales_report
compose_email = email_module.compose_email


@pytest.fixture
def valid_sales_data():
    return pd.DataFrame([
        {"date": "2026-01-01", "product": "Laptop", "region": "North", "quantity": 5, "unit_price": 1000},
        {"date": "2026-01-02", "product": "Laptop", "region": "South", "quantity": 3, "unit_price": 1000},
        {"date": "2026-01-03", "product": "Mouse", "region": "North", "quantity": 20, "unit_price": 25},
    ])


def test_valid_csv_analysis(tmp_path, valid_sales_data):
    csv_path = tmp_path / "sales.csv"
    valid_sales_data.to_csv(csv_path, index=False)

    loaded = load_sales_data(csv_path)
    validated = validate_sales_data(loaded)
    analysis = analyze_sales_data(validated)

    assert analysis["total_revenue"] == 8500
    assert analysis["total_quantity"] == 28
    assert analysis["highest_performing_product"] == "Laptop"
    assert analysis["lowest_performing_product"] == "Mouse"
    assert analysis["product_performance"]["Laptop"] == {"revenue": 8000.0, "quantity": 8}


def test_valid_xlsx_analysis(tmp_path, valid_sales_data):
    xlsx_path = tmp_path / "sales.xlsx"
    valid_sales_data.to_excel(xlsx_path, index=False, engine="openpyxl")

    loaded = load_sales_data(xlsx_path)
    analysis = analyze_sales_data(loaded)

    assert analysis["total_revenue"] == 8500
    assert "North" in analysis["region_performance"]


def test_missing_required_columns(valid_sales_data):
    missing = valid_sales_data.drop(columns=["region"])

    with pytest.raises(ValueError, match="Missing required columns: region"):
        validate_sales_data(missing)


def test_invalid_numeric_values(valid_sales_data):
    invalid = valid_sales_data.copy()
    invalid["quantity"] = invalid["quantity"].astype(object)
    invalid.at[0, "quantity"] = "many"

    with pytest.raises(ValueError, match="invalid numeric values"):
        analyze_sales_data(invalid)


def test_negative_values(valid_sales_data):
    negative_quantity = valid_sales_data.copy()
    negative_quantity.loc[0, "quantity"] = -1

    with pytest.raises(ValueError, match="negative values"):
        analyze_sales_data(negative_quantity)

    negative_price = valid_sales_data.copy()
    negative_price.loc[0, "unit_price"] = -10

    with pytest.raises(ValueError, match="negative values"):
        analyze_sales_data(negative_price)


def test_pdf_generation(tmp_path, valid_sales_data):
    analysis = analyze_sales_data(valid_sales_data)
    insights = [
        "Laptop is the strongest revenue-generating product.",
        "North and South regions have active sales.",
    ]

    pdf_path = generate_sales_report(analysis, insights, tmp_path)

    assert pdf_path.endswith(".pdf")
    assert (tmp_path / pdf_path.split("\\")[-1].split("/")[-1]).is_file()


def test_unique_pdf_filenames(tmp_path, valid_sales_data):
    analysis = analyze_sales_data(valid_sales_data)

    first = generate_sales_report(analysis, ["Laptop leads sales."], tmp_path)
    second = generate_sales_report(analysis, ["Laptop leads sales."], tmp_path)

    assert first != second


def test_email_draft_generation(tmp_path, valid_sales_data):
    analysis = analyze_sales_data(valid_sales_data)
    pdf_path = generate_sales_report(analysis, ["Laptop leads sales."], tmp_path)

    draft = compose_email(analysis, pdf_path, manager_name="Alex")

    assert draft["subject"] == "Sales Performance Report"
    assert "Hello Alex" in draft["body"]
    assert "PDF report is attached" in draft["body"]
    assert draft["attachment_path"] == pdf_path


def test_missing_or_invalid_inputs(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_sales_data(tmp_path / "missing.csv")

    with pytest.raises(ValueError, match="Unsupported file type"):
        load_sales_data(tmp_path / "sales.txt")

    with pytest.raises(ValueError, match="Sales data must be provided"):
        validate_sales_data({"quantity": [1]})

    with pytest.raises(ValueError, match="Sales analysis must be provided"):
        generate_sales_report(None, [], tmp_path)

    with pytest.raises(FileNotFoundError):
        compose_email({
            "total_revenue": 100,
            "total_quantity": 2,
            "highest_performing_product": "Laptop",
            "lowest_performing_product": "Mouse",
        }, tmp_path / "missing.pdf")
