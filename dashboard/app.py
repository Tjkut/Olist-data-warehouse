"""
Olist E-commerce Dashboard — Entry Point

Chỉ chứa cấu hình trang và màn hình chào mừng.
Nội dung phân tích nằm trong pages/1_Overview.py.

Run with: streamlit run app.py
"""

import streamlit as st

# ---------------------------------------------------------------------------
# Streamlit page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Olist E-commerce Dashboard",
    page_icon="🛒",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Custom CSS — Light theme (đồng nhất với .streamlit/config.toml)
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
    .portal-card {
        background-color: #F0F2F6;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 24px;
        height: 100%;
        transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
    }
    .portal-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
        border-color: #FF4B4B;
    }
    .portal-title {
        color: #1E293B;
        font-size: 1.15rem;
        font-weight: 700;
        margin-bottom: 8px;
    }
    .portal-desc {
        color: #64748B;
        font-size: 0.9rem;
        line-height: 1.5;
    }
    hr {
        border-color: #E2E8F0;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Welcome screen
# ---------------------------------------------------------------------------
st.markdown("# 🛒 Olist E-commerce Dashboard")
st.markdown(
    "Chào mừng bạn đến với **Olist E-commerce Analytics Platform** — Nền tảng phân tích dữ liệu bán lẻ trực tuyến tại Brazil. "
    "Dữ liệu được trích xuất và chuẩn hóa trực tiếp từ Data Warehouse (schema `warehouse` trên PostgreSQL)."
)
st.divider()

st.markdown("### 📌 Chọn chuyên mục phân tích ở thanh bên trái (Sidebar):")

col1, col2 = st.columns(2)
with col1:
    st.markdown("""
    <div class="portal-card">
        <div class="portal-title">📊 1. Overview (Tổng quan)</div>
        <div class="portal-desc">
            Theo dõi các chỉ số KPI cốt lõi: Doanh thu toàn sàn, Tổng đơn hàng, Tỷ lệ giao hàng thành công, Doanh thu theo tháng và Phân phối đơn theo ngày trong tuần.
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.write("")
    st.markdown("""
    <div class="portal-card">
        <div class="portal-title">👥 3. Customer (Khách hàng)</div>
        <div class="portal-desc">
            Phân bố khách hàng theo bang, Top các thành phố đông khách nhất và Tỷ lệ khách hàng quay lại mua sắm (Retention / Repeat Rate).
        </div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="portal-card">
        <div class="portal-title">📦 2. Product (Sản phẩm)</div>
        <div class="portal-desc">
            Xếp hạng Top 10 danh mục sản phẩm theo doanh thu và số lượng bán, cùng phân tích giá bán trung bình trên từng ngành hàng.
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.write("")
    st.markdown("""
    <div class="portal-card">
        <div class="portal-title">⭐ 4. Service Quality (Chất lượng dịch vụ)</div>
        <div class="portal-desc">
            Đo lường mức độ hài lòng khách hàng (CSAT review score), tương quan giữa thời gian giao hàng và đánh giá, bản đồ nhiệt thời gian giao theo bang.
        </div>
    </div>
    """, unsafe_allow_html=True)

st.divider()
st.info("👈 Hãy chọn một trang trên thanh bên trái (Sidebar) để bắt đầu khám phá dữ liệu.")
