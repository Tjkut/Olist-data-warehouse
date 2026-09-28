"""
Olist E-commerce Dashboard — Product Page

Hiển thị Top 10 danh mục sản phẩm theo doanh thu.
"""

import streamlit as st
import importlib
import query
import charts

importlib.reload(query)
importlib.reload(charts)

from db_connection import run_query
from query import (
    TOP_CATEGORY_PERFORMANCE_QUERY,
    TOP10_CATEGORY_REVENUE_QUERY,
    AVERAGE_PRICE_BY_CATEGORY_QUERY,
)
from charts import (
    top10_category_revenue_chart,
    top10_category_quantity_chart,
    avg_price_by_category_chart,
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
st.markdown("# 📦 Phân tích sản phẩm")
st.markdown(
    "Hiệu suất bán hàng theo danh mục sản phẩm (doanh thu và số lượng bán). "
    "Dữ liệu truy vấn từ `warehouse.fact_sales` × `warehouse.dim_product`."
)
st.divider()

# ---------------------------------------------------------------------------
# Top 10 Category Performance Chart (Doanh thu / Số lượng bán)
# ---------------------------------------------------------------------------
st.markdown("### 🏆 Top 10 danh mục sản phẩm")

try:
    df_perf = run_query(TOP_CATEGORY_PERFORMANCE_QUERY)
except Exception as e:
    df_perf = None
    st.error(f"Không thể truy vấn dữ liệu: {e}")

if df_perf is not None:
    if df_perf.empty:
        st.warning("⚠️ Không có dữ liệu để hiển thị.")
    else:
        df_perf["total_revenue"] = df_perf["total_revenue"].astype(float)
        df_perf["total_quantity"] = df_perf["total_quantity"].astype(int)

        metric_choice = st.radio(
            "Chọn chỉ số hiển thị:",
            options=["Doanh thu", "Số lượng bán"],
            horizontal=True,
            key="category_metric_choice",
        )

        if metric_choice == "Doanh thu":
            df_metric_sorted = (
                df_perf.sort_values(by="total_revenue", ascending=False)
                .reset_index(drop=True)
            )
            fig = top10_category_revenue_chart(df_metric_sorted.head(10))
            st.plotly_chart(fig, use_container_width=True)

            st.divider()

            # Data table
            st.markdown("#### 📋 Bảng chi tiết doanh thu")

            col_sort, col_show = st.columns([3, 2])
            with col_sort:
                sort_by = st.radio(
                    "Sắp xếp bảng theo:",
                    options=["Doanh thu", "Số lượng bán"],
                    horizontal=True,
                    key="sort_by_revenue_table",
                )
            with col_show:
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                show_all_perf = st.checkbox(
                    f"Xem toàn bộ {len(df_perf)} danh mục",
                    value=False,
                    key="show_all_perf_revenue",
                )

            if sort_by == "Số lượng bán":
                df_table_sorted = df_perf.sort_values(by="total_quantity", ascending=False).reset_index(drop=True)
                col_order = ["Danh mục sản phẩm", "Số lượng bán", "Doanh thu (BRL)"]
                df_display = df_table_sorted[["category", "total_quantity", "total_revenue"]].copy()
            else:
                df_table_sorted = df_perf.sort_values(by="total_revenue", ascending=False).reset_index(drop=True)
                col_order = ["Danh mục sản phẩm", "Doanh thu (BRL)", "Số lượng bán"]
                df_display = df_table_sorted[["category", "total_revenue", "total_quantity"]].copy()

            df_display.index = range(1, len(df_display) + 1)
            df_display.columns = col_order
            df_display["Doanh thu (BRL)"] = df_display["Doanh thu (BRL)"].apply(
                lambda x: f"R$ {x:,.2f}"
            )
            df_display["Số lượng bán"] = df_display["Số lượng bán"].apply(
                lambda x: f"{x:,}"
            )

            df_to_show = df_display if show_all_perf else df_display.head(10)
            st.dataframe(df_to_show, use_container_width=True)

            if not show_all_perf:
                st.caption(
                    f"Đang hiển thị 10 / {len(df_display)} danh mục đầu (sắp xếp theo {sort_by.lower()}). "
                    "Tích chọn ô **'Xem toàn bộ'** ở trên để xem tất cả."
                )
            else:
                st.caption(f"Đang hiển thị toàn bộ {len(df_display)} danh mục (sắp xếp theo {sort_by.lower()}).")

        else:
            df_metric_sorted = (
                df_perf.sort_values(by="total_quantity", ascending=False)
                .reset_index(drop=True)
            )
            fig = top10_category_quantity_chart(df_metric_sorted.head(10))
            st.plotly_chart(fig, use_container_width=True)

            st.divider()

            # Data table
            st.markdown("#### 📋 Bảng chi tiết số lượng bán")

            col_sort, col_show = st.columns([3, 2])
            with col_sort:
                sort_by = st.radio(
                    "Sắp xếp bảng theo:",
                    options=["Số lượng bán", "Doanh thu"],
                    horizontal=True,
                    key="sort_by_quantity_table",
                )
            with col_show:
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                show_all_perf = st.checkbox(
                    f"Xem toàn bộ {len(df_perf)} danh mục",
                    value=False,
                    key="show_all_perf_quantity",
                )

            if sort_by == "Doanh thu":
                df_table_sorted = df_perf.sort_values(by="total_revenue", ascending=False).reset_index(drop=True)
                col_order = ["Danh mục sản phẩm", "Doanh thu (BRL)", "Số lượng bán"]
                df_display = df_table_sorted[["category", "total_revenue", "total_quantity"]].copy()
            else:
                df_table_sorted = df_perf.sort_values(by="total_quantity", ascending=False).reset_index(drop=True)
                col_order = ["Danh mục sản phẩm", "Số lượng bán", "Doanh thu (BRL)"]
                df_display = df_table_sorted[["category", "total_quantity", "total_revenue"]].copy()

            df_display.index = range(1, len(df_display) + 1)
            df_display.columns = col_order
            df_display["Số lượng bán"] = df_display["Số lượng bán"].apply(
                lambda x: f"{x:,}"
            )
            df_display["Doanh thu (BRL)"] = df_display["Doanh thu (BRL)"].apply(
                lambda x: f"R$ {x:,.2f}"
            )

            df_to_show = df_display if show_all_perf else df_display.head(10)
            st.dataframe(df_to_show, use_container_width=True)

            if not show_all_perf:
                st.caption(
                    f"Đang hiển thị 10 / {len(df_display)} danh mục đầu (sắp xếp theo {sort_by.lower()}). "
                    "Tích chọn ô **'Xem toàn bộ'** ở trên để xem tất cả."
                )
            else:
                st.caption(f"Đang hiển thị toàn bộ {len(df_display)} danh mục (sắp xếp theo {sort_by.lower()}).")




# ---------------------------------------------------------------------------
# Average Price by Category Chart
# ---------------------------------------------------------------------------
st.divider()
st.markdown("### 💰 Top 10 danh mục có giá trung bình cao nhất")

try:
    df_avg_price = run_query(AVERAGE_PRICE_BY_CATEGORY_QUERY)
except Exception as e:
    df_avg_price = None
    st.error(f"Không thể truy vấn dữ liệu: {e}")

if df_avg_price is not None:
    if df_avg_price.empty:
        st.warning("⚠️ Không có dữ liệu để hiển thị.")
    else:
        df_avg_price["avg_price"] = df_avg_price["avg_price"].astype(float)
        fig_avg = avg_price_by_category_chart(df_avg_price)
        st.plotly_chart(fig_avg, use_container_width=True)

        st.divider()

        # Data table
        st.markdown("#### 📋 Bảng chi tiết giá trung bình")
        df_price_display = df_avg_price.copy()
        df_price_display.index = range(1, len(df_price_display) + 1)
        df_price_display.columns = ["Danh mục sản phẩm", "Giá trung bình (BRL)"]
        df_price_display["Giá trung bình (BRL)"] = df_price_display["Giá trung bình (BRL)"].apply(
            lambda x: f"R$ {x:,.2f}"
        )

        show_all = st.checkbox(
            f"Xem toàn bộ {len(df_price_display)} danh mục (mặc định hiển thị 10 danh mục đầu)",
            value=False,
            key="show_all_avg_price",
        )
        df_to_show = df_price_display if show_all else df_price_display.head(10)
        st.dataframe(df_to_show, use_container_width=True)

        if not show_all:
            st.caption(
                f"Đang hiển thị 10 / {len(df_price_display)} danh mục đầu. "
                "Tích chọn ô **'Xem toàn bộ'** ở trên để xem tất cả."
            )
        else:
            st.caption(f"Đang hiển thị toàn bộ {len(df_price_display)} danh mục.")

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.divider()
st.markdown(
    "<p style='text-align:center; color:#64748B; font-size:0.8rem;'>"
    "Olist E-commerce Analytics · Nguồn dữ liệu: warehouse schema · "
    "Grain: fact_sales (item-level)"
    "</p>",
    unsafe_allow_html=True,
)
