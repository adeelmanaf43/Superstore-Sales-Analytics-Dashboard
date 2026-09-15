"""Evidence-based selected-data narratives; no financial scenarios are retained."""

import pandas as pd

from src.analytics import (
    DISCOUNT_RISK_THRESHOLD,
    calculate_customer_value_segments,
    calculate_discount_loss_exposure,
    calculate_performance,
    calculate_quarterly_performance,
)


def generate_insights(df: pd.DataFrame) -> list[tuple[str, str]]:
    """Return titles and plain Markdown narratives using only supplied rows."""
    if df.empty:
        return []
    exposure = calculate_discount_loss_exposure(df)
    if exposure["transaction_count"]:
        discount_text = (
            f"{exposure['unprofitable_transaction_count']:,} of "
            f"{exposure['transaction_count']:,} transactions with discounts of "
            f"{DISCOUNT_RISK_THRESHOLD:.0%} or more were unprofitable "
            f"({exposure['unprofitable_transaction_rate']:.2f}%). "
            f"Observed gross loss exposure: ${exposure['gross_loss_exposure']:,.2f}. "
            f"Net profit across all transactions in this discount group: "
            f"${exposure['net_profit']:,.2f}. "
            "These are historical amounts for the selected data, not recoverable savings. "
            "Review discount policies alongside product mix and costs; association does not establish causation."
        )
    else:
        discount_text = (
            "No transactions meet the discount risk threshold in this selection."
        )
    customers, segments = calculate_customer_value_segments(df)
    top = segments.iloc[0]
    customer_text = (
        f"The highest-profit {int(top['customer_count']):,} of {len(customers):,} customers "
        f"(the rounded-up Top 20% group) contributed ${top['Profit']:,.2f} in selected-period net profit. "
    )
    if pd.notna(top["Net Profit Share %"]):
        customer_text += (
            f"This is {top['Net Profit Share %']:.2f}% of total net profit. "
            "Negative-profit customers can make this share exceed 100%."
        )
    else:
        customer_text += "A net-profit concentration percentage is not shown because total net profit is nonpositive."
    products = calculate_performance(df, "Sub-Category")
    loss_count = int((products["Profit"] < 0).sum())
    product_text = (
        f"{loss_count} of {len(products)} selected sub-categories have negative net profit. "
        "Review their pricing and costs. These records do not establish that selling "
        "loss-making products causes later purchases or preserves future revenue."
    )
    quarters = calculate_quarterly_performance(df)
    quarter_text = "Quarterly comparisons pool the selected years and use total profit / total sales. "
    q4 = quarters.loc[quarters["Quarter"] == 4]
    if not q4.empty:
        row = q4.iloc[0]
        quarter_text += (
            f"Q4 sales were ${row['Sales']:,.2f}, with net profit of ${row['Profit']:,.2f} "
            f"and a {row['Profit Margin %']:.2f}% margin. "
            "No change in profit from a future discount policy is estimated."
        )
    else:
        quarter_text += "No Q4 transactions are selected."
    return [
        ("Discounts and observed losses", discount_text),
        ("Customer profit concentration", customer_text),
        ("Product profitability", product_text),
        ("Quarterly performance", quarter_text),
    ]
