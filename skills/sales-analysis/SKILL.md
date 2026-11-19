---
name: sales-analysis
description: Analyze uploaded sales data from CSV or XLSX files and prepare business-friendly sales metrics and insights.
---

# Sales Analysis

## Purpose

Analyze uploaded sales data to calculate revenue, quantity, product performance, regional performance, and practical business insights.

## When to Use This Skill

Use this skill after a user uploads a sales CSV or XLSX file and before generating a PDF report.

## Input Requirements

- A CSV (`.csv`) or Excel (`.xlsx`) file.
- The dataset must contain these expected columns:
  - `date`
  - `product`
  - `region`
  - `quantity`
  - `unit_price`
- Column names may be checked and normalized before analysis.
- Numeric values should be valid quantities and unit prices.

## Step-by-Step Instructions

1. Read the uploaded CSV or XLSX file.
2. Validate that the required columns exist.
3. Remove or clearly report blank, invalid, or non-numeric rows.
4. Convert `quantity` and `unit_price` to numeric values.
5. Calculate revenue for each row as `revenue = quantity × unit_price`.
6. Calculate total revenue across all valid rows.
7. Calculate total quantity sold across all valid rows.
8. Group revenue and quantity by `product` to determine product-wise sales performance.
9. Group revenue and quantity by `region` to determine region-wise sales performance.
10. Identify the highest-performing product and lowest-performing product using revenue.
11. Review patterns in dates, products, regions, and revenue.
12. Generate clear business insights, such as:
    - The strongest product and region.
    - The weakest product or region.
    - Concentration of revenue among leading products.
    - Regional or product opportunities for growth.

## Expected Output

Provide a structured sales analysis containing:

- Total revenue.
- Total quantity sold.
- Product-wise sales performance.
- Region-wise sales performance.
- Highest-performing product.
- Lowest-performing product.
- A short list of business insights.

Keep the output clear and suitable for later use in a PDF report.

## Execution Guidance

- Perform calculations exactly before interpreting the results.
- Do not invent missing products, regions, dates, or values.
- Handle missing or invalid values safely and explain when data was excluded.
- Use consistent currency formatting when the currency is known.
- Keep calculations simple and beginner-friendly.
- Return the analysis as structured data that can be passed to the report-generation skill.
