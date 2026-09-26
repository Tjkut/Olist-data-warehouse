"""
Olist E-commerce Dashboard — Overview Page

Hiển thị KPI tổng quan và biểu đồ doanh thu theo tháng.
"""

import streamlit as st
import pandas as pd

from db_connection import run_query
from query import (
    TOTAL_ORDERS_QUERY,
    TOTAL_PRODUCT_REVENUE_QUERY,
    MONTHLY_REVENUE_QUERY,
    DELIVERD_ORDER,
    TOTAL_ORDERS_BY_DATE_OF_HOURS,
)
from charts import (
    monthly_revenue_chart,
    monthly_revenue_bar_chart,
    orders_by_day_of_week_chart,
)

# ---------------------------------------------------------------------------
# Custom CSS — Dark theme (đồng nhất với app.py & charts.py)
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    .stApp {
        background-color: #0F172A;
        color: #F8FAFC;
        font-family: 'Inter', sans-serif;
    }
    [data-testid="stSidebar"] {
        background-color: #1E293B;
    }
    [data-testid="stHeader"],
    [data-testid="stToolbar"] {
        background-color: #0F172A;
    }
    [data-testid="stMetric"] {
        background-color: #1E293B;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 20px 24px;
    }
    [data-testid="stMetricLabel"] {
        color: #94A3B8;
        font-size: 0.9rem;
        font-weight: 500;
    }
    [data-testid="stMetricValue"] {
        color: #F8FAFC;
        font-size: 1.8rem;
        font-weight: 700;
    }
    [data-testid="stRadio"] label { color: #F8FAFC; }
    hr { border-color: #334155; }
    .stAlert {
        background-color: #1E293B;
        border: 1px solid #334155;
        color: #F8FAFC;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Page title & description
# ---------------------------------------------------------------------------
st.markdown("# 🛒 Olist E-commerce Dashboard")
st.markdown(
    "Bảng điều khiển phân tích dữ liệu thương mại điện tử Olist (Brazil). "
    "Dữ liệu được truy vấn trực tiếp từ Data Warehouse schema `warehouse`."
)
st.divider()

# ---------------------------------------------------------------------------
# KPI Section — Total Orders & Total Revenue
# ---------------------------------------------------------------------------
st.markdown("### 📊 Tổng quan")

col_orders, col_revenue, col_delivery = st.columns(3)

# --- KPI: Tổng số đơn hàng ---
try:
    df_orders = run_query(TOTAL_ORDERS_QUERY)
    total_orders = int(df_orders["total_orders"].iloc[0])
except Exception as e:
    total_orders = None
    st.error(f"Không thể truy vấn tổng đơn hàng: {e}")

with col_orders:
    st.metric(
        label="Tổng số đơn hàng",
        value=f"{total_orders:,}" if total_orders is not None else "N/A",
    )

# --- KPI: Tổng doanh thu ---
try:
    df_revenue = run_query(TOTAL_PRODUCT_REVENUE_QUERY)
    total_revenue = float(df_revenue["total_revenue"].iloc[0])
except Exception as e:
    total_revenue = None
    st.error(f"Không thể truy vấn tổng doanh thu: {e}")

with col_revenue:
    st.metric(
        label="Tổng doanh thu",
        value=f"R$ {total_revenue:,.2f}" if total_revenue is not None else "N/A",
    )

# --- KPI: Tỉ lệ giao hàng thành công ---
try:
    df_delivery = run_query(DELIVERD_ORDER)
    delivered_orders = int(df_delivery["delivered_orders"].iloc[0])
    delivery_rate = float(df_delivery["delivery_success_rate_pct"].iloc[0])
except Exception as e:
    delivered_orders = None
    delivery_rate = None
    st.error(f"Không thể truy vấn tỉ lệ giao hàng: {e}")

with col_delivery:
    st.metric(
        label="Tỉ lệ giao hàng thành công",
        value=f"{delivery_rate}%" if delivery_rate is not None else "N/A",
        help=f"Số đơn đã giao: {delivered_orders:,}" if delivered_orders is not None else None,
    )

st.divider()

# ---------------------------------------------------------------------------
# Monthly Revenue Chart Section
# ---------------------------------------------------------------------------
st.markdown("### 📈 Doanh thu theo tháng")

try:
    df_monthly = run_query(MONTHLY_REVENUE_QUERY)
except Exception as e:
    df_monthly = pd.DataFrame()
    st.error(f"Không thể truy vấn doanh thu theo tháng: {e}")

if df_monthly.empty:
    st.warning("⚠️ Không có dữ liệu doanh thu theo tháng để hiển thị.")
else:
    # --- Chuẩn bị dữ liệu cho charts.py ---
    df_monthly["total_revenue"] = pd.to_numeric(
        df_monthly["total_revenue"], errors="coerce"
    ).fillna(0)
    df_monthly["year_month"] = df_monthly["year_month"].astype(str)
    df_monthly = df_monthly.sort_values("year_month").reset_index(drop=True)

    # --- Radio chọn loại biểu đồ ---
    chart_type = st.radio(
        "Chọn loại biểu đồ:",
        options=["Biểu đồ miền", "Biểu đồ cột"],
        horizontal=True,
    )

    # --- Render biểu đồ ---
    if chart_type == "Biểu đồ miền":
        fig = monthly_revenue_chart(df_monthly)
    else:
        fig = monthly_revenue_bar_chart(df_monthly)

    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Orders by Day of Week Chart Section
# ---------------------------------------------------------------------------
st.markdown("### 📅 Đơn hàng theo ngày trong tuần")

try:
    df_dow = run_query(TOTAL_ORDERS_BY_DATE_OF_HOURS)
except Exception as e:
    df_dow = pd.DataFrame()
    st.error(f"Không thể truy vấn đơn hàng theo ngày: {e}")

if df_dow.empty:
    st.warning("⚠️ Không có dữ liệu đơn hàng theo ngày trong tuần.")
else:
    df_dow["total_orders"] = pd.to_numeric(df_dow["total_orders"], errors="coerce").fillna(0)
    fig_dow = orders_by_day_of_week_chart(df_dow)
    st.plotly_chart(fig_dow, use_container_width=True)

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.divider()
st.markdown(
    "<p style='text-align:center; color:#475569; font-size:0.8rem;'>"
    "Olist E-commerce Analytics · Nguồn dữ liệu: warehouse schema · "
    "Grain: fact_sales (item-level) &amp; fact_order_fulfillment (order-level)"
    "</p>",
    unsafe_allow_html=True,
)
