"""Streamlit entry point: controls, layout, and rendering only."""

from pathlib import Path

import pandas as pd
import streamlit as st

from src import analytics, charts
from src.data import filter_data, load_data
from src.insights import generate_insights

st.set_page_config(
    page_title="Sales Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
style_path = Path(__file__).resolve().parent / "assets" / "dashboard.css"
st.markdown(
    f"<style>{style_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True
)


@st.cache_data(ttl=600)
def load_cached_data() -> pd.DataFrame:
    """Cache validated input for ten minutes."""
    return load_data()


def show_chart(figure) -> None:
    """Render a prepared Plotly figure at the available column width."""
    st.plotly_chart(figure, use_container_width=True)


def show_table(data: pd.DataFrame) -> None:
    """Apply readable financial formats without a plotting dependency."""
    labels = {
        "transaction_count": "Transactions",
        "unique_order_count": "Unique Orders",
        "customer_count": "Customers",
    }
    display = data.rename(columns=labels)
    formats = {
        column: "${:,.2f}"
        for column in ("Sales", "Profit", "Selected Sales per Order")
        if column in display
    }
    formats.update({column: "{:.2f}%" for column in display if column.endswith("%")})
    st.dataframe(
        display.style.format(formats, na_rep="N/A"),
        use_container_width=True,
        hide_index=True,
    )


try:
    df = load_cached_data()
except (OSError, ValueError, pd.errors.ParserError) as error:
    st.error(f"Unable to load dashboard data: {error}")
    st.stop()
if df.empty:
    st.warning("The dataset has no transactions. Add data before using the dashboard.")
    st.stop()

st.sidebar.title("🎯 Dashboard Controls")
st.sidebar.subheader("📅 Date Range")
date_range = st.sidebar.date_input(
    "Select Date Range",
    value=(df["Order Date"].min().date(), df["Order Date"].max().date()),
    min_value=df["Order Date"].min().date(),
    max_value=df["Order Date"].max().date(),
)
selected = {}
for column in ("Category", "Region", "Segment"):
    st.sidebar.subheader("Customer Segment" if column == "Segment" else column)
    value = st.sidebar.selectbox(
        f"Select {column}", ["All"] + sorted(df[column].unique())
    )
    selected[column.lower()] = None if value == "All" else value

st.title("📊 Sales Analytics Dashboard")
st.markdown("### Superstore Profitability Analysis & Business Intelligence")
if len(date_range) != 2:
    st.info("Select both a start and an end date to update the dashboard.")
    st.stop()
filtered_df = filter_data(df, date_range[0], date_range[1], **selected)
st.caption(
    f"All metrics, charts, and findings use the active filters: {date_range[0]} to {date_range[1]}. "
    "A transaction is one line item; an order is a distinct Order ID among selected line items. "
    "Category filters can select only part of an order."
)
st.subheader("🎯 Key Performance Indicators")
kpis = analytics.calculate_kpis(filtered_df)
for column, label, value in zip(
    st.columns(5),
    (
        "💰 Total Sales",
        "📈 Total Profit",
        "💹 Profit Margin",
        "📦 Unique Orders",
        "Loss-making Transactions",
    ),
    (
        f"${kpis['sales']:,.0f}",
        f"${kpis['profit']:,.0f}",
        f"{kpis['profit_margin']:.2f}%",
        f"{kpis['unique_order_count']:,}",
        f"{kpis['unprofitable_transaction_rate']:.2f}%",
    ),
):
    column.metric(label, value)
st.caption(
    f"{kpis['transaction_count']:,} selected transactions. Profit > 0 is profitable; "
    "Profit < 0 is loss-making; Profit = 0 is break-even. "
    "Margins with zero sales and rates with no transactions display 0% as a fallback."
)
if filtered_df.empty:
    st.warning(
        "No transactions match these filters. Widen the date range or choose All for a filter."
    )
    st.stop()

tabs = st.tabs(
    [
        "📊 Overview",
        "💸 Discount Analysis",
        "👥 Customer Insights",
        "📦 Product Performance",
        "Regional Analysis",
        "🎯 Key Findings",
    ]
)
with tabs[0]:
    st.header("Business Overview")
    left, right = st.columns(2)
    with left:
        show_chart(
            charts.dual_axis_chart(
                analytics.calculate_monthly_performance(filtered_df),
                "Order Date",
                "Profit",
                "Sales & Profit Trends Over Time",
                trend=True,
            )
        )
    with right:
        show_chart(
            charts.bar_chart(
                analytics.calculate_performance(filtered_df, "Category"),
                "Category",
                "Sales",
                "Category Performance",
                "Profit Margin %",
            )
        )
    st.subheader("🗺️ Category-Region Profit Margin Heatmap")
    show_chart(
        charts.margin_heatmap(
            analytics.calculate_performance(filtered_df, ["Category", "Region"]),
        )
    )

with tabs[1]:
    st.header("💸 Discount Impact Analysis")
    st.caption(
        "Profitability is the percentage of transactions with Profit > 0 at each exact discount."
    )
    show_chart(
        charts.discount_profitability_chart(
            analytics.calculate_discount_profitability(filtered_df),
        )
    )
    groups = analytics.calculate_discount_segments(filtered_df)
    for column, (_, group) in zip(st.columns(2), groups.iterrows()):
        with column:
            st.subheader(f"Discounts: {group['Discount Group']}")
            st.write(f"Transactions: **{int(group['transaction_count']):,}**")
            st.write(
                f"Average transaction profit: **${group['average_transaction_profit']:,.2f}**"
            )
            st.write(
                f"Profitable transactions: **{group['profitable_transaction_rate']:.2f}%**"
            )
    st.caption(
        f"The {analytics.DISCOUNT_RISK_THRESHOLD:.0%} threshold is descriptive, "
        "not a proven optimal discount cap or a guarantee of profitability."
    )
    st.subheader("Discount vs Transaction Profit")
    show_chart(charts.discount_scatter(filtered_df, analytics.DISCOUNT_RISK_THRESHOLD))

with tabs[2]:
    st.header("👥 Customer Analytics")
    customers, pyramid = analytics.calculate_customer_value_segments(filtered_df)
    left, right = st.columns(2)
    with left:
        value = (
            "Net Profit Share %"
            if pyramid["Net Profit Share %"].notna().all()
            else "Profit"
        )
        show_chart(
            charts.bar_chart(
                pyramid, "Value Segment", value, "Customer Value Pyramid", value
            )
        )
    with right:
        show_chart(
            charts.dual_axis_chart(
                analytics.calculate_performance(filtered_df, "Segment"),
                "Segment",
                "Profit Margin %",
                "Segment Performance",
            )
        )
    st.caption(
        "Customers are ranked by selected-period net profit, with Customer ID breaking ties. "
        "Top 20% uses ceil(0.20 × customer count); the next group ends at ceil(0.50 × count). "
        "Small selections may leave groups empty. Shares use total net profit, may exceed 100% "
        "or be negative, and are N/A when total net profit is nonpositive. These are not lifetime forecasts."
    )
    show_table(pyramid)
    st.subheader("🏆 Top 10 Customers by Selected-Period Profit")
    show_table(customers.head(10).drop(columns="Value Segment"))

with tabs[3]:
    st.header("📦 Product Performance Analysis")
    products = analytics.calculate_performance(filtered_df, "Sub-Category").sort_values(
        "Profit"
    )
    left, right = st.columns(2)
    with left:
        show_chart(
            charts.bar_chart(
                products.tail(10),
                "Profit",
                "Sub-Category",
                "Top 10 Sub-Categories by Profit",
                "Profit Margin %",
                "h",
            )
        )
    with right:
        show_chart(
            charts.bar_chart(
                products.head(10),
                "Profit",
                "Sub-Category",
                "Bottom 10 Sub-Categories by Profit",
                "Profit",
                "h",
            )
        )
    st.subheader("Complete Sub-Category Performance")
    show_table(products.sort_values("Profit Margin %", ascending=False))

with tabs[4]:
    st.header("🗺️ Regional Performance")
    regions = analytics.calculate_region_performance(filtered_df)
    left, right = st.columns(2)
    with left:
        show_chart(
            charts.bar_chart(
                regions,
                "Region",
                "Sales",
                "Regional Sales Performance",
                "Profit Margin %",
            )
        )
    with right:
        show_chart(charts.region_profit_chart(regions))
    st.subheader("Regional Metrics Comparison")
    show_table(regions)
    st.caption(
        "Selected sales per order = selected regional sales / distinct selected Order IDs."
    )

with tabs[5]:
    st.header("🎯 Key Business Insights & Recommendations")
    st.caption(
        "Historical observations from the active filters. No annualization, forecast, or realized savings claim."
    )
    for title, narrative in generate_insights(filtered_df):
        st.subheader(title)
        st.markdown(narrative.replace("$", r"\$"))
    show_table(analytics.calculate_quarterly_performance(filtered_df))
    st.info(
        "Validate pricing changes with controlled experiments and cost information. "
        "This sample does not measure policy changes, acquisition ROI, or causal retention effects."
    )

st.markdown("---")
st.markdown(
    "<div class='footer'><p>Sales Analytics Dashboard | Built with Streamlit & Plotly</p>"
    "<p>Developed by Adeel Manaf | Python &amp; Applied AI Developer</p>"
    "<p><a href='https://github.com/adeelmanaf43'>GitHub</a> | "
    "<a href='https://linkedin.com/in/adeel-manaf'>LinkedIn</a></p></div>",
    unsafe_allow_html=True,
)
