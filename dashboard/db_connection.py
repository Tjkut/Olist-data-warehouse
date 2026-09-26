"""
Database connection utilities for the Olist Dashboard.

Provides helper functions to connect to the PostgreSQL data warehouse
and execute analytical queries against the `warehouse` schema.

Uses SQLAlchemy for connection management and Streamlit caching
to avoid re-querying the database on every page interaction.
"""

import os
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# ---------------------------------------------------------------------------
# Load environment variables from the project-root .env file
# ---------------------------------------------------------------------------
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV_PATH)

_DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
_DB_PORT = os.getenv("POSTGRES_PORT", "5432")
_DB_NAME = os.getenv("POSTGRES_DB", "olist")
_DB_USER = os.getenv("POSTGRES_USER", "postgres")
_DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")


# ---------------------------------------------------------------------------
# SQLAlchemy engine (singleton — created once per process)
# ---------------------------------------------------------------------------
@st.cache_resource
def _get_engine():
    """Create and cache a SQLAlchemy engine connected to PostgreSQL.

    The engine is cached at the process level via @st.cache_resource
    so that connection pooling is reused across Streamlit reruns.

    Raises:
        RuntimeError: If required database credentials are missing
                      or the connection URL is invalid.
    """
    if not _DB_PASSWORD:
        raise RuntimeError(
            "Biến POSTGRES_PASSWORD chưa được thiết lập trong file .env. "
            "Vui lòng kiểm tra lại file .env tại thư mục gốc dự án."
        )

    url = (
        f"postgresql+psycopg2://{_DB_USER}:{_DB_PASSWORD}"
        f"@{_DB_HOST}:{_DB_PORT}/{_DB_NAME}"
    )

    try:
        engine = create_engine(url, pool_pre_ping=True)
        # Kiểm tra kết nối ngay khi khởi tạo
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception as exc:
        raise RuntimeError(
            f"Không thể kết nối đến PostgreSQL "
            f"({_DB_HOST}:{_DB_PORT}/{_DB_NAME}): {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Public API — run_query
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner="Đang truy vấn dữ liệu …")
def run_query(sql: str, params: dict | None = None) -> pd.DataFrame:
    """Execute a SQL query and return the result as a pandas DataFrame.

    Results are cached for 5 minutes (ttl=300) to reduce database load
    during interactive dashboard usage.

    Args:
        sql:    The SQL query string. Use :name placeholders for params
                (e.g. ``WHERE status = :status``).
        params: Optional dict of parameters to bind into the query
                (e.g. ``{"status": "delivered"}``).

    Returns:
        pd.DataFrame: Query results with column names from the cursor.

    Raises:
        RuntimeError: If the query fails with a clear error message.
    """
    try:
        engine = _get_engine()
        with engine.connect() as conn:
            return pd.read_sql_query(text(sql), conn, params=params)
    except RuntimeError:
        # Lỗi kết nối từ _get_engine — re-raise để Streamlit hiển thị
        raise
    except SQLAlchemyError as exc:
        raise RuntimeError(
            f"Lỗi khi thực thi truy vấn SQL: {exc}"
        ) from exc
    except Exception as exc:
        raise RuntimeError(
            f"Lỗi không xác định khi truy vấn: {exc}"
        ) from exc
