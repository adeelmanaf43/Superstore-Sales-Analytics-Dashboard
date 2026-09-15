"""Align the analysis notebook with the production analytics modules."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "SuperStore_Sales_Data_Analysis.ipynb"


def lines(text: str) -> list[str]:
    """Convert readable multiline source to notebook source lines."""
    return text.strip().splitlines(keepends=True)


def replace_cell(cells: list[dict], starts_with: str, source: str) -> None:
    """Replace the unique cell whose source starts with the supplied text."""
    matches = [
        cell
        for cell in cells
        if "".join(cell.get("source", [])).startswith(starts_with)
    ]
    replacement = lines(source)
    if not matches and any(cell.get("source", []) == replacement for cell in cells):
        return
    if not matches and replacement:
        first_line = replacement[0].rstrip("\r\n")
        matches = [
            cell
            for cell in cells
            if cell.get("source") and cell["source"][0].rstrip("\r\n") == first_line
        ]
    if len(matches) != 1:
        raise ValueError(
            f"Expected one cell starting with {starts_with!r}; found {len(matches)}"
        )
    matches[0]["source"] = replacement


def main() -> None:
    """Update terminology and calculations, then remove every stale saved output."""
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    cells = notebook["cells"]

    replace_cell(
        cells,
        "# Historical exploration",
        """
# Audited Superstore analysis

This notebook now uses the same validated, Streamlit-independent calculations as
the dashboard. A **transaction** is one dataframe row; an **order** is a distinct
`Order ID`. All financial figures below are historical observations from the
supplied **2011–2014** data. They are not forecasts, annualized impacts, recovered
profit, or realized savings.

See [the analytical methodology](docs/METHODOLOGY.md) for metric definitions.
Run `python scripts/report_findings.py` from the repository root to reproduce the
current full-data findings.
        """,
    )
    replace_cell(
        cells,
        "### Step 1. Upload the Dataset",
        "### Step 1: Use the Repository Dataset",
    )
    replace_cell(
        cells,
        "from google.colab import files",
        """
# Run this notebook from the repository root so Superstore.csv and src/ resolve.
# No upload step or external service is required.
""",
    )
    replace_cell(
        cells,
        "#import libraries",
        """
import numpy as np
import pandas as pd

pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", 100)
print("Libraries imported successfully")
""",
    )
    replace_cell(
        cells, "### Step 3: Load the Data", "### Step 3: Load and Validate the Data"
    )
    replace_cell(
        cells,
        'df = pd.read_csv("Superstore.csv"',
        """
from pathlib import Path

from src.data import validate_data

DATA_PATH = Path("Superstore.csv")
raw_df = pd.read_csv(DATA_PATH, encoding="latin-1")
raw_df["Order Date"] = pd.to_datetime(raw_df["Order Date"], format="%d-%m-%Y")
raw_df["Ship Date"] = pd.to_datetime(raw_df["Ship Date"], format="%d-%m-%Y")
df = validate_data(raw_df)

print("Dataset loaded and validated successfully")
print(f"Shape: {df.shape[0]:,} transactions, {df.shape[1]} validated columns")
print(f"Date range: {df['Order Date'].min():%Y-%m-%d} to {df['Order Date'].max():%Y-%m-%d}")
""",
    )
    replace_cell(
        cells,
        "The super store sales dataset",
        "The supplied dataset contains **9,994 transactions**, **5,009 unique orders**, and validated dates from **2011-01-04 through 2014-12-31**.",
    )
    replace_cell(cells, "### Step 4: Initital", "### Step 4: Initial Data Exploration")
    replace_cell(
        cells,
        "# Quick Business Insights",
        """
from src.analytics import calculate_kpis

kpis = calculate_kpis(df)
print("QUICK BUSINESS INSIGHTS")
print(f"Total Sales: ${kpis['sales']:,.2f}")
print(f"Total Profit: ${kpis['profit']:,.2f}")
print(f"Unique Orders: {kpis['unique_order_count']:,}")
print(f"Transactions: {kpis['transaction_count']:,}")
print(f"Customers: {df['Customer ID'].nunique():,}")
print(f"Profit Margin: {kpis['profit_margin']:.2f}%")
print(f"Loss-making Transactions: {kpis['unprofitable_transaction_rate']:.2f}%")
""",
    )
    replace_cell(
        cells,
        "### Step 7. Fix Date Columns",
        "### Step 7: Verify Parsed Date Columns",
    )
    replace_cell(
        cells,
        'print("="*80)\nprint("CONVERTING DATE COLUMNS")',
        """
