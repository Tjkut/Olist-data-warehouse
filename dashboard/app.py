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
# Custom CSS — Dark theme
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Welcome screen
# ---------------------------------------------------------------------------
st.markdown("# 🛒 Olist E-commerce Dashboard")
st.divider()

st.markdown("""
Chào mừng đến với **Olist E-commerce Analytics Platform**.

Dữ liệu được truy vấn trực tiếp từ Data Warehouse — schema `warehouse` trên PostgreSQL.

---

👈 **Chọn Overview ở thanh bên để xem phân tích tổng quan.**
""")
