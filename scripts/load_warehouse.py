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
# Configuration & Environment
# Current implementation uses full refresh for reproducibility and idempotency.
# Incremental loading can be introduced for production workloads.
# ------------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

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


def get_connection():
    """Creates and returns a connection to the PostgreSQL database.

    Reads database credentials from environment variables or defaults
    configured in the application settings.

    Returns:
        psycopg2.extensions.connection: An active PostgreSQL database connection.

    Raises:
        psycopg2.OperationalError: If connection to the database cannot be established.
    """
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )


def row_count(cursor, table):
    """Counts the total number of rows in a database table.

    Args:
        cursor (psycopg2.extensions.cursor): The database cursor used to execute queries.
        table (str): Fully qualified name of the table to count rows from.

    Returns:
        int: The total count of rows in the specified table.
    """
    cursor.execute(f"SELECT COUNT(*) FROM {table};")
    return cursor.fetchone()[0]


# ------------------------------------------------------------------------------
# Ensure staging views exist (stg.* aliases + staging.vw_* transform views)
# ------------------------------------------------------------------------------
def ensure_staging_views(cursor):
    """Creates or replaces staging views for type casting and cleaning.

    Reads and executes sql/olist_staging_views.sql to set up the stg schema
    alias views and staging.vw_* transformation views. Uses CREATE OR REPLACE
    for idempotency.

    Args:
        cursor (psycopg2.extensions.cursor): The database cursor used to execute queries.
    """
    ddl_file = BASE_DIR / "sql" / "olist_staging_views.sql"
    print(f"[*] Creating staging views from {ddl_file.name}...")
    # Ensure staging schema exists before executing view definitions
    cursor.execute("CREATE SCHEMA IF NOT EXISTS staging;")
    sql = ddl_file.read_text(encoding="utf-8")
    cursor.execute(sql)
    print("[+] Staging views created.")


# ------------------------------------------------------------------------------
# Truncate warehouse tables (respect FK dependency order: facts first, then dims)
# ------------------------------------------------------------------------------
def truncate_warehouse(cursor):
    """Truncates all tables in the warehouse schema in dependency order.

    Clears facts first, followed by dimensions, using CASCADE to respect
    foreign key constraints and prepare the data warehouse for a full refresh.

    Args:
        cursor (psycopg2.extensions.cursor): The database cursor used to execute queries.
    """
    print("[*] Truncating warehouse tables...")
    cursor.execute("""
        TRUNCATE TABLE
            warehouse.fact_order_fulfillment,
            warehouse.fact_sales,
            warehouse.dim_seller,
            warehouse.dim_product,
            warehouse.dim_customer,
            warehouse.dim_date
        CASCADE;
    """)
    print("[+] Warehouse tables truncated.")


# ------------------------------------------------------------------------------
# 1. dim_date: generate calendar via generate_series (no staging dependency)
# Surrogate key: date_key (YYYYMMDD)
# ------------------------------------------------------------------------------
def load_dim_date(cursor):
    """Populates the date dimension table using generate_series.

    Generates calendar days between 2016-01-01 and 2019-12-31 without any
    external staging dependency. Computes calendar attributes such as year,
    quarter, month, week, day of week, and weekend indicator.

    Args:
        cursor (psycopg2.extensions.cursor): The database cursor used to execute queries.

    Returns:
        int: Total number of rows loaded into warehouse.dim_date.
    """
    print("[*] Loading dim_date...")
    cursor.execute("""
        INSERT INTO warehouse.dim_date (
            date_key, full_date, year, quarter, month, month_name,
            week_of_year, day_of_month, day_of_week, day_name, is_weekend
        )
        SELECT
            TO_CHAR(d, 'YYYYMMDD')::INT,
            d,
            EXTRACT(YEAR    FROM d)::SMALLINT,
            EXTRACT(QUARTER FROM d)::SMALLINT,
            EXTRACT(MONTH   FROM d)::SMALLINT,
            TRIM(TO_CHAR(d, 'Month')),
            EXTRACT(WEEK    FROM d)::SMALLINT,
            EXTRACT(DAY     FROM d)::SMALLINT,
            EXTRACT(DOW     FROM d)::SMALLINT + 1,
            TRIM(TO_CHAR(d, 'Day')),
            EXTRACT(DOW FROM d) IN (0, 6)
        FROM generate_series('2016-01-01'::DATE, '2019-12-31'::DATE, '1 day') AS t(d);
    """)
    cnt = row_count(cursor, "warehouse.dim_date")
    print(f"[+] dim_date: {cnt:,} rows loaded.")
    return cnt


