"""Sales analysis implementation owned by the sales-analysis skill."""

from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = ["date", "product", "region", "quantity", "unit_price"]


def load_sales_data(file_path):
    """Load sales data from a CSV or XLSX file."""
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix not in (".csv", ".xlsx"):
        raise ValueError("Unsupported file type. Please upload a CSV or XLSX file.")
    if not path.exists():
        raise FileNotFoundError(f"Sales file not found: {file_path}")
    if suffix == ".csv":
        return pd.read_csv(path)
    return pd.read_excel(path, engine="openpyxl")


def validate_sales_data(dataframe):
    """Normalize and validate sales data."""
    if not isinstance(dataframe, pd.DataFrame):
        raise ValueError("Sales data must be provided as a pandas DataFrame.")
    if dataframe.empty:
        raise ValueError("Sales data is empty.")

    dataframe.columns = [
        str(column).strip().lower().replace(" ", "_")
        for column in dataframe.columns
    ]
    missing = [column for column in REQUIRED_COLUMNS if column not in dataframe.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    data = dataframe.copy()
    for column in REQUIRED_COLUMNS:
        if data[column].isna().any():
            raise ValueError(f"Column '{column}' contains missing values.")

    for column in ("quantity", "unit_price"):
        converted = pd.to_numeric(data[column], errors="coerce")
        if converted.isna().any():
            raise ValueError(f"Column '{column}' contains invalid numeric values.")
        data[column] = converted

    if (data["quantity"] < 0).any():
        raise ValueError("Quantity cannot contain negative values.")
    if (data["unit_price"] < 0).any():
        raise ValueError("Unit price cannot contain negative values.")

    for column in ("product", "region", "date"):
        if data[column].astype(str).str.strip().eq("").any():
            raise ValueError(f"Column '{column}' contains missing values.")

    return data


def analyze_sales_data(dataframe):
    """Calculate JSON-safe sales totals and performance summaries."""
    data = validate_sales_data(dataframe).copy()
    data["revenue"] = data["quantity"] * data["unit_price"]

    product_performance = (
        data.groupby("product", sort=True)[["revenue", "quantity"]]
        .sum()
        .reset_index()
        .sort_values("revenue", ascending=False)
    )
    region_performance = (
        data.groupby("region", sort=True)[["revenue", "quantity"]]
        .sum()
        .reset_index()
        .sort_values("revenue", ascending=False)
    )

    if product_performance.empty:
        raise ValueError("No valid product sales could be analyzed.")

    highest_product = product_performance.iloc[0]
    lowest_product = product_performance.iloc[-1]

    return {
        "total_revenue": round(float(data["revenue"].sum()), 2),
        "total_quantity": int(data["quantity"].sum()),
        "product_performance": {
            str(row["product"]): {
                "revenue": round(float(row["revenue"]), 2),
                "quantity": int(row["quantity"]),
            }
            for _, row in product_performance.iterrows()
        },
        "region_performance": {
            str(row["region"]): {
                "revenue": round(float(row["revenue"]), 2),
                "quantity": int(row["quantity"]),
            }
            for _, row in region_performance.iterrows()
        },
        "highest_performing_product": str(highest_product["product"]),
        "lowest_performing_product": str(lowest_product["product"]),
    }


def execute(state, context=None):
    """Execute this skill from a generic workflow state."""
    context = context or {}
    file_path = state.get("file_path")
    if not file_path:
        raise ValueError("Sales analysis requires an uploaded CSV or XLSX file.")

    path = Path(file_path)
    if not path.is_file():
        raise ValueError(
            f"Sales analysis requires an uploaded CSV or XLSX file. File not found: {file_path}"
        )

    try:
        analysis = analyze_sales_data(load_sales_data(path))
        generate_insights = context.get("generate_business_insights")
        insights = generate_insights(analysis) if generate_insights else []
    except Exception as error:
        raise ValueError(f"Sales analysis failed: {error}") from error

    return {
        "sales_analysis": analysis,
        "business_insights": insights,
    }
