"""Streamlit integration smoke tests; pure analytics tests run separately."""

from datetime import date
from pathlib import Path

from streamlit.testing.v1 import AppTest

from src.analytics import calculate_kpis
from src.data import filter_data, load_data

APP = Path(__file__).resolve().parents[1] / "streamlit_app.py"


def test_all_tabs_and_combined_filters():
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not app.exception
    assert len(app.tabs) == 6
    assert len(app.get("plotly_chart")) == 11
    assert app.metric[2].value == "12.47%"
    app.selectbox[0].select("Furniture")
    app.selectbox[1].select("Central")
    app.selectbox[2].select("Consumer")
    app.date_input[0].set_value((date(2013, 1, 1), date(2013, 12, 31)))
    app.run()
    assert not app.exception
    expected = calculate_kpis(
        filter_data(
            load_data(),
            date(2013, 1, 1),
            date(2013, 12, 31),
            category="Furniture",
            region="Central",
            segment="Consumer",
        )
    )
    assert app.metric[0].value == f"${expected['sales']:,.0f}"
    assert app.metric[2].value == f"{expected['profit_margin']:.2f}%"
    assert app.metric[3].value == f"{expected['unique_order_count']:,}"
    assert app.metric[4].value == f"{expected['unprofitable_transaction_rate']:.2f}%"


def test_empty_and_incomplete_date_filters():
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.selectbox[0].select("Technology")
    app.selectbox[1].select("West")
    app.date_input[0].set_value((date(2011, 1, 4), date(2011, 1, 4))).run()
    assert not app.exception
    assert "No transactions match" in app.warning[0].value
    assert app.metric[2].value == "0.00%"
    app.date_input[0].set_value((date(2011, 1, 4),)).run()
    assert not app.exception
    assert "both a start and an end" in app.info[0].value