# ------------------------------------------------------------------------------
# 2. dim_customer: dedup by most-frequent location per customer_unique_id
# Tie-break: city ASC, state ASC, zip ASC for deterministic reproducibility.
# Business rule (ROW_NUMBER dedup) stays here; cleaning is in staging.vw_customers.
# ------------------------------------------------------------------------------
def load_dim_customer(cursor):
    """Loads and deduplicates customer records into the customer dimension.

    Reads cleaned customer profiles from staging.vw_customers. Resolves
    multiple customer locations by choosing the most frequent location,
    using city, state, and zip code as deterministic tie-breakers.

    Args:
        cursor (psycopg2.extensions.cursor): The database cursor used to execute queries.

    Returns:
        int: Total number of rows loaded into warehouse.dim_customer.
    """
    print("[*] Loading dim_customer...")
    cursor.execute("""
        INSERT INTO warehouse.dim_customer (
            customer_unique_id, customer_city, customer_state, zip_code_prefix
        )
        SELECT
            customer_unique_id,
            customer_city,
            customer_state,
            customer_zip_code_prefix
        FROM (
            SELECT
                customer_unique_id,
                customer_city,
                customer_state,
                customer_zip_code_prefix,
                ROW_NUMBER() OVER (
                    PARTITION BY customer_unique_id
                    ORDER BY COUNT(*) DESC,
                             customer_city ASC,
                             customer_state ASC,
                             customer_zip_code_prefix ASC
                ) AS rn
            FROM staging.vw_customers
            GROUP BY customer_unique_id, customer_city,
                     customer_state, customer_zip_code_prefix
        ) ranked
        WHERE rn = 1;
    """)
    cnt = row_count(cursor, "warehouse.dim_customer")
    print(f"[+] dim_customer: {cnt:,} rows loaded.")
    return cnt


# ------------------------------------------------------------------------------
# 3. dim_product: reads from staging.vw_products (translation join + type casting
#    already handled in view). Surrogate key product_key generated as SERIAL PK.
# ------------------------------------------------------------------------------
def load_dim_product(cursor):
    """Loads product records into the product dimension.

    Reads cleaned and enriched product data from staging.vw_products, which
    handles category translation joins, COALESCE fallbacks, and numeric
    type casting.

    Args:
        cursor (psycopg2.extensions.cursor): The database cursor used to execute queries.

    Returns:
        int: Total number of rows loaded into warehouse.dim_product.
    """
    print("[*] Loading dim_product...")
    cursor.execute("""
        INSERT INTO warehouse.dim_product (
            product_id, category_name, category_name_english,
            product_name_length, product_description_length, product_photos_qty,
            product_weight_g, product_length_cm, product_height_cm, product_width_cm
        )
        SELECT
            product_id,
            category_name,
            category_name_english,
            product_name_length,
            product_description_length,
            product_photos_qty,
            product_weight_g,
            product_length_cm,
            product_height_cm,
            product_width_cm
        FROM staging.vw_products;
    """)
    cnt = row_count(cursor, "warehouse.dim_product")
    print(f"[+] dim_product: {cnt:,} rows loaded.")
    return cnt


# ------------------------------------------------------------------------------
# 4. dim_seller: reads from staging.vw_sellers (filtering done in view).
# Surrogate key seller_key generated as SERIAL PK.
# ------------------------------------------------------------------------------
def load_dim_seller(cursor):
    """Loads seller records into the seller dimension table.

    Reads cleaned seller profiles from staging.vw_sellers, which filters
    out records with null or empty seller_id identifiers.

    Args:
        cursor (psycopg2.extensions.cursor): The database cursor used to execute queries.

    Returns:
        int: Total number of rows loaded into warehouse.dim_seller.
    """
    print("[*] Loading dim_seller...")
    cursor.execute("""
        INSERT INTO warehouse.dim_seller (
            seller_id, seller_city, seller_state, zip_code_prefix
        )
        SELECT
            seller_id,
            seller_city,
            seller_state,
            seller_zip_code_prefix
        FROM staging.vw_sellers;
    """)
    cnt = row_count(cursor, "warehouse.dim_seller")
    print(f"[+] dim_seller: {cnt:,} rows loaded.")
    return cnt