print("DATE VALIDATION")
print(f"Order Date Range: {df['Order Date'].min():%Y-%m-%d} to {df['Order Date'].max():%Y-%m-%d}")
print(f"Ship Date Range: {df['Ship Date'].min():%Y-%m-%d} to {df['Ship Date'].max():%Y-%m-%d}")
display(df[["Order Date", "Ship Date"]].dtypes)
""",
    )
    replace_cell(
        cells,
        "#Calculate derived financial metrics",
        """
# Derived descriptive fields used only for notebook exploration.
df["Profit Margin %"] = np.where(df["Sales"] != 0, df["Profit"] / df["Sales"] * 100, 0.0)
df["Is Profitable"] = df["Profit"] > 0
df["Is Loss Making"] = df["Profit"] < 0

print("Derived fields created: Profit Margin %, Is Profitable, Is Loss Making")
print("Dashboard aggregate margins are recomputed as sum(Profit) / sum(Sales), not mean row margins.")
print("No discount-dollar amount or counterfactual list price is inferred from Sales.")
""",
    )
    replace_cell(
        cells,
        "#Customer-level metrics",
        """
# Customer-level observed metrics. These are selected-period values, not forecasts.
customer_metrics = df.groupby("Customer ID").agg(
    Customer_Name=("Customer Name", "first"),
    Selected_Period_Sales=("Sales", "sum"),
    Selected_Period_Profit=("Profit", "sum"),
    Transaction_Count=("Order ID", "size"),
    Unique_Order_Count=("Order ID", "nunique"),
).reset_index()

print(f"Customers: {len(customer_metrics):,}")
display(customer_metrics.sort_values("Selected_Period_Profit", ascending=False).head())
        """,
    )
    replace_cell(
        cells,
        'print("\\n" + "=" * 80)\nprint("CREATING TIME-BASED FEATURES")',
        """
df["Year"] = df["Order Date"].dt.year
df["Month"] = df["Order Date"].dt.month
df["Month Name"] = df["Order Date"].dt.month_name()
df["Quarter"] = df["Order Date"].dt.quarter
df["Day of Week"] = df["Order Date"].dt.day_name()
df["Week of Year"] = df["Order Date"].dt.isocalendar().week
df["Days to Ship"] = (df["Ship Date"] - df["Order Date"]).dt.days

print("Time fields created")
print(df["Year"].value_counts().sort_index())
print(f"Average days to ship: {df['Days to Ship'].mean():.2f}")
""",
    )
    replace_cell(
        cells,
        "# Product/Category performance",
        """
from src.analytics import calculate_performance

category_performance = calculate_performance(df, "Category")
subcategory_performance = calculate_performance(df, "Sub-Category")

print("CATEGORY PERFORMANCE")
display(category_performance)
print("SUB-CATEGORY PERFORMANCE")
display(subcategory_performance.sort_values("Profit", ascending=False))
""",
    )
    replace_cell(
        cells,
        "# Discount analysis",
        """
from src.analytics import calculate_discount_profitability, calculate_discount_segments

discount_analysis = calculate_discount_profitability(df)
discount_groups = calculate_discount_segments(df)

print("DISCOUNT IMPACT ANALYSIS")
print("Profitable transaction rate = count(Profit > 0) / transaction count × 100.")
display(discount_analysis)
display(discount_groups)
""",
    )
    replace_cell(
        cells,
        "#Regional Performance",
        """
from src.analytics import calculate_performance, calculate_region_performance

region_performance = calculate_region_performance(df)
segment_performance = calculate_performance(df, "Segment")

print("REGIONAL PERFORMANCE")
display(region_performance)
print("CUSTOMER-SEGMENT PERFORMANCE")
display(segment_performance)
""",
    )
    replace_cell(
        cells,
        "# Save cleaned dataset",
        """
# The dashboard validates the supplied repository artifact at load time.
# Export a fresh validated source-column copy only when explicitly needed:
# df.to_csv("superstore_cleaned.csv", index=False)
print("Validated data is ready. No file was overwritten by this notebook run.")
""",
    )
    replace_cell(
        cells,
        "---\n\n## 📝 Day 1 Summary",
        """
---

## Data preparation summary

- **9,994 transactions** and **5,009 unique orders** from **2011–2014**
- **793 customers**
- Total sales: **$2,297,200.86**
- Total profit: **$286,397.02**
- Aggregate profit margin: **12.47%**
- **18.72%** of transactions were loss-making (`Profit < 0`)

