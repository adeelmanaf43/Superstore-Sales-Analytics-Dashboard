"""Small, independently checkable examples for dashboard calculations."""

from datetime import date

import pandas as pd
import pytest

from src import analytics
from src.data import filter_data, load_data, validate_data
from src.insights import generate_insights


@pytest.fixture
def transactions():
    return validate_data(
        pd.DataFrame(
            {
                "Order ID": ["O1", "O1", "O2", "O3", "O4"],
                "Order Date": [
                    "2024-01-01",
                    "2024-01-01",
                    "2024-04-01",
                    "2024-10-01",
                    "2024-10-02",
                ],
                "Ship Date": ["2024-01-03"] * 5,
                "Sales": [100, 100, 100, 100, 100],
                "Profit": [20, -10, 0, -30, 5],
                "Discount": [0, 0.25, 0.25, 0.8, 1],
                "Category": ["A", "B", "A", "B", "A"],
                "Sub-Category": ["S"] * 5,
                "Region": ["East"] * 5,
                "Segment": ["Consumer"] * 5,
                "Customer ID": ["C1", "C1", "C2", "C3", "C4"],
                "Customer Name": ["One", "One", "Two", "Three", "Four"],
                "Product Name": ["Product"] * 5,
            }
        )
    )


def test_safe_division():
    assert analytics.safe_divide(6, 3) == 2
    assert analytics.safe_divide(6, 0) == 0
    assert analytics.safe_divide(0, 0, default=-1) == -1
    assert analytics.safe_divide(-6, 3) == -2


def test_transaction_and_order_counts(transactions):
    result = analytics.calculate_kpis(transactions)
    assert result["transaction_count"] == 5
    assert result["unique_order_count"] == 4
    assert result["unprofitable_transaction_rate"] == 40
    assert result["profit_margin"] == -3
    region = analytics.calculate_region_performance(transactions).iloc[0]
    assert region["Selected Sales per Order"] == 125


def test_discount_rates_include_zero_full_discount_and_break_even(transactions):
    result = analytics.calculate_discount_profitability(transactions).set_index(
        "Discount"
    )
    assert result["transaction_count"].sum() == 5
    assert result.loc[0, "profitable_transaction_rate"] == 100
    assert result.loc[1, "profitable_transaction_rate"] == 100
    assert result.loc[0.25, "transaction_count"] == 2
    assert result.loc[0.25, "profitable_transaction_rate"] == 0
    assert result.loc[0.25, "unprofitable_transaction_rate"] == 50
    assert result.loc[0.25, "break_even_transaction_rate"] == 50
    assert result["transaction_share"].sum() == pytest.approx(100)


def test_threshold_is_inclusive_and_gross_loss_differs_from_net(transactions):
    result = analytics.calculate_discount_loss_exposure(transactions)
    assert result["transaction_count"] == 4
    assert result["unprofitable_transaction_count"] == 2
    assert result["unprofitable_transaction_rate"] == 50
    assert result["gross_loss_exposure"] == 40
    assert result["net_profit"] == -35
    segments = analytics.calculate_discount_segments(transactions)
    assert segments["transaction_count"].tolist() == [1, 4]
    assert segments["profitable_transaction_rate"].tolist() == [100, 25]
    assert (
        analytics.calculate_discount_loss_exposure(transactions, 1)["transaction_count"]
        == 1
    )
    with pytest.raises(ValueError, match="threshold"):
        analytics.calculate_discount_loss_exposure(transactions, 1.1)


def test_customer_rank_ties_rounding_and_negative_denominator(transactions):
    customers, summary = analytics.calculate_customer_value_segments(transactions)
    assert customers["Customer ID"].tolist() == ["C1", "C4", "C2", "C3"]
    assert summary["customer_count"].tolist() == [1, 1, 2]
    assert summary["Net Profit Share %"].isna().all()
    tied = transactions.copy()
    tied["Profit"] = [5, 5, 10, 10, 10]
    customers, _ = analytics.calculate_customer_value_segments(
        tied.sample(frac=1, random_state=1)
    )
    assert customers["Customer ID"].tolist() == ["C1", "C2", "C3", "C4"]


def test_customer_shares_may_exceed_100_and_single_customer(transactions):
    sample = transactions.iloc[:3].copy()
    sample["Profit"] = [50, 50, -20]
    _, summary = analytics.calculate_customer_value_segments(sample)
    assert summary.iloc[0]["Net Profit Share %"] == 125
    assert summary["Net Profit Share %"].sum() == pytest.approx(100)
    _, one = analytics.calculate_customer_value_segments(sample.iloc[:1])
    assert one["customer_count"].tolist() == [1, 0, 0]


def test_zero_sales(transactions):
    transactions["Sales"] = 0
    assert analytics.calculate_kpis(transactions)["profit_margin"] == 0
    assert (
        analytics.calculate_performance(transactions, "Category")["Profit Margin %"]
        == 0
    ).all()


def test_empty_data(transactions):
    empty = transactions.iloc[:0]
    assert all(value == 0 for value in analytics.calculate_kpis(empty).values())
    assert analytics.calculate_discount_profitability(empty).empty
    assert analytics.calculate_discount_loss_exposure(empty)["gross_loss_exposure"] == 0
    assert analytics.calculate_discount_segments(empty)["transaction_count"].sum() == 0
    customers, summary = analytics.calculate_customer_value_segments(empty)
    assert customers.empty
    assert summary["customer_count"].sum() == 0
    assert analytics.calculate_region_performance(empty).empty
    assert analytics.calculate_monthly_performance(empty).empty
    assert analytics.calculate_quarterly_performance(empty).empty
    assert generate_insights(empty) == []


def test_validation_missing_column(transactions):
    with pytest.raises(ValueError, match="missing required columns: Order ID"):
        validate_data(transactions.drop(columns="Order ID"))


@pytest.mark.parametrize(
    "column,value,match",
    [
        ("Sales", "bad", "finite numeric"),
        ("Profit", float("inf"), "finite numeric"),
        ("Discount", 1.1, "fraction"),
        ("Order Date", "bad", "invalid dates"),
        ("Customer ID", " ", "blank values"),
        ("Region", None, "missing values"),
        ("Sales", -1, "nonnegative"),
    ],
)
def test_validation_bad_values(transactions, column, value, match):
    invalid = transactions.astype({column: object})
    invalid.loc[0, column] = value
    with pytest.raises(ValueError, match=match):
        validate_data(invalid)


def test_inclusive_filters_and_partial_orders(transactions):
    result = filter_data(transactions, date(2024, 1, 1), date(2024, 1, 1), category="A")
    assert len(result) == 1
    assert analytics.calculate_kpis(result)["unique_order_count"] == 1
    assert filter_data(transactions, region="West").empty
    assert filter_data(transactions, segment="Corporate").empty
    assert len(transactions) == 5


def test_weighted_quarter_margin(transactions):
    result = analytics.calculate_quarterly_performance(transactions).set_index(
        "Quarter"
    )
    assert result.loc[1, "Profit Margin %"] == 5
    assert result.loc[4, "Profit Margin %"] == -12.5


def test_insights_follow_selection(transactions):
    narrative = generate_insights(transactions)[0][1]
    assert "2 of 4" in narrative
    assert "$40.00" in narrative
    assert "No transactions meet" in generate_insights(transactions.iloc[:1])[0][1]


def test_repo_relative_path(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    assert not load_data().empty
    with pytest.raises(FileNotFoundError, match="Dataset not found"):
        load_data(tmp_path / "missing.csv")