# ------------------------------------------------------------------------------
# 5. fact_sales: grain = 1 row per order_item (order_id, order_item_id)
# Type casting done in staging.vw_order_items and staging.vw_orders.
# Uses LEFT JOIN to prevent silent dropping of records.
# Surrogate keys resolved via dimension lookups:
#   customer_key, product_key, seller_key, date_key
# ------------------------------------------------------------------------------
def load_fact_sales(cursor):
    """Loads line-item sales facts into warehouse.fact_sales.

    Preserves the grain of 1 row per order item. Reads cleaned order items
    from staging.vw_order_items and joins with staging.vw_orders and
    staging.vw_customers for timestamp and customer resolution. Uses LEFT JOINs
    to warehouse dimension tables to resolve surrogate keys (customer_key,
    product_key, seller_key, date_key) while preventing silent record drops.

    Args:
        cursor (psycopg2.extensions.cursor): The database cursor used to execute queries.

    Returns:
        int: Total number of rows loaded into warehouse.fact_sales.
    """
    print("[*] Loading fact_sales...")
    cursor.execute("""
        INSERT INTO warehouse.fact_sales (
            order_id, order_item_id,
            customer_key, product_key, seller_key, date_key,
            price, freight_value, sales_amount
        )
        SELECT
            oi.order_id,
            oi.order_item_id,

            dc.customer_key,
            dp.product_key,
            ds.seller_key,
            dd.date_key,

            oi.price,
            oi.freight_value,
            COALESCE(oi.price, 0) + COALESCE(oi.freight_value, 0)

        FROM staging.vw_order_items oi

        -- Join orders for customer_id and purchase timestamp
        LEFT JOIN staging.vw_orders o
                ON oi.order_id = o.order_id

        -- Resolve customer_id -> customer_unique_id -> surrogate customer_key
        LEFT JOIN staging.vw_customers sc
                ON o.customer_id = sc.customer_id
        LEFT JOIN warehouse.dim_customer dc
                ON sc.customer_unique_id = dc.customer_unique_id

        -- Resolve product surrogate key
        LEFT JOIN warehouse.dim_product dp
                ON oi.product_id = dp.product_id

        -- Resolve seller surrogate key
        LEFT JOIN warehouse.dim_seller ds
                ON oi.seller_id = ds.seller_id

        -- Resolve purchase date surrogate key
        LEFT JOIN warehouse.dim_date dd
                ON dd.full_date = o.order_purchase_timestamp::DATE;
    """)
    cnt = row_count(cursor, "warehouse.fact_sales")
    print(f"[+] fact_sales: {cnt:,} rows loaded.")
    return cnt


