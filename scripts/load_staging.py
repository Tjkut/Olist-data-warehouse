import os
import sys
import time
from pathlib import Path
import psycopg2

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# ------------------------------------------------------------------------------
# Configuration & Paths
# ------------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATASETS_DIR = BASE_DIR / "datasets"
DDL_FILE = BASE_DIR / "sql" / "olist_staging.sql"

# Load .env file (try python-dotenv, fallback to custom parser)
env_file = BASE_DIR / ".env"
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=env_file)
except ImportError:
    pass

if env_file.exists():
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip().strip("'\""))

DB_HOST = os.getenv("POSTGRES_HOST") or os.getenv("DB_HOST") or "localhost"
DB_PORT = os.getenv("POSTGRES_PORT") or os.getenv("DB_PORT") or "5432"
DB_NAME = os.getenv("POSTGRES_DB") or os.getenv("DB_NAME") or "olist_db"
DB_USER = os.getenv("POSTGRES_USER") or os.getenv("DB_USER") or "postgres"
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD") or os.getenv("DB_PASSWORD") or "postgres"

TABLE_FILE_MAPPING = [
    ("staging.customers", DATASETS_DIR / "olist_customers_dataset.csv"),
    ("staging.orders", DATASETS_DIR / "olist_orders_dataset.csv"),
    ("staging.order_items", DATASETS_DIR / "olist_order_items_dataset.csv"),
    ("staging.order_payments", DATASETS_DIR / "olist_order_payments_dataset.csv"),
    ("staging.order_reviews", DATASETS_DIR / "olist_order_reviews_dataset.csv"),
    ("staging.products", DATASETS_DIR / "olist_products_dataset.csv"),
    ("staging.sellers", DATASETS_DIR / "olist_sellers_dataset.csv"),
    ("staging.geolocation", DATASETS_DIR / "olist_geolocation_dataset.csv"),
    ("staging.product_category_name_translation", DATASETS_DIR / "product_category_name_translation.csv"),
]


def get_connection():
    """Tạo kết nối tới PostgreSQL."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )


def apply_ddl(cursor):
    """Chạy script DDL tạo schema và bảng staging."""
    if not DDL_FILE.exists():
        raise FileNotFoundError(f"Không tìm thấy file DDL: {DDL_FILE}")
    print(f"[*] Đang thực thi DDL từ {DDL_FILE.name}...")
    with open(DDL_FILE, "r", encoding="utf-8") as f:
        cursor.execute(f.read())
    print("[+] Khởi tạo schema và bảng staging thành công.")


def load_data():
    """Load tất cả các file CSV vào các bảng staging bằng COPY."""
    start_total = time.time()
    print("=" * 60)
    print(f"Bắt đầu load dữ liệu vào Database: {DB_NAME} ({DB_HOST}:{DB_PORT})")
    print("=" * 60)

    try:
        conn = get_connection()
        conn.autocommit = False
        cursor = conn.cursor()

        # 1. Tạo mới / reset các bảng staging
        apply_ddl(cursor)

        # 2. Ingest từng file CSV
        for table_name, file_path in TABLE_FILE_MAPPING:
            if not file_path.exists():
                print(f"[!] Bỏ qua {table_name}: không tìm thấy file {file_path}")
                continue

            print(f"[*] Đang nạp {file_path.name} -> {table_name}...")
            t0 = time.time()
            with open(file_path, "r", encoding="utf-8-sig") as f:
                copy_query = f"COPY {table_name} FROM STDIN WITH CSV HEADER"
                cursor.copy_expert(copy_query, f)

            # Lấy số dòng đã nạp để kiểm chứng
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            row_count = cursor.fetchone()[0]
            elapsed = time.time() - t0
            print(f"    -> Thành công: {row_count:,} dòng ({elapsed:.2f}s)")

        conn.commit()
        cursor.close()
        conn.close()

        total_elapsed = time.time() - start_total
        print("=" * 60)
        print(f"[+] Hoàn tất nạp toàn bộ datasets vào staging ({total_elapsed:.2f}s)!")
        print("=" * 60)

    except Exception as e:
        print(f"[ERROR] Quá trình nạp dữ liệu thất bại: {e}", file=sys.stderr)
        if "conn" in locals() and conn:
            conn.rollback()
            conn.close()
        sys.exit(1)


if __name__ == "__main__":
    load_data()