These figures are descriptive results for the supplied sample. They do not
represent an identified retailer's realized impact or a causal policy result.
""",
    )
    replace_cell(cells, "# Day2:", "# Part 2: Audited Insights and Visualizations")
    replace_cell(
        cells,
        "## PART 1:",
        "## Discount profitability by exact observed discount",
    )
    replace_cell(
        cells,
        "# Create granular discount bins",
        """
from src.analytics import calculate_discount_profitability

profit_cliff = calculate_discount_profitability(df)
display(profit_cliff[[
    "Discount", "transaction_count", "profitable_transaction_count",
    "unprofitable_transaction_count", "break_even_transaction_count",
    "profitable_transaction_rate", "transaction_share",
]])
""",
    )
    replace_cell(
        cells,
        "# Visualize the cliff",
        """
from src.charts import discount_profitability_chart

fig = discount_profitability_chart(profit_cliff)
fig.show()
""",
    )
    replace_cell(
        cells,
        "### Finding #2. Financial Impact Analysis",
        "### Finding 2: Observed High-Discount Loss Exposure",
    )
    replace_cell(
        cells,
        'print("\\n" + "="*80)\nprint("💸 FINANCIAL IMPACT',
        """
from src.analytics import DISCOUNT_RISK_THRESHOLD, calculate_discount_loss_exposure

exposure = calculate_discount_loss_exposure(df)
print(f"Threshold: Discount >= {DISCOUNT_RISK_THRESHOLD:.0%}")
print(f"Transactions: {exposure['transaction_count']:,}")
print(f"Loss-making transactions: {exposure['unprofitable_transaction_count']:,}")
print(f"Loss-making transaction rate: {exposure['unprofitable_transaction_rate']:.2f}%")
print(f"Observed gross loss exposure: ${exposure['gross_loss_exposure']:,.2f}")
print(f"Net profit across all transactions in the group: ${exposure['net_profit']:,.2f}")
print("Historical amounts only; neither amount is recoverable savings or an annual forecast.")
""",
    )
    replace_cell(
        cells,
        "# Create the most impactful chart",
        """
from src.charts import discount_scatter

fig = discount_scatter(df, DISCOUNT_RISK_THRESHOLD)
fig.show()
""",
    )
    replace_cell(
        cells,
        "### Finding #3:",
        "### Finding 3: Customer Profit Concentration",
    )
    replace_cell(
        cells,
        "# Get first purchase category",
        """
from src.analytics import calculate_customer_value_segments

customers, customer_segments = calculate_customer_value_segments(df)
display(customer_segments)
display(customers.head(10))

top = customer_segments.iloc[0]
print(
    f"The highest-profit {int(top['customer_count']):,} of {len(customers):,} customers "
    f"contributed ${top['Profit']:,.2f}, or {top['Net Profit Share %']:.2f}% of total net profit."
)
print("Negative-profit customers can make a segment share exceed 100%.")
print("These are observed selected-period values, not customer lifetime forecasts.")
""",
    )
    replace_cell(
        cells,
        "### Finding #4.",
        "### Finding 4: Product Profitability",
    )
    replace_cell(
        cells,
        "# For customer who bought unprofitable products",
        """
from src.analytics import calculate_performance

product_performance = calculate_performance(df, "Sub-Category").sort_values("Profit")
display(product_performance)
loss_making_subcategories = product_performance[product_performance["Profit"] < 0]
print(f"{len(loss_making_subcategories)} of {len(product_performance)} sub-categories have negative net profit.")
print("The dataset does not establish that loss-making products cause later purchases or preserve future revenue.")
""",
    )
    replace_cell(
        cells,
        "### Insights#5:",
        "### Finding 5: Quarterly Performance",
    )
    replace_cell(
        cells,
        "# Add markdown:",
        """
from src.analytics import calculate_quarterly_performance

quarterly_analysis = calculate_quarterly_performance(df)
display(quarterly_analysis)
q4 = quarterly_analysis.loc[quarterly_analysis["Quarter"] == 4].iloc[0]
print(
    f"Q4 sales were ${q4['Sales']:,.2f}, with net profit of ${q4['Profit']:,.2f} "
    f"and a {q4['Profit Margin %']:.2f}% aggregate margin."
)
print("No future discount-policy impact is estimated because price and volume responses are not observed.")
""",
    )

    for cell in cells:
        if cell["cell_type"] == "code":
            cell["outputs"] = []
            cell["execution_count"] = None

    notebook.setdefault("metadata", {}).setdefault("language_info", {})["name"] = (
        "python"
    )
    NOTEBOOK.write_text(
        json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(f"Updated {NOTEBOOK.name}; cleared all stale outputs.")


if __name__ == "__main__":
    main()