# ------------------------------------------------------------------------------
# 6. fact_order_fulfillment: grain = 1 row per order (order_id)
# Timestamps pre-cast in staging.vw_orders. Payment and review pre-aggregated
# in staging.vw_order_payments_agg and staging.vw_order_reviews_latest.
# CASE WHEN duration/is_on_time business logic stays here (not cleaning).
# Surrogate keys:
#   customer_key, order_purchase_date_key, order_approved_date_key,
#   carrier_pickup_date_key, delivered_date_key, estimated_delivery_date_key
# ------------------------------------------------------------------------------
def load_fact_order_fulfillment(cursor):
    """Loads order fulfillment and logistics facts into warehouse.fact_order_fulfillment.

    Maintains the grain of 1 row per order. Reads cleaned timestamps from
    staging.vw_orders, pre-aggregated payments from staging.vw_order_payments_agg,
    and latest review scores from staging.vw_order_reviews_latest. Resolves date
    surrogate keys and calculates duration metrics ensuring no negative values.

    Args:
        cursor (psycopg2.extensions.cursor): The database cursor used to execute queries.

    Returns:
        int: Total number of rows loaded into warehouse.fact_order_fulfillment.
    """
    print("[*] Loading fact_order_fulfillment...")
    cursor.execute("""
        INSERT INTO warehouse.fact_order_fulfillment (
            order_id,
            customer_key,
            order_purchase_date_key,
            order_approved_date_key,
            carrier_pickup_date_key,
            delivered_date_key,
            estimated_delivery_date_key,
            hours_to_approval,
            hours_to_carrier,
            hours_to_customer,
            total_fulfillment_hours,
            days_vs_estimate,
            review_score,
            order_status,
            is_on_time,
            total_payment_value,
            payment_count
        )
        SELECT
            o.order_id,

            dc.customer_key,

            -- Date keys via full_date lookup
            dd_purchase.date_key,
            dd_approved.date_key,
            dd_carrier.date_key,
            dd_delivered.date_key,
            dd_estimated.date_key,

            -- hours_to_approval: only when approved_at >= purchase_timestamp
            CASE
                WHEN o.order_approved_at >= o.order_purchase_timestamp
                THEN ROUND(EXTRACT(EPOCH FROM (
                    o.order_approved_at - o.order_purchase_timestamp
                )) / 3600.0, 2)
                ELSE NULL
            END,

            -- hours_to_carrier: only when carrier_date >= approved_at
            CASE
                WHEN o.order_delivered_carrier_date >= o.order_approved_at
                THEN ROUND(EXTRACT(EPOCH FROM (
                    o.order_delivered_carrier_date - o.order_approved_at
                )) / 3600.0, 2)
                ELSE NULL
            END,

            -- hours_to_customer: only when customer_date >= carrier_date
            CASE
                WHEN o.order_delivered_customer_date >= o.order_delivered_carrier_date
                THEN ROUND(EXTRACT(EPOCH FROM (
                    o.order_delivered_customer_date - o.order_delivered_carrier_date
                )) / 3600.0, 2)
                ELSE NULL
            END,

            -- total_fulfillment_hours: only when customer_date >= purchase_timestamp
            CASE
                WHEN o.order_delivered_customer_date >= o.order_purchase_timestamp
                THEN ROUND(EXTRACT(EPOCH FROM (
                    o.order_delivered_customer_date - o.order_purchase_timestamp
                )) / 3600.0, 2)
                ELSE NULL
            END,

            -- days_vs_estimate: NULL if either timestamp missing
            CASE
                WHEN o.order_delivered_customer_date IS NOT NULL
                 AND o.order_estimated_delivery_date IS NOT NULL
                THEN ROUND(EXTRACT(EPOCH FROM (
                    o.order_delivered_customer_date - o.order_estimated_delivery_date
                )) / 86400.0, 2)
                ELSE NULL
            END,

            -- review_score: latest review per order (from pre-aggregated view)
            r.review_score,

            o.order_status,

            -- is_on_time: NULL if either timestamp missing
            CASE
                WHEN o.order_delivered_customer_date IS NOT NULL
                 AND o.order_estimated_delivery_date IS NOT NULL
                THEN o.order_delivered_customer_date <= o.order_estimated_delivery_date
                ELSE NULL
            END,

            -- payment aggregate at order level (from pre-aggregated view)
            pay.total_payment_value,
            pay.payment_count

        FROM staging.vw_orders o

        -- Customer lookup
        LEFT JOIN staging.vw_customers sc
                ON o.customer_id = sc.customer_id
        LEFT JOIN warehouse.dim_customer dc
                ON sc.customer_unique_id = dc.customer_unique_id

        -- Date lookups (timestamps already cast to TIMESTAMP in view)
        LEFT JOIN warehouse.dim_date dd_purchase
                ON dd_purchase.full_date = o.order_purchase_timestamp::DATE
        LEFT JOIN warehouse.dim_date dd_approved
                ON dd_approved.full_date = o.order_approved_at::DATE
        LEFT JOIN warehouse.dim_date dd_carrier
                ON dd_carrier.full_date = o.order_delivered_carrier_date::DATE
        LEFT JOIN warehouse.dim_date dd_delivered
                ON dd_delivered.full_date = o.order_delivered_customer_date::DATE
        LEFT JOIN warehouse.dim_date dd_estimated
                ON dd_estimated.full_date = o.order_estimated_delivery_date::DATE

        -- Review: latest review per order (pre-aggregated in view)
        LEFT JOIN staging.vw_order_reviews_latest r
                ON o.order_id = r.order_id

        -- Payment aggregate at order level (pre-aggregated in view)
        LEFT JOIN staging.vw_order_payments_agg pay
                ON o.order_id = pay.order_id

        WHERE o.order_id IS NOT NULL
          AND TRIM(o.order_id) != '';
    """)
    cnt = row_count(cursor, "warehouse.fact_order_fulfillment")
    print(f"[+] fact_order_fulfillment: {cnt:,} rows loaded.")
    return cnt


