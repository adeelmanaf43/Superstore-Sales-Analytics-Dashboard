"""Charts must represent losses and zero-sales data without hidden omissions."""

import pandas as pd

from src.charts import discount_scatter, region_profit_chart


def test_regional_losses_use_bars():
    data = pd.DataFrame({"Region": ["East", "West"], "Profit": [100, -20]})
    figure = region_profit_chart(data)
    assert figure.data[0].type == "bar"
    assert list(figure.data[0].y) == [100, -20]


def test_nonnegative_regional_profits_use_donut():
    data = pd.DataFrame({"Region": ["East", "West"], "Profit": [100, 20]})
    assert region_profit_chart(data).data[0].type == "pie"
    data["Profit"] = 0
    assert region_profit_chart(data).data[0].type == "bar"


def test_zero_sales_scatter_is_serializable():
    data = pd.DataFrame(
        {
            "Discount": [0],
            "Profit": [0],
            "Sales": [0],
            "Category": ["A"],
            "Product Name": ["Product"],
            "Region": ["East"],
            "Segment": ["Consumer"],
        }
    )
    assert discount_scatter(data, 0.25).to_json()
