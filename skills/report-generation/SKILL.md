---
name: report-generation
description: Generate a professional PDF sales report from sales analysis metrics and business insights.
requires: sales-analysis
---

# Report Generation

## Purpose

Create a clear, professional PDF report that summarizes sales performance and presents business insights and recommendations.

## When to Use This Skill

Use this skill after the sales-analysis skill has produced valid totals, product and regional performance, and business insights.

## Input Requirements

- Sales analysis results from the sales-analysis skill.
- Business insights produced from the sales analysis.
- Optional reporting period, company name, or report date.
- The analysis must include:
  - Total revenue.
  - Total quantity sold.
  - Product-wise performance.
  - Region-wise performance.
  - Highest-performing product.
  - Lowest-performing product.

## Step-by-Step Instructions

1. Use the sales analysis and business insights as the report's source data.
2. Create a report title, such as **Sales Performance Report**.
3. Add a reporting summary describing the analysis period and overall sales position.
4. Present the overall sales metrics:
   - Total revenue.
   - Total quantity sold.
   - Highest-performing product.
   - Lowest-performing product.
5. Include a product performance section with revenue and quantity for each product.
6. Include a regional performance section with revenue and quantity for each region.
7. Include the business insights section in plain, understandable language.
8. Add recommendations based only on the calculated results, such as:
   - Protecting the strongest product or region.
   - Reviewing the weakest product or region.
   - Allocating more attention to promising markets.
9. Format the PDF professionally with clear headings, spacing, and readable sections.
10. Save the report in the `outputs/` directory.

## Expected Output

Provide a PDF report file containing:

- Report title.
- Reporting summary.
- Overall sales metrics.
- Product performance.
- Regional performance.
- Business insights.
- Recommendations.
- The final attachment path for the PDF report.

## Execution Guidance

- Do not recalculate or change the sales analysis during report generation.
- Use the supplied analysis as the source of truth.
- Keep table and text content readable on the PDF page.
- Avoid unsupported claims or recommendations not supported by the data.
- Use a deterministic and descriptive filename, for example `outputs/sales_report.pdf`.
- Return the PDF file path to the email-composition skill.

## PDF Formatting Configuration

The PDF generator must consume the following configuration. Do not maintain separate copies of these formatting values in Python.

```json
{
  "page": {
    "width": 612,
    "height": 792,
    "margins": {
      "left": 54,
      "right": 54,
      "top": 54,
      "bottom": 54
    }
  },
  "content": {
    "title": "Sales Performance Report",
    "summary_heading": "Reporting Summary",
    "summary_text": "This report summarizes revenue and quantity performance across products and regions.",
    "summary_table_heading": "Metric",
    "summary_value_heading": "Value",
    "total_revenue_label": "Total Revenue",
    "total_quantity_label": "Total Quantity",
    "highest_product_label": "Highest-Performing Product",
    "lowest_product_label": "Lowest-Performing Product",
    "product_heading": "Product Performance",
    "region_heading": "Regional Performance",
    "insights_heading": "Business Insights",
    "no_insights_text": "No business insights were provided.",
    "recommendations_heading": "Recommendations"
  },
  "styles": {
    "title": {
      "font_name": "Helvetica-Bold",
      "font_size": 20,
      "text_color": "#000000",
      "alignment": "left",
      "space_after": 14
    },
    "heading": {
      "font_name": "Helvetica-Bold",
      "font_size": 13,
      "text_color": "#1F4E78",
      "alignment": "left",
      "space_after": 8
    },
    "body": {
      "font_name": "Helvetica",
      "font_size": 10,
      "text_color": "#333333",
      "alignment": "left",
      "leading": 14,
      "space_after": 0
    }
  },
  "spacing": {
    "section_after": 18,
    "table_heading_before_table": 8,
    "table_after": 16,
    "insights_after": 10
  },
  "tables": {
    "summary_column_widths": [220, 220],
    "performance_column_widths": [220, 110, 110],
    "header_background": "#1F4E78",
    "header_text_color": "#FFFFFF",
    "grid_color": "#808080",
    "grid_width": 0.5,
    "alternate_row_background": "#EAF2F8",
    "header_font_name": "Helvetica-Bold",
    "body_font_name": "Helvetica",
    "header_top_padding": 8,
    "header_bottom_padding": 8,
    "body_top_padding": 6,
    "body_bottom_padding": 6,
    "numeric_alignment": "RIGHT"
  },
  "footer": {
    "enabled": true,
    "left_text": "Sales Performance Report",
    "page_prefix": "Page",
    "font_name": "Helvetica",
    "font_size": 8,
    "text_color": "#666666",
    "top_from_bottom": 24
  }
}
```