# ------------------------------------------------------------------------------
# Post-load validation
# ------------------------------------------------------------------------------
def validate_warehouse(cursor):
    """Performs comprehensive data quality and reconciliation validations on the warehouse.

    Validates:
        1. Row counts across all dimension and fact tables (must be non-empty).
        2. Uniqueness of dimension natural keys (dim_customer, dim_product, dim_seller).
        3. Fact table grains (1 row per order_item for sales, 1 row per order for fulfillment).
        4. Staging vs warehouse row count sanity checks.
        5. Foreign key integrity and orphan detection across all surrogate keys.
        6. Logical constraints such as absence of negative duration values.
        7. Source reconciliation for fact_sales against staging.order_items (Checks A, B, C, D)
           to detect and report any dropped records or unmapped dimensions.

    Args:
        cursor (psycopg2.extensions.cursor): The database cursor used to execute queries.

    Returns:
        int: Total number of validation errors encountered.
    """
    print("\n" + "=" * 60)
    print("DATA QUALITY VALIDATION")
    print("=" * 60)

    errors = 0

    # 1. Row counts
    print("\n[ROW COUNTS]")
    for tbl in [
        "warehouse.dim_date", "warehouse.dim_customer",
        "warehouse.dim_product", "warehouse.dim_seller",
        "warehouse.fact_sales", "warehouse.fact_order_fulfillment",
    ]:
        cnt = row_count(cursor, tbl)
        status = "[PASS]" if cnt > 0 else "[FAIL]"
        print(f"  {status} {tbl}: {cnt:,} rows")
        if cnt == 0:
            errors += 1

    # 2. Grain checks (dimension uniqueness)
    dim_grain_checks = [
        ("dim_customer", "customer_unique_id"),
        ("dim_product", "product_id"),
        ("dim_seller", "seller_id"),
    ]
    print("\n[GRAIN - DIMENSIONS]")
    for tbl, col in dim_grain_checks:
        cursor.execute(f"""
            SELECT COUNT(*) FROM (
                SELECT {col} FROM warehouse.{tbl}
                GROUP BY {col} HAVING COUNT(*) > 1
            ) t;
        """)
        dups = cursor.fetchone()[0]
        status = "[PASS]" if dups == 0 else "[FAIL]"
        print(f"  {status} {tbl} uniqueness ({col} dups: {dups})")
        if dups > 0:
            errors += 1

    # 3. fact_sales grain
    print("\n[GRAIN - FACT_SALES]")
    cursor.execute("""
        SELECT COUNT(*) FROM (
            SELECT order_id, order_item_id FROM warehouse.fact_sales
            GROUP BY order_id, order_item_id HAVING COUNT(*) > 1
        ) t;
    """)
    fact_sales_dups = cursor.fetchone()[0]
    status = "[PASS]" if fact_sales_dups == 0 else "[FAIL]"
    if fact_sales_dups == 0:
        print(f"  {status} fact_sales grain (1 row = 1 order_item, dups: {fact_sales_dups})")
    else:
        print(f"  {status} fact_sales grain violation: duplicate order_id + order_item_id ({fact_sales_dups})")
        errors += 1

    # 4. fact_order_fulfillment grain
    print("\n[GRAIN - FACT_ORDER_FULFILLMENT]")
    cursor.execute("""
        SELECT COUNT(*) FROM (
            SELECT order_id FROM warehouse.fact_order_fulfillment
            GROUP BY order_id HAVING COUNT(*) > 1
        ) t;
    """)
    fact_order_dups = cursor.fetchone()[0]
    status = "[PASS]" if fact_order_dups == 0 else "[FAIL]"
    if fact_order_dups == 0:
        print(f"  {status} fact_order_fulfillment grain (1 row = 1 order, dups: {fact_order_dups})")
    else:
        print(f"  {status} fact_order_fulfillment grain violation: duplicate order_id ({fact_order_dups})")
        errors += 1

    # 5. Row count sanity: fact_sales vs staging order_items
    print("\n[ROW COUNT SANITY - STAGING VS WAREHOUSE]")
    staging_items = row_count(cursor, "staging.order_items")
    fact_sales_cnt = row_count(cursor, "warehouse.fact_sales")
    print(f"  staging.order_items:       {staging_items:,}")
    print(f"  warehouse.fact_sales:      {fact_sales_cnt:,}")
    if fact_sales_cnt > staging_items:
        print(f"  [FAIL] fact_sales has MORE rows than staging ({fact_sales_cnt} > {staging_items})")
        errors += 1
    else:
        print(f"  [PASS] fact_sales <= staging (delta: {staging_items - fact_sales_cnt:,})")

    staging_orders = row_count(cursor, "staging.orders")
    fact_fulfill_cnt = row_count(cursor, "warehouse.fact_order_fulfillment")
    print(f"  staging.orders:                    {staging_orders:,}")
    print(f"  warehouse.fact_order_fulfillment:  {fact_fulfill_cnt:,}")
    if fact_fulfill_cnt > staging_orders:
        print(f"  [FAIL] fact_order_fulfillment has MORE rows than staging ({fact_fulfill_cnt} > {staging_orders})")
        errors += 1
    else:
        print(f"  [PASS] fact_order_fulfillment <= staging (delta: {staging_orders - fact_fulfill_cnt:,})")

    # 6. FK orphan checks
    print("\n[FK INTEGRITY]")
    fk_checks = [
        ("fact_sales", "customer_key", "dim_customer", "customer_key"),
        ("fact_sales", "product_key", "dim_product", "product_key"),
        ("fact_sales", "seller_key", "dim_seller", "seller_key"),
        ("fact_sales", "date_key", "dim_date", "date_key"),
        ("fact_order_fulfillment", "customer_key", "dim_customer", "customer_key"),
        ("fact_order_fulfillment", "order_purchase_date_key", "dim_date", "date_key"),
    ]
    for fact, fk_col, dim, pk_col in fk_checks:
        cursor.execute(f"""
            SELECT COUNT(*) FROM warehouse.{fact} f
            LEFT JOIN warehouse.{dim} d ON f.{fk_col} = d.{pk_col}
            WHERE f.{fk_col} IS NOT NULL AND d.{pk_col} IS NULL;
        """)
        orphans = cursor.fetchone()[0]
        status = "[PASS]" if orphans == 0 else "[FAIL]"
        label = f"{fact}.{fk_col} -> {dim}.{pk_col}"
        print(f"  {status} {label}: {orphans} orphans")
        if orphans > 0:
            errors += 1

    # 7. No negative durations
    print("\n[DURATION VALIDATION]")
    cursor.execute("""
        SELECT COUNT(*) FROM warehouse.fact_order_fulfillment
        WHERE hours_to_approval < 0
           OR hours_to_carrier < 0
           OR hours_to_customer < 0
           OR total_fulfillment_hours < 0;
    """)
    neg_durations = cursor.fetchone()[0]
    status = "[PASS]" if neg_durations == 0 else "[FAIL]"
    print(f"  {status} Negative durations in fact_order_fulfillment: {neg_durations}")
    if neg_durations > 0:
        errors += 1

    # 8. Source reconciliation validation for fact_sales (prevent silent drop of records)
    print("\n[SOURCE RECONCILIATION - FACT_SALES]")
    cursor.execute("""
        SELECT COUNT(*) FROM staging.order_items
        WHERE order_id IS NOT NULL AND TRIM(order_id) != ''
          AND order_item_id IS NOT NULL AND TRIM(order_item_id) != '';
    """)
    eligible_items = cursor.fetchone()[0]

    # Check A: Order items without order in staging.orders
    cursor.execute("""
        SELECT COUNT(*)
        FROM staging.order_items oi
        LEFT JOIN staging.orders o ON oi.order_id = o.order_id
        WHERE oi.order_id IS NOT NULL AND TRIM(oi.order_id) != ''
          AND o.order_id IS NULL;
    """)
    orphan_orders = cursor.fetchone()[0]

    # Check B: Order items without customer in staging.customers
    cursor.execute("""
        SELECT COUNT(*)
        FROM staging.order_items oi
        JOIN staging.orders o ON oi.order_id = o.order_id
        LEFT JOIN staging.customers sc ON o.customer_id = sc.customer_id
        WHERE oi.order_id IS NOT NULL AND TRIM(oi.order_id) != ''
          AND (o.customer_id IS NULL OR TRIM(o.customer_id) = '' OR sc.customer_id IS NULL);
    """)
    orphan_customers = cursor.fetchone()[0]

    # Check C: Order items whose customer cannot resolve to dim_customer
    cursor.execute("""
        SELECT COUNT(*)
        FROM staging.order_items oi
        JOIN staging.orders o ON oi.order_id = o.order_id
        JOIN staging.customers sc ON o.customer_id = sc.customer_id
        LEFT JOIN warehouse.dim_customer dc ON sc.customer_unique_id = dc.customer_unique_id
        WHERE oi.order_id IS NOT NULL AND TRIM(oi.order_id) != ''
          AND dc.customer_key IS NULL;
    """)
    orphan_dim_cust = cursor.fetchone()[0]

    # Check D: Expected vs actual load comparison
    missing_items = eligible_items - fact_sales_cnt
    reconciliation_pass = (missing_items == 0)

    recon_status = "[PASS]" if reconciliation_pass else "[FAIL]"
    print(f"  {recon_status} fact_sales source reconciliation")
    print(f"      Staging order_items (total)   : {staging_items:,}")
    print(f"      Staging order_items (eligible): {eligible_items:,}")
    print(f"      Warehouse fact_sales (loaded) : {fact_sales_cnt:,}")
    print(f"      Missing records               : {missing_items:,}")
    print(f"      Orphan orders (A)             : {orphan_orders:,}")
    print(f"      Orphan customers (B)          : {orphan_customers:,}")
    print(f"      Unresolved dim_customer (C)   : {orphan_dim_cust:,}")

    if not reconciliation_pass:
        print("  [FAIL] fact_sales source reconciliation")
        print(f"      Expected: {eligible_items:,}")
        print(f"      Loaded:   {fact_sales_cnt:,}")
        print(f"      Missing:  {missing_items:,}")
        reasons = []
        if staging_items != eligible_items:
            reasons.append(f"{staging_items - eligible_items} items have missing order_id/order_item_id")
        if orphan_orders > 0:
            reasons.append(f"{orphan_orders} items reference nonexistent orders")
        if orphan_customers > 0:
            reasons.append(f"{orphan_customers} items reference nonexistent customers")
        if orphan_dim_cust > 0:
            reasons.append(f"{orphan_dim_cust} items have customers unmapped in dim_customer")
        if not reasons:
            reasons.append("Unidentified drop during transform/load")
        print(f"      Reason:   {'; '.join(reasons)}")
        errors += 1

    # Final Summary
    print("\n" + "=" * 60)
    if errors == 0:
        print("VALIDATION PASSED")
    else:
        print("VALIDATION FAILED")
    print(f"Total error count: {errors}")
    print("=" * 60)

    return errors


