"""Streamlit-independent calculations. One transaction is one input row."""

import math

import pandas as pd

DISCOUNT_RISK_THRESHOLD = 0.25
CUSTOMER_SEGMENTS = ("Top 20%", "Middle 30%", "Bottom 50%")


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Divide scalars, returning the documented fallback for a zero denominator."""
    return float(numerator / denominator) if denominator != 0 else default


def calculate_kpis(df: pd.DataFrame) -> dict[str, float | int]:
    """Compute selected-line-item totals; unique orders may be partially selected."""
    sales, profit = float(df["Sales"].sum()), float(df["Profit"].sum())
    return {
        "sales": sales,
        "profit": profit,
        "profit_margin": safe_divide(profit, sales) * 100,
        "transaction_count": len(df),
        "unique_order_count": df["Order ID"].nunique(),
        "unprofitable_transaction_rate": safe_divide((df["Profit"] < 0).sum(), len(df))
        * 100,
    }


def calculate_performance(
    df: pd.DataFrame, dimensions: str | list[str]
) -> pd.DataFrame:
    """Aggregate sums, row counts, distinct orders/customers, and weighted margins."""
    result = (
        df.groupby(dimensions, observed=True)
        .agg(
            Sales=("Sales", "sum"),
            Profit=("Profit", "sum"),
            transaction_count=("Order ID", "size"),
            unique_order_count=("Order ID", "nunique"),
            customer_count=("Customer ID", "nunique"),
        )
        .reset_index()
    )
    result["Profit Margin %"] = [
        safe_divide(profit, sales) * 100
        for profit, sales in zip(result["Profit"], result["Sales"])
    ]
    return result


def calculate_monthly_performance(df: pd.DataFrame) -> pd.DataFrame:
    """Sum sales and profit by calendar month, in chronological order."""
    result = df.groupby(df["Order Date"].dt.to_period("M"))[["Sales", "Profit"]].sum()
    result.index = result.index.to_timestamp()
    return result.reset_index()


def calculate_discount_profitability(df: pd.DataFrame) -> pd.DataFrame:
    """Group exact discount values (including 0 and 1); break-even is separate.

    Profitable rate = 100 * rows with Profit > 0 / all rows at that discount.
    Exact values avoid ambiguous band endpoints and floating-point bin edges.
    """
    result = (
        df.groupby("Discount")
        .agg(
            transaction_count=("Profit", "size"),
            profitable_transaction_count=("Profit", lambda values: (values > 0).sum()),
            unprofitable_transaction_count=(
                "Profit",
                lambda values: (values < 0).sum(),
            ),
            break_even_transaction_count=("Profit", lambda values: (values == 0).sum()),
            Profit=("Profit", "sum"),
            Sales=("Sales", "sum"),
        )
        .reset_index()
    )
    for prefix in ("profitable", "unprofitable", "break_even"):
        result[f"{prefix}_transaction_rate"] = (
            result[f"{prefix}_transaction_count"] / result["transaction_count"] * 100
        )
    result["transaction_share"] = result["transaction_count"] / max(len(df), 1) * 100
    return result


def calculate_discount_segments(
    df: pd.DataFrame,
    threshold: float = DISCOUNT_RISK_THRESHOLD,
) -> pd.DataFrame:
    """Split rows strictly below versus at/above a descriptive risk threshold."""
    if not 0 <= threshold <= 1:
        raise ValueError("Discount threshold must be between 0 and 1.")
    records = []
    for label, mask in (
        (f"Below {threshold:.0%}", df["Discount"] < threshold),
        (f"{threshold:.0%} or more", df["Discount"] >= threshold),
    ):
        subset = df.loc[mask]
        records.append(
            {
                "Discount Group": label,
                "transaction_count": len(subset),
                "average_transaction_profit": safe_divide(
                    subset["Profit"].sum(), len(subset)
                ),
                "profitable_transaction_rate": safe_divide(
                    (subset["Profit"] > 0).sum(), len(subset)
                )
                * 100,
                "unprofitable_transaction_rate": safe_divide(
                    (subset["Profit"] < 0).sum(), len(subset)
                )
                * 100,
            }
        )
    return pd.DataFrame(records)


def calculate_discount_loss_exposure(
    df: pd.DataFrame,
    threshold: float = DISCOUNT_RISK_THRESHOLD,
) -> dict[str, float | int]:
    """Historical gross losses and net profit at/above threshold, never savings.

    Gross loss exposure = -sum(Profit for negative-profit qualifying rows).
    Net profit includes positive and negative qualifying rows. Neither amount
    establishes causation, annualizes the period, or predicts recoverability.
    """
    if not 0 <= threshold <= 1:
        raise ValueError("Discount threshold must be between 0 and 1.")
    selected = df.loc[df["Discount"] >= threshold]
    losses = selected.loc[selected["Profit"] < 0, "Profit"]
    return {
        "transaction_count": len(selected),
        "unprofitable_transaction_count": len(losses),
        "unprofitable_transaction_rate": safe_divide(len(losses), len(selected)) * 100,
        "gross_loss_exposure": float(-losses.sum()),
        "net_profit": float(selected["Profit"].sum()),
    }


def calculate_customer_value_segments(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Rank selected-period customer net profit, breaking ties by Customer ID.

    Top ceil(20% * N), then through ceil(50% * N), then the remainder.
    Net-profit shares are undefined (NaN) when total net profit <= 0; otherwise
    shares may exceed 100% or be negative. No misleading cumulative curve.
    """
    customers = (
        df.groupby("Customer ID")
        .agg(
            **{
                "Customer Name": ("Customer Name", "first"),
                "Sales": ("Sales", "sum"),
                "Profit": ("Profit", "sum"),
                "unique_order_count": ("Order ID", "nunique"),
            }
        )
        .reset_index()
        .sort_values(["Profit", "Customer ID"], ascending=[False, True])
    )
    customers = customers.reset_index(drop=True)
    count = len(customers)
    top_end, middle_end = math.ceil(count * 0.2), math.ceil(count * 0.5)
    customers["Value Segment"] = pd.Categorical(
        [
            CUSTOMER_SEGMENTS[0]
            if i < top_end
            else CUSTOMER_SEGMENTS[1]
            if i < middle_end
            else CUSTOMER_SEGMENTS[2]
            for i in range(count)
        ],
        categories=CUSTOMER_SEGMENTS,
        ordered=True,
    )
    summary = (
        customers.groupby("Value Segment", observed=False)
        .agg(
            customer_count=("Customer ID", "size"),
            Profit=("Profit", "sum"),
        )
        .reset_index()
    )
    total_profit = customers["Profit"].sum()
    summary["Net Profit Share %"] = (
        summary["Profit"] / total_profit * 100 if total_profit > 0 else float("nan")
    )
    return customers, summary


def calculate_region_performance(df: pd.DataFrame) -> pd.DataFrame:
    """Regional results; order value uses selected sales per distinct order."""
    result = calculate_performance(df, "Region")
    result["Selected Sales per Order"] = [
        safe_divide(sales, orders)
        for sales, orders in zip(result["Sales"], result["unique_order_count"])
    ]
    return result.sort_values("Sales", ascending=False)


def calculate_quarterly_performance(df: pd.DataFrame) -> pd.DataFrame:
    """Compare calendar quarters pooled over selected years using weighted margins."""
    return calculate_performance(
        df.assign(Quarter=df["Order Date"].dt.quarter), "Quarter"
    )
