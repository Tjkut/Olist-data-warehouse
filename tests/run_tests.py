"""
tests/run_tests.py
==================
Chạy 2 bộ kiểm thử SQL chất lượng dữ liệu:
  1. tests/test_staging_views.sql  — kiểm tra tầng Staging Views
  2. tests/test_warehouse.sql      — kiểm tra tầng Data Warehouse

Kết quả được in ra terminal và trả về exit code:
  0 = Tất cả test PASS
  1 = Có ít nhất 1 test FAIL

Cách chạy (từ thư mục gốc hoặc thư mục tests/):
  python tests/run_tests.py
  python run_tests.py
"""

import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# 0. Cau hinh duong dan & bien moi truong
# ---------------------------------------------------------------------------
TESTS_DIR = Path(__file__).resolve().parent
ROOT_DIR  = TESTS_DIR.parent

load_dotenv(ROOT_DIR / ".env")

# Force UTF-8 output on Windows (cp1252 terminal issue)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

DB_HOST     = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT     = os.getenv("POSTGRES_PORT", "5432")
DB_NAME     = os.getenv("POSTGRES_DB",   "olist")
DB_USER     = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")

# ---------------------------------------------------------------------------
# Thu tu cac bo test — (nhan hien thi, duong dan file SQL)
# ---------------------------------------------------------------------------
TEST_FILES = [
    ("Staging Views", TESTS_DIR / "test_staging_views.sql"),
    ("Warehouse DWH", TESTS_DIR / "test_warehouse.sql"),
]

# ---------------------------------------------------------------------------
# Hang mau ANSI (tat tu dong neu terminal khong ho tro)
# ---------------------------------------------------------------------------
_NO_COLOR = not sys.stdout.isatty()

def _green(s):  return s if _NO_COLOR else f"\033[32m{s}\033[0m"
def _red(s):    return s if _NO_COLOR else f"\033[31m{s}\033[0m"
def _yellow(s): return s if _NO_COLOR else f"\033[33m{s}\033[0m"
def _cyan(s):   return s if _NO_COLOR else f"\033[36m{s}\033[0m"
def _bold(s):   return s if _NO_COLOR else f"\033[1m{s}\033[0m"


# ---------------------------------------------------------------------------
# Kết nối DB
# ---------------------------------------------------------------------------
def get_connection():
    """Mở và trả về connection psycopg2 tới PostgreSQL."""
    return psycopg2.connect(
        host=DB_HOST,
        port=int(DB_PORT),
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )


# ---------------------------------------------------------------------------
# Chạy một file SQL và trả về danh sách kết quả
# ---------------------------------------------------------------------------
def run_sql_file(cursor, sql_path: Path) -> list[dict]:
    """Thực thi file SQL test và trả về list[{"test_name": str, "failed_rows": int}]."""
    sql = sql_path.read_text(encoding="utf-8").strip()
    if not sql:
        raise ValueError(f"File SQL trống: {sql_path}")

    cursor.execute(sql)
    rows = cursor.fetchall()
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in rows]


# ---------------------------------------------------------------------------
# In ket qua mot bo test
# ---------------------------------------------------------------------------
def print_suite_results(suite_name: str, results: list[dict]) -> int:
    """Print test results and return number of FAILs."""
    sep = "-" * max(0, 50 - len(suite_name))
    print()
    print(_bold(_cyan(f"  +- {suite_name} {sep}+")))

    failed = 0
    passed = 0
    for row in results:
        name   = row.get("test_name", "?")
        count  = int(row.get("failed_rows", 0))
        if count == 0:
            status = _green("  PASS")
            passed += 1
        else:
            status = _red(f"  FAIL  ({count} error rows)")
            failed += 1
        print(f"  |  {status}  {name}")

    total = passed + failed
    summary_color = _green if failed == 0 else _red
    print(_bold(summary_color(f"  +- Result: {passed}/{total} PASS -- {failed} FAIL")))
    return failed


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> int:
    print()
    print(_bold("=" * 60))
    print(_bold("  Olist DWH -- Test Runner"))
    print(_bold(f"  DB: {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}"))
    print(_bold("=" * 60))

    # Kiem tra file SQL ton tai
    for label, path in TEST_FILES:
        if not path.exists():
            print(_red(f"[ERROR] File not found: {path}"))
            return 1

    try:
        conn = get_connection()
        conn.autocommit = True          # read-only — no transaction needed
        cursor = conn.cursor()
    except Exception as exc:
        print(_red(f"\n[ERROR] Cannot connect to PostgreSQL: {exc}"))
        return 1

    total_failed = 0
    try:
        for label, sql_path in TEST_FILES:
            try:
                results = run_sql_file(cursor, sql_path)
                total_failed += print_suite_results(label, results)
            except Exception as exc:
                print(_red(f"\n[ERROR] Suite '{label}' failed: {exc}"))
                total_failed += 1
    finally:
        cursor.close()
        conn.close()

    # Tong ket
    print()
    print(_bold("=" * 60))
    if total_failed == 0:
        print(_bold(_green("  [OK] All tests PASS -- Data Warehouse is analytics-ready!")))
    else:
        print(_bold(_red(f"  [!!] {total_failed} test(s) FAIL -- please review data quality.")))
    print(_bold("=" * 60))
    print()

    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