# ------------------------------------------------------------------------------
# Main Execution Pipeline
# Order: Views -> Truncate -> Dims -> Facts -> Validate -> Commit (Rollback on failure)
# ------------------------------------------------------------------------------
def main():
    """Main execution controller for the ETL warehouse load pipeline.

    Orchestrates the transactional full-refresh workflow:
        0. Creates/refreshes staging views (stg.* aliases + staging.vw_* transforms).
        1. Truncates all warehouse tables in reverse foreign key order.
        2. Loads dimension tables (date, customer, product, seller).
        3. Loads fact tables (sales, order fulfillment).
        4. Executes data quality and reconciliation validations.
        5. Commits transaction if all validations pass, or rolls back on any failure.

    Raises:
        SystemExit: Exits with code 1 if validation fails or an exception occurs.
    """
    start_total = time.time()
    print("=" * 60)
    print(f"LOAD WAREHOUSE: {DB_NAME} ({DB_HOST}:{DB_PORT})")
    print("=" * 60)

    conn = None
    try:
        conn = get_connection()
        conn.autocommit = False
        cursor = conn.cursor()

        # Step 0: Ensure staging views exist (type casting + cleaning layer)
        ensure_staging_views(cursor)

        # Step 1: Truncate for full refresh idempotency
        truncate_warehouse(cursor)

        # Step 2: Load dimensions (facts depend on surrogate keys)
        load_dim_date(cursor)
        load_dim_customer(cursor)
        load_dim_product(cursor)
        load_dim_seller(cursor)

        # Step 3: Load facts
        load_fact_sales(cursor)
        load_fact_order_fulfillment(cursor)

        # Step 4: Validate before commit
        validation_errors = validate_warehouse(cursor)

        if validation_errors > 0:
            print(f"\n[!] {validation_errors} validation error(s). Rolling back transaction.")
            conn.rollback()
            sys.exit(1)
        else:
            conn.commit()
            elapsed = time.time() - start_total
            print(f"\n[+] Warehouse load completed successfully ({elapsed:.2f}s).")

    except Exception as e:
        print(f"\n[ERROR] Pipeline execution failed: {e}", file=sys.stderr)
        if conn:
            conn.rollback()
        sys.exit(1)
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    main()
