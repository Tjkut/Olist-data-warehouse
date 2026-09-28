"""
Chart builder functions for the Olist Dashboard.

Uses Plotly to create interactive charts consumed by Streamlit pages.
Each function receives a pandas DataFrame (output of run_query) and
returns a plotly.graph_objects.Figure ready for st.plotly_chart().
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import json
from pathlib import Path


# ---------------------------------------------------------------------------
# Color palette & layout defaults
# ---------------------------------------------------------------------------
COLORS = {
    "primary": "#FF4B4B",        # Primary Red/Coral from .streamlit/config.toml
    "primary_light": "#FFA8A8",  # Light coral
    "accent": "#F59E0B",         # Amber-500
    "bg": "#FFFFFF",             # Pure white from config.toml
    "card_bg": "#F0F2F6",        # Secondary bg from config.toml
    "text": "#31333F",           # Dark text from config.toml
    "grid": "#E2E8F0",           # Slate-200 border / grid lines
}

_LAYOUT_DEFAULTS = dict(
    paper_bgcolor=COLORS["bg"],
    plot_bgcolor=COLORS["bg"],
    font=dict(family="Inter, sans-serif", color=COLORS["text"], size=13),
    margin=dict(l=60, r=30, t=50, b=50),
    hovermode="x unified",
)


def _apply_axis_style(fig: go.Figure) -> go.Figure:
    """Apply consistent axis styling across all charts."""
    fig.update_xaxes(
        showgrid=False,
        linecolor=COLORS["grid"],
        tickfont=dict(size=11, color=COLORS["text"]),
        title_font=dict(color=COLORS["text"]),
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor=COLORS["grid"],
        gridwidth=0.5,
        linecolor=COLORS["grid"],
        tickfont=dict(size=11, color=COLORS["text"]),
        title_font=dict(color=COLORS["text"]),
    )
    return fig


# ---------------------------------------------------------------------------
# 1. Monthly Revenue — Area chart
# ---------------------------------------------------------------------------
def monthly_revenue_chart(df: pd.DataFrame) -> go.Figure:
    """Create an area chart showing monthly revenue trend.

    Args:
        df: DataFrame with columns [year_month, total_revenue].

    Returns:
        go.Figure: Interactive area chart.
    """
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["year_month"],
        y=df["total_revenue"],
        mode="lines+markers",
        name="Doanh thu (BRL)",
        line=dict(color=COLORS["primary"], width=2.5, shape="spline"),
        marker=dict(size=5, color=COLORS["primary_light"]),
        fill="tozeroy",
        fillcolor="rgba(255, 75, 75, 0.12)",
        hovertemplate="<b>%{x}</b><br>Doanh thu: R$ %{y:,.2f}<extra></extra>",
    ))

    fig.update_layout(
        title=dict(text="Doanh thu theo tháng", font=dict(size=18)),
        xaxis_title="Tháng",
        yaxis_title="Doanh thu (BRL)",
        **_LAYOUT_DEFAULTS,
    )

    return _apply_axis_style(fig)


# ---------------------------------------------------------------------------
# 2. Monthly Revenue — Bar chart (alternative view)
# ---------------------------------------------------------------------------
def monthly_revenue_bar_chart(df: pd.DataFrame) -> go.Figure:
    """Create a bar chart showing monthly revenue.

    Args:
        df: DataFrame with columns [year_month, total_revenue].

    Returns:
        go.Figure: Interactive bar chart.
    """
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df["year_month"],
        y=df["total_revenue"],
        name="Doanh thu (BRL)",
        marker=dict(
            color=df["total_revenue"],
            colorscale=[[0, COLORS["primary_light"]], [1, COLORS["primary"]]],
            line=dict(width=0),
            cornerradius=4,
        ),
        hovertemplate="<b>%{x}</b><br>Doanh thu: R$ %{y:,.2f}<extra></extra>",
    ))

    fig.update_layout(
        title=dict(text="Doanh thu theo tháng", font=dict(size=18)),
        xaxis_title="Tháng",
        yaxis_title="Doanh thu (BRL)",
        bargap=0.15,
        **_LAYOUT_DEFAULTS,
    )

    return _apply_axis_style(fig)


# ---------------------------------------------------------------------------
# 3. Orders by Day of Week — Bar chart
# ---------------------------------------------------------------------------
def orders_by_day_of_week_chart(df: pd.DataFrame) -> go.Figure:
    """Create a bar chart showing total orders by day of week.

    Args:
        df: DataFrame with columns [day_name, total_orders]
            ordered Monday → Sunday (day_of_week 2 → 8, Sunday = 1 → 8).

    Returns:
        go.Figure: Interactive bar chart.
    """
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df["day_name"],
        y=df["total_orders"],
        name="Số đơn hàng",
        marker=dict(
            color=df["total_orders"],
            colorscale=[[0, "#FEE2E2"], [0.5, "#F87171"], [1, COLORS["primary"]]],
            line=dict(width=0),
            cornerradius=6,
        ),
        hovertemplate="<b>%{x}</b><br>Số đơn: %{y:,}<extra></extra>",
    ))

    fig.update_layout(
        title=dict(text="Đơn hàng theo ngày trong tuần", font=dict(size=18)),
        xaxis_title="Ngày trong tuần",
        yaxis_title="Số đơn hàng",
        bargap=0.2,
        **_LAYOUT_DEFAULTS,
    )

    return _apply_axis_style(fig)


# ---------------------------------------------------------------------------
# 4. Top 10 Product Categories by Revenue — Horizontal Bar chart
# ---------------------------------------------------------------------------
def top10_category_revenue_chart(df: pd.DataFrame) -> go.Figure:
    """Create a horizontal bar chart for top 10 product categories by revenue.

    Args:
        df: DataFrame with columns [category, total_revenue],
            ordered descending by total_revenue.

    Returns:
        go.Figure: Interactive horizontal bar chart.
    """
    # Ensure top 10 and reverse so highest value appears at the top
    df_top10 = df.head(10).iloc[::-1].reset_index(drop=True)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df_top10["total_revenue"],
        y=df_top10["category"],
        orientation="h",
        name="Doanh thu (BRL)",
        marker=dict(
            color=df_top10["total_revenue"],
            colorscale=[[0, COLORS["primary_light"]], [1, COLORS["primary"]]],
            line=dict(width=0),
            cornerradius=4,
        ),
        hovertemplate="<b>%{y}</b><br>Doanh thu: R$ %{x:,.2f}<extra></extra>",
    ))

    fig.update_layout(
        title=dict(text="Top 10 danh mục sản phẩm theo doanh thu", font=dict(size=18)),
        xaxis_title="Doanh thu (BRL)",
        yaxis_title="Danh mục sản phẩm",
        **_LAYOUT_DEFAULTS,
    )

    return _apply_axis_style(fig)


# ---------------------------------------------------------------------------
# 5. Top 10 Product Categories by Sales Quantity — Horizontal Bar chart
# ---------------------------------------------------------------------------
def top10_category_quantity_chart(df: pd.DataFrame) -> go.Figure:
    """Create a horizontal bar chart for top 10 product categories by sales quantity.

    Args:
        df: DataFrame with columns [category, total_quantity],
            ordered descending by total_quantity.

    Returns:
        go.Figure: Interactive horizontal bar chart.
    """
    # Ensure top 10 and reverse so highest value appears at the top
    df_top10 = df.head(10).iloc[::-1].reset_index(drop=True)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df_top10["total_quantity"],
        y=df_top10["category"],
        orientation="h",
        name="Số lượng bán",
        marker=dict(
            color=df_top10["total_quantity"],
            colorscale=[[0, "#93C5FD"], [1, "#2563EB"]],
            line=dict(width=0),
            cornerradius=4,
        ),
        hovertemplate="<b>%{y}</b><br>Số lượng bán: %{x:,} sản phẩm<extra></extra>",
    ))

    fig.update_layout(
        title=dict(text="Top 10 danh mục sản phẩm theo số lượng bán", font=dict(size=18)),
        xaxis_title="Số lượng bán (sản phẩm)",
        yaxis_title="Danh mục sản phẩm",
        **_LAYOUT_DEFAULTS,
    )

    return _apply_axis_style(fig)



# ---------------------------------------------------------------------------
# 5. Average Price by Product Category — Horizontal Bar chart
# ---------------------------------------------------------------------------
def avg_price_by_category_chart(df: pd.DataFrame) -> go.Figure:
    """Create a horizontal bar chart for average product price by category.

    Args:
        df: DataFrame with columns [category, avg_price],
            ordered descending by avg_price.

    Returns:
        go.Figure: Interactive horizontal bar chart.
    """
    # Only display top 10 categories
    df_top10 = df.head(10)

    # Reverse so highest value appears at the top
    df_top10 = df_top10.iloc[::-1].reset_index(drop=True)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df_top10["avg_price"],
        y=df_top10["category"],
        orientation="h",
        name="Giá trung bình (BRL)",
        marker=dict(
            color=df_top10["avg_price"],
            colorscale=[[0, "#FDE68A"], [1, COLORS["accent"]]],
            line=dict(width=0),
            cornerradius=4,
        ),
        hovertemplate="<b>%{y}</b><br>Giá trung bình: R$ %{x:,.2f}<extra></extra>",
    ))

    fig.update_layout(
        title=dict(text="Top 10 danh mục có giá trung bình cao nhất", font=dict(size=18)),
        xaxis_title="Giá trung bình (BRL)",
        yaxis_title="Danh mục sản phẩm",
        **_LAYOUT_DEFAULTS,
    )

    return _apply_axis_style(fig)


# ---------------------------------------------------------------------------
# 7. Customers by State — Bar chart
# ---------------------------------------------------------------------------
def customers_by_state_chart(df: pd.DataFrame) -> go.Figure:
    """Create a bar chart showing customer count by Brazilian state.

    Args:
        df: DataFrame with columns [state, total_customers],
            ordered descending by total_customers.

    Returns:
        go.Figure: Interactive bar chart.
    """
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df["state"],
        y=df["total_customers"],
        name="Số khách hàng",
        marker=dict(
            color=df["total_customers"],
            colorscale=[[0, "#93C5FD"], [1, COLORS["primary"]]],
            line=dict(width=0),
            cornerradius=4,
        ),
        hovertemplate="<b>Bang: %{x}</b><br>Số khách hàng: %{y:,}<extra></extra>",
    ))

    fig.update_layout(
        title=dict(text="Phân bố số lượng khách hàng theo bang (Brazil)", font=dict(size=18)),
        xaxis_title="Bang (State)",
        yaxis_title="Số khách hàng",
        bargap=0.2,
        **_LAYOUT_DEFAULTS,
    )

    return _apply_axis_style(fig)


# ---------------------------------------------------------------------------
# 8. Top 10 Cities by Customer Count — Horizontal Bar chart
# ---------------------------------------------------------------------------
def top10_cities_customer_chart(df: pd.DataFrame) -> go.Figure:
    """Create a horizontal bar chart for top 10 cities by customer count.

    Args:
        df: DataFrame with columns [city, state, total_customers] or [city_label, total_customers],
            ordered descending by total_customers.

    Returns:
        go.Figure: Interactive horizontal bar chart.
    """
    df_top10 = df.head(10).copy()

    # Create city_label if not present
    if "city_label" not in df_top10.columns:
        if "state" in df_top10.columns:
            df_top10["city_label"] = df_top10["city"] + " (" + df_top10["state"] + ")"
        else:
            df_top10["city_label"] = df_top10["city"]

    # Reverse so highest value appears at the top
    df_top10 = df_top10.iloc[::-1].reset_index(drop=True)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df_top10["total_customers"],
        y=df_top10["city_label"],
        orientation="h",
        name="Số khách hàng",
        marker=dict(
            color=df_top10["total_customers"],
            colorscale=[[0, "#A7F3D0"], [1, "#059669"]],  # Emerald green
            line=dict(width=0),
            cornerradius=4,
        ),
        hovertemplate="<b>%{y}</b><br>Số khách hàng: %{x:,}<extra></extra>",
    ))

    fig.update_layout(
        title=dict(text="Top 10 thành phố có nhiều khách hàng nhất", font=dict(size=18)),
        xaxis_title="Số khách hàng",
        yaxis_title="Thành phố (Bang)",
        **_LAYOUT_DEFAULTS,
    )

    return _apply_axis_style(fig)


# ---------------------------------------------------------------------------
# 9. One-time vs Repeat Customers — Donut / Pie chart
# ---------------------------------------------------------------------------
def repeat_customers_pie_chart(df: pd.DataFrame) -> go.Figure:
    """Create a pie/donut chart showing One-time vs Repeat customers.

    Args:
        df: DataFrame with columns [one_time_customers, repeat_customers]

    Returns:
        go.Figure: Interactive pie/donut chart.
    """
    one_time = int(df["one_time_customers"].iloc[0])
    repeat = int(df["repeat_customers"].iloc[0])

    labels = ["Khách mua 1 lần", "Khách quay lại (≥ 2 lần)"]
    values = [one_time, repeat]
    colors = [COLORS["primary"], COLORS["accent"]]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.55,
        marker=dict(colors=colors, line=dict(color=COLORS["bg"], width=2)),
        textinfo="label+percent",
        textfont=dict(size=13),
        hovertemplate="<b>%{label}</b><br>Số lượng: %{value:,} khách<br>Tỷ lệ: %{percent}<extra></extra>",
    )])

    fig.update_layout(
        title=dict(text="Tỷ lệ khách hàng mua lại (Repeat Purchase Rate)", font=dict(size=18)),
        legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5),
        **_LAYOUT_DEFAULTS,
    )

    return fig


# ---------------------------------------------------------------------------
# 10. Delivery Time vs Review Score — Scatter plot
# ---------------------------------------------------------------------------
def delivery_time_vs_review_scatter(df: pd.DataFrame) -> go.Figure:
    """Create a scatter plot showing Effect of Delivery Day on Customer's Review.

    Args:
        df: DataFrame with columns [delivery_status, delivery_day, avg_review_score, order_count]

    Returns:
        go.Figure: Interactive scatter plot matching the reference design.
    """
    fig = go.Figure()

    # Colors matching screenshot: Late (dark blue), On Time (light blue)
    colors = {
        "Late": "#2563EB",     # Darker blue
        "On Time": "#60A5FA",  # Lighter blue
    }

    # Add points for Late and On Time
    for status in ["Late", "On Time"]:
        df_sub = df[df["delivery_status"] == status]
        if not df_sub.empty:
            fig.add_trace(go.Scatter(
                x=df_sub["avg_review_score"],
                y=df_sub["delivery_day"],
                mode="markers",
                name=status,
                marker=dict(
                    size=8,
                    color=colors.get(status, "#93C5FD"),
                    opacity=0.85,
                    line=dict(width=0.5, color="#FFFFFF"),
                ),
                customdata=df_sub["order_count"],
                hovertemplate=(
                    f"<b>{status}</b><br>"
                    "Điểm review: %{x:.2f} ⭐<br>"
                    "Thời gian giao: %{y:.0f} ngày<br>"
                    "Số đơn hàng: %{customdata:,}<extra></extra>"
                ),
            ))

    # Calculate trendline (Linear regression)
    if len(df) > 1:
        x_vals = df["avg_review_score"].astype(float)
        y_vals = df["delivery_day"].astype(float)
        slope, intercept = np.polyfit(x_vals, y_vals, 1)
        x_trend = np.array([1.0, 5.0])
        y_trend = slope * x_trend + intercept

        fig.add_trace(go.Scatter(
            x=x_trend,
            y=y_trend,
            mode="lines",
            name="Trendline",
            showlegend=False,
            line=dict(color="#64748B", width=2, dash="dash"),
            hoverinfo="skip",
        ))

    fig.update_layout(
        title=dict(
            text="Effect of Delivery Day on Customer's Review",
            font=dict(size=18),
            x=0.5,
            xanchor="center",
        ),
        xaxis=dict(
            title="Customer's Review",
            range=[0.8, 5.2],
            tickmode="linear",
            tick0=1,
            dtick=1,
        ),
        yaxis=dict(
            title="Delivery Day",
            range=[-2, 85],
            tickmode="linear",
            tick0=0,
            dtick=20,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
        ),
        **_LAYOUT_DEFAULTS,
    )

    return _apply_axis_style(fig)


# ---------------------------------------------------------------------------
# 11. Average Delivery Time by State — Choropleth Map
# ---------------------------------------------------------------------------
_GEOJSON_PATH = Path(__file__).parent / "assets" / "brazil_states.geojson"

# Approximate centroid coordinates for all 27 Brazilian states (lat, lon)
_BRAZIL_STATE_CENTROIDS = {
    "AC": (-8.77, -70.55),   "AL": (-9.57, -36.78),
    "AM": (-3.47, -65.10),   "AP": (1.41, -51.77),
    "BA": (-12.96, -41.68),  "CE": (-5.20, -39.53),
    "DF": (-15.83, -47.86),  "ES": (-19.19, -40.34),
    "GO": (-15.98, -49.86),  "MA": (-5.42, -45.44),
    "MG": (-18.10, -44.38),  "MS": (-20.51, -54.54),
    "MT": (-12.64, -55.42),  "PA": (-3.79, -52.48),
    "PB": (-7.28, -36.72),   "PE": (-8.38, -37.86),
    "PI": (-7.72, -42.73),   "PR": (-24.89, -51.55),
    "RJ": (-22.25, -42.66),  "RN": (-5.81, -36.59),
    "RO": (-10.83, -63.34),  "RR": (1.99, -61.33),
    "RS": (-29.75, -53.25),  "SC": (-27.45, -50.95),
    "SE": (-10.57, -37.45),  "SP": (-22.19, -48.79),
    "TO": (-10.18, -48.33),
}


def delivery_time_by_state_map(df: pd.DataFrame) -> go.Figure:
    """Create a choropleth map showing average delivery days per Brazilian state.

    Args:
        df: DataFrame with columns [customer_state, avg_delivery_days, delivered_orders].

    Returns:
        go.Figure: Interactive choropleth map ready for st.plotly_chart().
    """
    with open(_GEOJSON_PATH, "r", encoding="utf-8") as f:
        brazil_geojson = json.load(f)

    # Blue gradient: light blue (fast) → dark blue (slow)
    blue_scale = [
        [0.0, "#DBEAFE"],   # Blue-100  (fastest)
        [0.25, "#93C5FD"],  # Blue-300
        [0.5, "#3B82F6"],   # Blue-500
        [0.75, "#1D4ED8"],  # Blue-700
        [1.0, "#1E3A5F"],   # Navy      (slowest)
    ]

    fig = px.choropleth(
        df,
        geojson=brazil_geojson,
        locations="customer_state",
        featureidkey="properties.sigla",
        color="avg_delivery_days",
        color_continuous_scale=blue_scale,
        hover_name="customer_state",
        hover_data={
            "customer_state": False,
            "avg_delivery_days": ":.2f",
            "delivered_orders": ":,",
        },
        labels={
            "avg_delivery_days": "Giao TB (ngày)",
            "delivered_orders": "Số đơn đã giao",
        },
    )

    # --- Add state name labels on the map ---
    label_lats = []
    label_lons = []
    label_texts = []
    for _, row in df.iterrows():
        sigla = row["customer_state"]
        if sigla in _BRAZIL_STATE_CENTROIDS:
            lat, lon = _BRAZIL_STATE_CENTROIDS[sigla]
            label_lats.append(lat)
            label_lons.append(lon)
            label_texts.append(sigla)

    fig.add_trace(go.Scattergeo(
        lat=label_lats,
        lon=label_lons,
        text=label_texts,
        mode="text",
        textfont=dict(size=10, color="#1E293B", family="Inter, sans-serif"),
        showlegend=False,
        hoverinfo="skip",
    ))

    fig.update_geos(
        fitbounds="locations",
        visible=False,
        bgcolor="rgba(0,0,0,0)",
    )

    fig.update_layout(
        title=dict(
            text="Thời gian giao hàng trung bình theo bang",
            font=dict(size=18, color=COLORS["text"]),
            x=0.5,
            xanchor="center",
        ),
        height=800,
        paper_bgcolor=COLORS["bg"],
        plot_bgcolor=COLORS["bg"],
        geo=dict(bgcolor="rgba(0,0,0,0)"),
        font=dict(family="Inter, sans-serif", color=COLORS["text"], size=13),
        margin=dict(l=10, r=10, t=50, b=10),
        coloraxis_colorbar=dict(
            title="Ngày",
            tickfont=dict(color=COLORS["text"]),
            titlefont=dict(color=COLORS["text"]),
        ),
    )

    return fig

