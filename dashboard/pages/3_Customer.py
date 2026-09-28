"""
Olist E-commerce Dashboard — Customer Page

Phân tích khách hàng theo bang và các chỉ số nhân khẩu học.
"""

import streamlit as st
import pandas as pd
import importlib
import query
import charts

importlib.reload(query)
importlib.reload(charts)

from db_connection import run_query
from query import (
    TOTAL_CUSTOMERS_QUERY,
    CUSTOMERS_BY_STATE_QUERY,
    CUSTOMERS_BY_CITY_QUERY,
    REPEAT_CUSTOMERS_QUERY,
)
from charts import (
    customers_by_state_chart,
    top10_cities_customer_chart,
    repeat_customers_pie_chart,
)

# ---------------------------------------------------------------------------
# Custom CSS — Light theme (đồng nhất với .streamlit/config.toml & charts.py)
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    .stApp {
        background-color: #FFFFFF;
        color: #31333F;
        font-family: 'Inter', sans-serif;
    }
    [data-testid="stSidebar"] {
        background-color: #F0F2F6;
        border-right: 1px solid #E2E8F0;
    }
    [data-testid="stSidebar"] * {
        color: #000000;
    }
    [data-testid="stSidebarNav"] a,
    [data-testid="stSidebarNav"] a:visited,
    [data-testid="stSidebarNav"] a span,
    [data-testid="stSidebarNavLink"],
    [data-testid="stSidebarNavLink"] span,
    section[data-testid="stSidebar"] a,
    section[data-testid="stSidebar"] a span {
        color: #000000 !important;
        font-weight: 500;
    }
    [data-testid="stSidebarNav"] a:hover span,
    [data-testid="stSidebarNavLink"]:hover span,
    section[data-testid="stSidebar"] a:hover span {
        color: #FF4B4B !important;
    }
    [data-testid="stSidebarNav"] a[aria-current="page"] span,
    [data-testid="stSidebarNavLink"][aria-current="page"] span,
    section[data-testid="stSidebar"] a[aria-current="page"] span {
        color: #000000 !important;
        font-weight: 700 !important;
    }
    [data-testid="stHeader"],
    [data-testid="stToolbar"] {
        background-color: #FFFFFF;
    }
    [data-testid="stMetric"] {
        background-color: #F0F2F6;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 20px 24px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    }
    [data-testid="stMetricLabel"] {
        color: #64748B;
        font-size: 0.9rem;
        font-weight: 500;
    }
    [data-testid="stMetricValue"] {
        color: #1E293B;
        font-size: 1.8rem;
        font-weight: 700;
    }
    [data-testid="stRadio"] label {
        color: #31333F;
    }
    hr {
        border-color: #E2E8F0;
    }
    .stAlert {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        color: #31333F;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Page title
# ---------------------------------------------------------------------------
st.markdown("# 👥 Phân tích khách hàng")
st.markdown(
    "Phân bố địa lý và số lượng khách hàng trên các bang của Brazil. "
    "Dữ liệu truy vấn trực tiếp từ `warehouse.dim_customer`."
)
st.divider()

# ---------------------------------------------------------------------------
# KPI Section — Total Customers & Repeat Purchase
# ---------------------------------------------------------------------------
st.markdown("### 📊 Tổng quan khách hàng")

try:
    df_cust = run_query(TOTAL_CUSTOMERS_QUERY)
    total_customers = int(df_cust["total_customers"].iloc[0])
except Exception as e:
    total_customers = None
    st.error(f"Không thể truy vấn tổng số khách hàng: {e}")

try:
    df_repeat = run_query(REPEAT_CUSTOMERS_QUERY)
    one_time = int(df_repeat["one_time_customers"].iloc[0])
    repeat = int(df_repeat["repeat_customers"].iloc[0])
    total_valid = one_time + repeat
    repeat_rate = (repeat / total_valid * 100) if total_valid > 0 else 0
except Exception as e:
    df_repeat = None
    one_time, repeat, total_valid, repeat_rate = None, None, None, None
    st.error(f"Không thể truy vấn tỷ lệ khách hàng quay lại: {e}")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(
        label="Tổng số khách hàng",
        value=f"{total_customers:,}" if total_customers is not None else "N/A",
        help="Số lượng khách hàng duy nhất (customer_unique_id) trong hệ thống",
    )
with col2:
    st.metric(
        label="Khách mua lại (≥ 2 lần)",
        value=f"{repeat:,}" if repeat is not None else "N/A",
        help="Số khách hàng đã từng đặt từ 2 đơn hàng trở lên",
    )
with col3:
    st.metric(
        label="Tỷ lệ quay lại (Repeat Rate)",
        value=f"{repeat_rate:.2f}%" if repeat_rate is not None else "N/A",
        help="Tỷ lệ khách hàng quay lại mua hàng trên tổng tập khách hàng",
    )

st.divider()

# ---------------------------------------------------------------------------
# Repeat Customers Pie Chart Section
# ---------------------------------------------------------------------------
st.markdown("### 🔄 Tỷ lệ khách hàng quay lại mua hàng")

if df_repeat is not None and not df_repeat.empty:
    col_pie, col_summary = st.columns([3, 2])
    with col_pie:
        fig_pie = repeat_customers_pie_chart(df_repeat)
        st.plotly_chart(fig_pie, use_container_width=True)
    with col_summary:
        st.markdown("#### 📋 Bảng phân loại khách hàng")
        df_summary = pd.DataFrame({
            "Phân loại": ["Khách mua 1 lần (One-time)", "Khách quay lại (Repeat ≥ 2)"],
            "Số khách hàng": [f"{one_time:,}", f"{repeat:,}"],
            "Tỷ lệ (%)": [f"{(one_time / total_valid * 100):.2f}%", f"{repeat_rate:.2f}%"],
        })
        df_summary.index = [1, 2]
        st.dataframe(df_summary, use_container_width=True)

st.divider()


# ---------------------------------------------------------------------------
# Customers by State Chart Section
# ---------------------------------------------------------------------------
st.markdown("### 🗺️ Phân bố khách hàng theo bang")

try:
    df_state = run_query(CUSTOMERS_BY_STATE_QUERY)
except Exception as e:
    df_state = None
    st.error(f"Không thể truy vấn khách hàng theo bang: {e}")

if df_state is not None:
    if df_state.empty:
        st.warning("⚠️ Không có dữ liệu để hiển thị.")
    else:
        df_state["total_customers"] = df_state["total_customers"].astype(int)
        fig = customers_by_state_chart(df_state)
        st.plotly_chart(fig, use_container_width=True)

        st.divider()

        # Data table
        st.markdown("#### 📋 Bảng chi tiết số lượng khách hàng theo bang")

        col_sort, col_show = st.columns([3, 2])
        with col_sort:
            sort_by = st.radio(
                "Sắp xếp bảng theo:",
                options=["Số khách hàng", "Tên bang"],
                horizontal=True,
                key="sort_by_state_table",
            )
        with col_show:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            show_all_states = st.checkbox(
                f"Xem toàn bộ {len(df_state)} bang",
                value=True,
                key="show_all_states",
            )

        if sort_by == "Tên bang":
            df_table_sorted = df_state.sort_values(by="state", ascending=True).reset_index(drop=True)
        else:
            df_table_sorted = df_state.sort_values(by="total_customers", ascending=False).reset_index(drop=True)

        df_display = df_table_sorted.copy()
        df_display.index = range(1, len(df_display) + 1)
        total_all = df_display["total_customers"].sum()
        df_display["Tỷ lệ (%)"] = (df_display["total_customers"] / total_all * 100).apply(
            lambda x: f"{x:.2f}%"
        )
        df_display["total_customers"] = df_display["total_customers"].apply(
            lambda x: f"{x:,}"
        )
        df_display.columns = ["Bang (State)", "Số khách hàng", "Tỷ lệ (%)"]

        df_to_show = df_display if show_all_states else df_display.head(10)
        st.dataframe(df_to_show, use_container_width=True)

        if not show_all_states:
            st.caption(
                f"Đang hiển thị 10 / {len(df_display)} bang đầu (sắp xếp theo {sort_by.lower()}). "
                "Tích chọn ô **'Xem toàn bộ'** ở trên để xem tất cả."
            )
        else:
            st.caption(f"Đang hiển thị toàn bộ {len(df_display)} bang (sắp xếp theo {sort_by.lower()}).")

# ---------------------------------------------------------------------------
# Top Cities by Customer Count Section
# ---------------------------------------------------------------------------
st.divider()
st.markdown("### 🏙️ Top 10 thành phố có nhiều khách hàng nhất")

try:
    df_city = run_query(CUSTOMERS_BY_CITY_QUERY)
except Exception as e:
    df_city = None
    st.error(f"Không thể truy vấn khách hàng theo thành phố: {e}")

if df_city is not None:
    if df_city.empty:
        st.warning("⚠️ Không có dữ liệu để hiển thị.")
    else:
        df_city["total_customers"] = df_city["total_customers"].astype(int)
        fig_city = top10_cities_customer_chart(df_city)
        st.plotly_chart(fig_city, use_container_width=True)

        st.divider()

        # Data table
        st.markdown("#### 📋 Bảng chi tiết khách hàng theo thành phố")

        col_sort_city, col_show_city = st.columns([3, 2])
        with col_sort_city:
            sort_by_city = st.radio(
                "Sắp xếp bảng theo:",
                options=["Số khách hàng", "Tên thành phố"],
                horizontal=True,
                key="sort_by_city_table",
            )
        with col_show_city:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            show_all_cities = st.checkbox(
                f"Xem toàn bộ {len(df_city)} thành phố (mặc định: Top 10)",
                value=False,
                key="show_all_cities",
            )

        if sort_by_city == "Tên thành phố":
            df_city_sorted = df_city.sort_values(by="city", ascending=True).reset_index(drop=True)
        else:
            df_city_sorted = df_city.sort_values(by="total_customers", ascending=False).reset_index(drop=True)

        df_city_display = df_city_sorted.copy()
        df_city_display.index = range(1, len(df_city_display) + 1)
        total_customers_all = df_city_display["total_customers"].sum()
        df_city_display["Tỷ lệ (%)"] = (df_city_display["total_customers"] / total_customers_all * 100).apply(
            lambda x: f"{x:.2f}%"
        )
        df_city_display["total_customers"] = df_city_display["total_customers"].apply(
            lambda x: f"{x:,}"
        )
        df_city_display.columns = ["Thành phố", "Bang", "Số khách hàng", "Tỷ lệ (%)"]

        df_city_to_show = df_city_display if show_all_cities else df_city_display.head(10)
        st.dataframe(df_city_to_show, use_container_width=True)

        if not show_all_cities:
            st.caption(
                f"Đang hiển thị 10 / {len(df_city_display)} thành phố đầu (sắp xếp theo {sort_by_city.lower()}). "
                "Tích chọn ô **'Xem toàn bộ'** ở trên để xem tất cả."
            )
        else:
            st.caption(f"Đang hiển thị toàn bộ {len(df_city_display)} thành phố (sắp xếp theo {sort_by_city.lower()}).")

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.divider()
st.markdown(
    "<p style='text-align:center; color:#64748B; font-size:0.8rem;'>"
    "Olist E-commerce Analytics · Nguồn dữ liệu: warehouse schema · "
    "Entity: dim_customer (customer_unique_id)"
    "</p>",
    unsafe_allow_html=True,
)
