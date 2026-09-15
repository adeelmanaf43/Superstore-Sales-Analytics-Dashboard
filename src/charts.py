"""Plotly figure construction from prepared analytics results."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def bar_chart(
    data: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    color: str | None = None,
    orientation: str = "v",
) -> go.Figure:
    """Construct an automatically scaled performance bar chart."""
    fig = px.bar(
        data,
        x=x,
        y=y,
        color=color,
        orientation=orientation,
        title=title,
        color_continuous_scale="RdYlGn",
    )
    fig.update_layout(template="plotly_white", height=400)
    return fig


def dual_axis_chart(
    data: pd.DataFrame,
    x: str,
    secondary: str,
    title: str,
    trend: bool = False,
) -> go.Figure:
    """Show sales and a separately labeled profit or margin series."""
    fig = go.Figure()
    sales = {"x": data[x], "y": data["Sales"], "name": "Sales"}
    if trend:
        fig.add_trace(
            go.Scatter(**sales, line={"color": "#3498db", "width": 3}, fill="tozeroy")
        )
    else:
        fig.add_trace(go.Bar(**sales, marker_color="lightblue"))
    fig.add_trace(
        go.Scatter(
            x=data[x],
            y=data[secondary],
            name=secondary,
            yaxis="y2",
            mode="lines+markers",
            line={"color": "#2ecc71", "width": 3},
        )
    )
    fig.update_layout(
        title=title,
        xaxis_title="Date" if trend else x,
        yaxis_title="Sales ($)",
        yaxis2={
            "title": "Profit ($)" if secondary == "Profit" else secondary,
            "overlaying": "y",
            "side": "right",
        },
        hovermode="x unified",
        template="plotly_white",
        height=400,
    )
    return fig


def margin_heatmap(data: pd.DataFrame) -> go.Figure:
    """Plot prepared category/region margins; absent combinations remain blank."""
    pivot = data.pivot(index="Category", columns="Region", values="Profit Margin %")
    fig = go.Figure(
        go.Heatmap(
            z=pivot.values,
            x=pivot.columns,
            y=pivot.index,
            colorscale="RdYlGn",
            text=pivot.values,
            texttemplate="%{text:.1f}%",
            colorbar={"title": "Margin %"},
        )
    )
    fig.update_layout(
        title="Profit Margin by Category and Region",
        template="plotly_white",
        height=400,
    )
    return fig


def discount_profitability_chart(data: pd.DataFrame) -> go.Figure:
    """Plot profitable-transaction rate at each observed exact discount."""
    fig = go.Figure(
        go.Bar(
            x=[f"{value:.2%}" for value in data["Discount"]],
            y=data["profitable_transaction_rate"],
            text=data["profitable_transaction_rate"],
            texttemplate="%{text:.1f}%",
            textposition="outside",
            marker_color=data["profitable_transaction_rate"],
            marker_colorscale="RdYlGn",
            marker_cmin=0,
            marker_cmax=100,
            customdata=data[["transaction_count", "transaction_share"]].to_numpy(),
            hovertemplate=(
                "Discount: %{x}<br>Profitable transactions: %{y:.2f}%"
                "<br>Transactions: %{customdata[0]}"
                "<br>Share of selected transactions: %{customdata[1]:.2f}%<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        title="Transaction Profitability by Exact Discount",
        xaxis_title="Discount",
        yaxis_title="Profitable Transactions (%)",
        template="plotly_white",
        height=500,
    )
    return fig


def discount_scatter(df: pd.DataFrame, threshold: float) -> go.Figure:
    """Show individual transaction profit versus discount, sized by sales."""
    fig = px.scatter(
        df,
        x="Discount",
        y="Profit",
        color="Category",
        size="Sales",
        hover_data=["Product Name", "Region", "Segment"],
        opacity=0.6,
    )
    fig.add_hline(y=0, line_dash="dash", line_color="red")
    fig.add_vline(x=threshold, line_dash="dash", line_color="orange")
    fig.update_xaxes(tickformat=".0%")
    fig.update_layout(
        template="plotly_white", height=500, yaxis_title="Transaction Profit ($)"
    )
    return fig


def region_profit_chart(data: pd.DataFrame) -> go.Figure:
    """Use a donut only for nonnegative profit; bars faithfully show losses."""
    if data.empty or (data["Profit"] < 0).any() or data["Profit"].sum() <= 0:
        return bar_chart(data, "Region", "Profit", "Net Profit by Region", "Profit")
    fig = px.pie(
        data,
        values="Profit",
        names="Region",
        title="Profit Distribution by Region",
        hole=0.4,
    )
    fig.update_layout(template="plotly_white", height=400)
    return fig
