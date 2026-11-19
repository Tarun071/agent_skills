# Sales Input Data Reference

## Supported Formats

- CSV: `.csv`
- Excel: `.xlsx`

## Required Columns

| Column | Accepted Values |
|---|---|
| `date` | Any nonblank date or date text |
| `product` | Nonblank product name |
| `region` | Nonblank region name |
| `quantity` | Zero or positive numeric value |
| `unit_price` | Zero or positive numeric value |

Column names are normalized to lowercase and spaces are converted to underscores.

## Calculations

- Revenue: `quantity * unit_price`
- Total revenue: sum of row revenue
- Total quantity: sum of quantity
- Product performance: revenue and quantity grouped by product
- Region performance: revenue and quantity grouped by region
- Highest/lowest product: ranked by revenue

Invalid numeric values, negative quantities or prices, blank required values, missing columns, and empty datasets are rejected.
