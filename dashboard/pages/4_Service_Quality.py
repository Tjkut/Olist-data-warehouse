import streamlit as st
import pandas as pd
import importlib
import query
import charts

importlib.reload(query)
importlib.reload(charts)

from db_connection import run_query
from query import AVG_REVIEW_SCORE_QUERY, DELIVERY_TIME_VS_REVIEW_QUERY, AVG_DELIVERY_TIME_BY_STATE_QUERY
from charts import delivery_time_vs_review_scatter, delivery_time_by_state_map

# ---------------------------------------------------------------------------
# Custom CSS — Dark theme (đồng nhất với các trang khác)
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    .stApp {
        background-color: #0F172A;
        color: #F8FAFC;
        font-family: 'Inter', sans-serif;
    }
    [data-testid="stSidebar"] { background-color: #1E293B; }
    [data-testid="stHeader"], [data-testid="stToolbar"] { background-color: #0F172A; }
    [data-testid="stMetric"] {
        background-color: #1E293B;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 20px 24px;
    }
    [data-testid="stMetricLabel"] { color: #94A3B8; font-size: 0.9rem; font-weight: 500; }
    [data-testid="stMetricValue"] { color: #F8FAFC; font-size: 1.8rem; font-weight: 700; }
    [data-testid="stRadio"] label { color: #F8FAFC; }
    hr { border-color: #334155; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Page title
# ---------------------------------------------------------------------------
st.markdown("# ⭐ Chất lượng dịch vụ & Đánh giá")
st.markdown(
    "Đo lường mức độ hài lòng của khách hàng (CSAT) và chất lượng dịch vụ giao hàng Olist. "
    "Dữ liệu truy vấn trực tiếp từ `warehouse.fact_order_fulfillment`."
)
st.divider()

# ---------------------------------------------------------------------------
# KPI Section — Average Review Score
# ---------------------------------------------------------------------------
st.markdown("### 📊 Tổng quan chất lượng dịch vụ")

try:
    df_review = run_query(AVG_REVIEW_SCORE_QUERY)
    avg_score = float(df_review["avg_review_score"].iloc[0])
except Exception as e:
    avg_score = None
    st.error(f"Không thể truy vấn điểm đánh giá trung bình: {e}")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(
        label="Điểm đánh giá trung bình",
        value=f"{avg_score:.2f} / 5.0 ⭐" if avg_score is not None else "N/A",
        help="Điểm review trung bình trên thang điểm 1 đến 5 sao từ khách hàng",
    )

st.divider()

# ---------------------------------------------------------------------------
# Delivery Time vs Review Score Section (Scatter Plot)
# ---------------------------------------------------------------------------
st.markdown("### ⏱️ Effect of Delivery Day on Customer's Review")
st.markdown(
    "Biểu đồ phân tán (Scatter plot) thể hiện tác động của số ngày giao hàng (`Delivery Day`) đến điểm đánh giá của khách hàng, "
    "phân loại theo đơn giao trễ (**Late**) và đúng hạn (**On Time**). Đường đứt nét thể hiện xu hướng giảm điểm đánh giá khi thời gian giao hàng kéo dài."
)

try:
    df_scatter = run_query(DELIVERY_TIME_VS_REVIEW_QUERY)
except Exception as e:
    df_scatter = None
    st.error(f"Không thể truy vấn dữ liệu tương quan giao hàng: {e}")

if df_scatter is not None and not df_scatter.empty:
    df_scatter["delivery_day"] = df_scatter["delivery_day"].astype(float)
    df_scatter["avg_review_score"] = df_scatter["avg_review_score"].astype(float)
    df_scatter["order_count"] = df_scatter["order_count"].astype(int)

    fig_scatter = delivery_time_vs_review_scatter(df_scatter)
    st.plotly_chart(fig_scatter, use_container_width=True)

    st.divider()

    # Summary table
    st.markdown("#### 📋 Thống kê so sánh giữa đơn giao đúng hạn (On Time) và giao trễ (Late)")
    df_status_summary = (
        df_scatter.groupby("delivery_status")
        .apply(
            lambda g: pd.Series({
                "Tổng số đơn": g["order_count"].sum(),
                "Thời gian giao TB": (g["delivery_day"] * g["order_count"]).sum() / g["order_count"].sum(),
                "Điểm review TB": (g["avg_review_score"] * g["order_count"]).sum() / g["order_count"].sum(),
            })
        )
        .reset_index()
    )

    total_orders_all = df_status_summary["Tổng số đơn"].sum()
    df_status_display = pd.DataFrame({
        "Trạng thái giao hàng": df_status_summary["delivery_status"],
        "Số lượng đơn": df_status_summary["Tổng số đơn"].apply(lambda x: f"{int(x):,}"),
        "Tỷ lệ đơn (%)": (df_status_summary["Tổng số đơn"] / total_orders_all * 100).apply(lambda x: f"{x:.2f}%"),
        "Thời gian giao TB": df_status_summary["Thời gian giao TB"].apply(lambda x: f"{x:.1f} ngày"),
        "Điểm review TB": df_status_summary["Điểm review TB"].apply(lambda x: f"{x:.2f} ⭐"),
    })
    df_status_display.index = range(1, len(df_status_display) + 1)
    st.dataframe(df_status_display, use_container_width=True)


# ---------------------------------------------------------------------------
# Delivery Time by State — Choropleth Map
# ---------------------------------------------------------------------------
st.divider()
st.subheader("🚚 Thời gian giao hàng trung bình theo bang")
st.markdown(
    "Bản đồ nhiệt thể hiện thời gian giao hàng trung bình (ngày) đến từng bang của Brazil. "
    "Bang có màu càng đậm thì thời gian giao hàng càng lâu."
)

try:
    df_delivery_state = run_query(AVG_DELIVERY_TIME_BY_STATE_QUERY)
except Exception as e:
    df_delivery_state = None
    st.error(f"Không thể truy vấn dữ liệu giao hàng theo bang: {e}")

if df_delivery_state is not None and not df_delivery_state.empty:
    df_delivery_state["avg_delivery_days"] = df_delivery_state["avg_delivery_days"].astype(float)
    df_delivery_state["delivered_orders"] = df_delivery_state["delivered_orders"].astype(int)

    col_legend, col_map = st.columns([1, 4])

    # Left column — scrollable state code legend
    with col_legend:
        st.markdown("##### 📖 Chú thích mã bang")
        _STATE_NAMES = {
            "AC": "Acre",           "AL": "Alagoas",        "AM": "Amazonas",
            "AP": "Amapá",          "BA": "Bahia",          "CE": "Ceará",
            "DF": "Distrito Federal","ES": "Espírito Santo", "GO": "Goiás",
            "MA": "Maranhão",       "MG": "Minas Gerais",   "MS": "Mato Grosso do Sul",
            "MT": "Mato Grosso",    "PA": "Pará",           "PB": "Paraíba",
            "PE": "Pernambuco",     "PI": "Piauí",          "PR": "Paraná",
            "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte", "RO": "Rondônia",
            "RR": "Roraima",        "RS": "Rio Grande do Sul",   "SC": "Santa Catarina",
            "SE": "Sergipe",        "SP": "São Paulo",      "TO": "Tocantins",
        }
        rows_html = ""
        for i, (code, name) in enumerate(sorted(_STATE_NAMES.items())):
            bg = "#1E293B" if i % 2 == 0 else "#0F172A"
            rows_html += (
                f"<div style='display:flex; gap:24px; "
                f"padding:6px 12px; background:{bg}; border-radius:4px;'>"
                f"<span style='font-weight:700; color:#93C5FD; min-width:40px;'>{code}</span>"
                f"<span style='color:#CBD5E1;'>{name}</span></div>"
            )
        st.markdown(
            f"<div style='max-height:700px; overflow-y:auto; border:1px solid #334155; "
            f"border-radius:8px; padding:4px;'>{rows_html}</div>",
            unsafe_allow_html=True,
        )

    # Right column — choropleth map
    with col_map:
        fig_map = delivery_time_by_state_map(df_delivery_state)
        st.plotly_chart(fig_map, use_container_width=True)
else:
    if df_delivery_state is not None:
        st.warning("Không có dữ liệu thời gian giao hàng theo bang để hiển thị.")


# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.divider()
st.markdown(
    "<p style='text-align:center; color:#475569; font-size:0.8rem;'>"
    "Olist E-commerce Analytics · Nguồn dữ liệu: warehouse schema · "
    "Grain: fact_order_fulfillment (review_score)"
    "</p>",
    unsafe_allow_html=True,
)

