"""
==============================================================================
Olist E-Commerce Data Warehouse - Data Quality & Validation Suite
Script: scripts/validate_warehouse.py
Purpose: Post-load validation and data quality auditing for Kimball star schema.
         Validates referential integrity, business rules, temporal logic,
         null rates, formatting, and financial reconciliation.
Author: Data Engineering Team
==============================================================================
"""

import os
import sys
import time
from pathlib import Path
from typing import List, Optional

import pandas as pd
import psycopg2


# Ensure UTF-8 output encoding for Windows Terminal
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# ------------------------------------------------------------------------------
# 1. Environment & Database Connection
# ------------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BASE_DIR / "validation_reports"

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

DB_HOST = os.getenv("DB_HOST") or os.getenv("POSTGRES_HOST") or "localhost"
DB_PORT = os.getenv("DB_PORT") or os.getenv("POSTGRES_PORT") or "5432"
DB_NAME = os.getenv("DB_NAME") or os.getenv("POSTGRES_DB") or "olist"
DB_USER = os.getenv("DB_USER") or os.getenv("POSTGRES_USER") or "postgres"
DB_PASSWORD = os.getenv("DB_PASSWORD") or os.getenv("POSTGRES_PASSWORD") or ""


def get_connection():
    """Establishes connection to PostgreSQL warehouse."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )


# ------------------------------------------------------------------------------
# Data Structure for Check Results
# ------------------------------------------------------------------------------
class CheckResult:
    def __init__(
        self,
        category: str,
        name: str,
        total_evaluated: int,
        failed_count: int,
        severity: str = "CRITICAL",
        violation_df: Optional[pd.DataFrame] = None,
        report_filename: Optional[str] = None,
        notes: str = "",
    ):
        self.category = category
        self.name = name
        self.total_evaluated = total_evaluated
        self.failed_count = failed_count
        self.severity = severity  # "CRITICAL" | "WARNING"
        self.violation_df = violation_df
        self.report_filename = report_filename
        self.notes = notes

    @property
    def error_pct(self) -> float:
        if self.total_evaluated == 0:
            return 0.0
        return (self.failed_count / self.total_evaluated) * 100.0

    @property
    def status(self) -> str:
        if self.failed_count == 0:
            return "PASS"
        return "FAIL" if self.severity == "CRITICAL" else "WARNING"


# ------------------------------------------------------------------------------
# SECTION 1: Kiá»ƒm tra khoÃ¡ & tÃ­nh toÃ n váº¹n tham chiáº¿u (Referential Integrity)
# ------------------------------------------------------------------------------
def check_keys_and_referential_integrity(conn) -> List[CheckResult]:
    results = []
    cursor = conn.cursor()

    # 1.1 Primary Key Unique & Not Null
    pk_definitions = [
        ("warehouse.dim_customer", "customer_key"),
        ("warehouse.dim_date", "date_key"),
        ("warehouse.dim_product", "product_key"),
        ("warehouse.dim_seller", "seller_key"),
        ("warehouse.fact_sales", "sales_key"),
        ("warehouse.fact_order_fulfillment", "fulfillment_key"),
    ]

    for table, pk in pk_definitions:
        query_stats = f"""
            SELECT
                COUNT(*) AS total_rows,
                COUNT(*) - COUNT(DISTINCT {pk}) AS duplicate_count,
                COUNT(*) FILTER (WHERE {pk} IS NULL) AS null_count
            FROM {table};
        """
        cursor.execute(query_stats)
        total, dups, nulls = cursor.fetchone()
        failed = dups + nulls

        violation_df = None
        if failed > 0:
            query_violations = f"""
                SELECT {pk}, COUNT(*) AS occurrences
                FROM {table}
                GROUP BY {pk}
                HAVING COUNT(*) > 1 OR {pk} IS NULL;
            """
            violation_df = pd.read_sql(query_violations, conn)

        table_short = table.split(".")[1]
        results.append(
            CheckResult(
                category="1. Key & RI",
                name=f"PK Unique & Not Null: {table_short}.{pk}",
                total_evaluated=total,
                failed_count=failed,
                severity="CRITICAL",
                violation_df=violation_df,
                report_filename=f"pk_violation_{table_short}_{pk}.csv",
                notes=f"Dups: {dups}, Nulls: {nulls}",
            )
        )

    # 1.2 Fact Sales Grain: (order_id, order_item_id) Uniqueness
    cursor.execute("""
        SELECT COUNT(*) AS total_rows,
               COUNT(*) - COUNT(DISTINCT (order_id, order_item_id)) AS duplicate_count
        FROM warehouse.fact_sales;
    """)
    total, dups = cursor.fetchone()
    violation_df = None
    if dups > 0:
        query_grain = """
            SELECT order_id, order_item_id, COUNT(*) AS occurrences
            FROM warehouse.fact_sales
            GROUP BY order_id, order_item_id
            HAVING COUNT(*) > 1;
        """
        violation_df = pd.read_sql(query_grain, conn)

    results.append(
        CheckResult(
            category="1. Key & RI",
            name="Fact Sales Grain Unique: (order_id, order_item_id)",
            total_evaluated=total,
            failed_count=dups,
            severity="CRITICAL",
            violation_df=violation_df,
            report_filename="grain_duplicate_fact_sales.csv",
        )
    )

    # 1.3 Foreign Key Orphan Checks
    fk_checks = [
        # fact_sales FKs
        ("warehouse.fact_sales", "customer_key", "warehouse.dim_customer", "customer_key"),
        ("warehouse.fact_sales", "product_key", "warehouse.dim_product", "product_key"),
        ("warehouse.fact_sales", "seller_key", "warehouse.dim_seller", "seller_key"),
        ("warehouse.fact_sales", "date_key", "warehouse.dim_date", "date_key"),
        # fact_order_fulfillment FKs
        ("warehouse.fact_order_fulfillment", "customer_key", "warehouse.dim_customer", "customer_key"),
        ("warehouse.fact_order_fulfillment", "order_purchase_date_key", "warehouse.dim_date", "date_key"),
        ("warehouse.fact_order_fulfillment", "order_approved_date_key", "warehouse.dim_date", "date_key"),
        ("warehouse.fact_order_fulfillment", "carrier_pickup_date_key", "warehouse.dim_date", "date_key"),
        ("warehouse.fact_order_fulfillment", "delivered_date_key", "warehouse.dim_date", "date_key"),
        ("warehouse.fact_order_fulfillment", "estimated_delivery_date_key", "warehouse.dim_date", "date_key"),
    ]

    for fact_tbl, fk_col, dim_tbl, dim_pk in fk_checks:
        fact_short = fact_tbl.split(".")[1]
        dim_short = dim_tbl.split(".")[1]

        cursor.execute(f"""
            SELECT
                COUNT(*) FILTER (WHERE f.{fk_col} IS NOT NULL) AS evaluated_rows,
                COUNT(*) FILTER (WHERE f.{fk_col} IS NOT NULL AND d.{dim_pk} IS NULL) AS orphan_count
            FROM {fact_tbl} f
            LEFT JOIN {dim_tbl} d ON f.{fk_col} = d.{dim_pk};
        """)
        evaluated, orphans = cursor.fetchone()

        violation_df = None
        if orphans > 0:
            query_orphans = f"""
                SELECT f.*
                FROM {fact_tbl} f
                LEFT JOIN {dim_tbl} d ON f.{fk_col} = d.{dim_pk}
                WHERE f.{fk_col} IS NOT NULL AND d.{dim_pk} IS NULL
                LIMIT 10000;
            """
            violation_df = pd.read_sql(query_orphans, conn)

        results.append(
            CheckResult(
                category="1. Key & RI",
                name=f"FK Orphan: {fact_short}.{fk_col} -> {dim_short}.{dim_pk}",
                total_evaluated=evaluated,
                failed_count=orphans,
                severity="CRITICAL",
                violation_df=violation_df,
                report_filename=f"fk_orphans_{fact_short}_{fk_col}.csv",
            )
        )

    return results


# ------------------------------------------------------------------------------
# SECTION 2: Kiá»ƒm tra null trÃªn cÃ¡c cá»™t báº¯t buá»™c
# ------------------------------------------------------------------------------
def check_null_percentages_and_mandatory_columns(conn) -> (List[CheckResult], pd.DataFrame):
    results = []
    cursor = conn.cursor()

    mandatory_columns = {
        "dim_customer": ["customer_key", "customer_unique_id"],
        "dim_date": [
            "date_key", "full_date", "year", "quarter", "month",
            "month_name", "week_of_year", "day_of_month", "day_of_week",
            "day_name", "is_weekend"
        ],
        "dim_product": ["product_key", "product_id"],
        "dim_seller": ["seller_key", "seller_id"],
        "fact_sales": [
            "sales_key", "order_id", "order_item_id", "customer_key",
            "product_key", "seller_key", "date_key", "price",
            "freight_value", "sales_amount"
        ],
        "fact_order_fulfillment": [
            "fulfillment_key", "order_id", "customer_key",
            "order_purchase_date_key", "order_status"
        ],
    }

    tables = ["dim_customer", "dim_date", "dim_product", "dim_seller", "fact_sales", "fact_order_fulfillment"]
    all_null_records = []

    for tbl in tables:
        cursor.execute(f"""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'warehouse' AND table_name = '{tbl}'
            ORDER BY ordinal_position;
        """)
        cols = cursor.fetchall()

        cursor.execute(f"SELECT COUNT(*) FROM warehouse.{tbl};")
        tbl_total = cursor.fetchone()[0]

        tbl_mandatory = mandatory_columns.get(tbl, [])

        for col_name, data_type in cols:
            cursor.execute(f"""
                SELECT COUNT(*) FILTER (WHERE {col_name} IS NULL)
                FROM warehouse.{tbl};
            """)
            null_count = cursor.fetchone()[0]
            null_pct = (null_count / tbl_total * 100.0) if tbl_total > 0 else 0.0

            is_mandatory = col_name in tbl_mandatory

            all_null_records.append({
                "table_name": f"warehouse.{tbl}",
                "column_name": col_name,
                "data_type": data_type,
                "total_rows": tbl_total,
                "null_count": null_count,
                "null_pct": round(null_pct, 2),
                "is_mandatory": is_mandatory,
            })

            # If it is a mandatory column, register as a CRITICAL check result
            if is_mandatory:
                violation_df = None
                if null_count > 0:
                    pk_col = cols[0][0]
                    query_nulls = f"""
                        SELECT {pk_col}, {col_name}
                        FROM warehouse.{tbl}
                        WHERE {col_name} IS NULL
                        LIMIT 5000;
                    """
                    violation_df = pd.read_sql(query_nulls, conn)

                results.append(
                    CheckResult(
                        category="2. Null Checks",
                        name=f"Mandatory Column Not Null: {tbl}.{col_name}",
                        total_evaluated=tbl_total,
                        failed_count=null_count,
                        severity="CRITICAL",
                        violation_df=violation_df,
                        report_filename=f"null_mandatory_{tbl}_{col_name}.csv",
                    )
                )

    null_rates_df = pd.DataFrame(all_null_records)
    return results, null_rates_df


# ------------------------------------------------------------------------------
# SECTION 3: Kiá»ƒm tra business rule / range
# ------------------------------------------------------------------------------
def check_business_rules_and_ranges(conn) -> List[CheckResult]:
    results = []
    cursor = conn.cursor()

    # 3.1 Non-negative prices/freight in fact_sales
    cursor.execute("""
        SELECT
            COUNT(*) AS total_rows,
            COUNT(*) FILTER (WHERE price < 0 OR freight_value < 0 OR sales_amount < 0) AS failed_rows
        FROM warehouse.fact_sales;
    """)
    total, failed = cursor.fetchone()
    violation_df = None
    if failed > 0:
        query_neg = """
            SELECT sales_key, order_id, order_item_id, price, freight_value, sales_amount
            FROM warehouse.fact_sales
            WHERE price < 0 OR freight_value < 0 OR sales_amount < 0;
        """
        violation_df = pd.read_sql(query_neg, conn)

    results.append(
        CheckResult(
            category="3. Business Rules",
            name="Non-negative values: price, freight, sales_amount",
            total_evaluated=total,
            failed_count=failed,
            severity="CRITICAL",
            violation_df=violation_df,
            report_filename="business_negative_sales_measures.csv",
        )
    )

    # 3.2 sales_amount == price + freight_value (tolerance 0.01)
    cursor.execute("""
        SELECT
            COUNT(*) AS total_rows,
            COUNT(*) FILTER (WHERE ABS(sales_amount - (price + freight_value)) > 0.01) AS failed_rows
        FROM warehouse.fact_sales;
    """)
    total, failed = cursor.fetchone()
    violation_df = None
    if failed > 0:
        query_calc = """
            SELECT sales_key, order_id, order_item_id, price, freight_value, sales_amount,
                   ROUND((price + freight_value)::numeric, 2) AS expected_sales,
                   ROUND(ABS(sales_amount - (price + freight_value))::numeric, 2) AS diff
            FROM warehouse.fact_sales
            WHERE ABS(sales_amount - (price + freight_value)) > 0.01;
        """
        violation_df = pd.read_sql(query_calc, conn)

    results.append(
        CheckResult(
            category="3. Business Rules",
            name="Sales Amount Match: sales_amount == price + freight (tol 0.01)",
            total_evaluated=total,
            failed_count=failed,
            severity="CRITICAL",
            violation_df=violation_df,
            report_filename="business_sales_amount_mismatch.csv",
        )
    )

    # 3.3 Hours non-negative in fact_order_fulfillment
    cursor.execute("""
        SELECT
            COUNT(*) FILTER (WHERE hours_to_approval IS NOT NULL OR hours_to_carrier IS NOT NULL
                                OR hours_to_customer IS NOT NULL OR total_fulfillment_hours IS NOT NULL) AS evaluated_rows,
            COUNT(*) FILTER (WHERE hours_to_approval < 0 OR hours_to_carrier < 0
                                OR hours_to_customer < 0 OR total_fulfillment_hours < 0) AS failed_rows
        FROM warehouse.fact_order_fulfillment;
    """)
    evaluated, failed = cursor.fetchone()
    violation_df = None
    if failed > 0:
        query_hours = """
            SELECT order_id, hours_to_approval, hours_to_carrier, hours_to_customer, total_fulfillment_hours
            FROM warehouse.fact_order_fulfillment
            WHERE hours_to_approval < 0 OR hours_to_carrier < 0
               OR hours_to_customer < 0 OR total_fulfillment_hours < 0;
        """
        violation_df = pd.read_sql(query_hours, conn)

    results.append(
        CheckResult(
            category="3. Business Rules",
            name="Non-negative hours in fact_order_fulfillment",
            total_evaluated=evaluated,
            failed_count=failed,
            severity="CRITICAL",
            violation_df=violation_df,
            report_filename="business_negative_fulfillment_hours.csv",
        )
    )

    # 3.4 total_fulfillment_hours matches sum of 3 sub-intervals (tol 0.05h for rounding)
    cursor.execute("""
        SELECT
            COUNT(*) FILTER (WHERE hours_to_approval IS NOT NULL AND hours_to_carrier IS NOT NULL
                                AND hours_to_customer IS NOT NULL AND total_fulfillment_hours IS NOT NULL) AS evaluated_rows,
            COUNT(*) FILTER (WHERE hours_to_approval IS NOT NULL AND hours_to_carrier IS NOT NULL
                                AND hours_to_customer IS NOT NULL AND total_fulfillment_hours IS NOT NULL
                                AND ABS(total_fulfillment_hours - (hours_to_approval + hours_to_carrier + hours_to_customer)) > 0.05) AS failed_rows
        FROM warehouse.fact_order_fulfillment;
    """)
    evaluated, failed = cursor.fetchone()
    violation_df = None
    if failed > 0:
        query_sum = """
            SELECT order_id, hours_to_approval, hours_to_carrier, hours_to_customer, total_fulfillment_hours,
                   ROUND((hours_to_approval + hours_to_carrier + hours_to_customer)::numeric, 2) AS sum_stages,
                   ROUND(ABS(total_fulfillment_hours - (hours_to_approval + hours_to_carrier + hours_to_customer))::numeric, 2) AS diff
            FROM warehouse.fact_order_fulfillment
            WHERE hours_to_approval IS NOT NULL AND hours_to_carrier IS NOT NULL
              AND hours_to_customer IS NOT NULL AND total_fulfillment_hours IS NOT NULL
              AND ABS(total_fulfillment_hours - (hours_to_approval + hours_to_carrier + hours_to_customer)) > 0.05;
        """
        violation_df = pd.read_sql(query_sum, conn)

    results.append(
        CheckResult(
            category="3. Business Rules",
            name="Fulfillment Hours Additivity: total == sum(stages) (tol 0.05h)",
            total_evaluated=evaluated,
            failed_count=failed,
            severity="WARNING",
            violation_df=violation_df,
            report_filename="business_fulfillment_hours_additivity.csv",
        )
    )

    # 3.5 review_score range: 1 to 5 (when not null)
    cursor.execute("""
        SELECT
            COUNT(*) FILTER (WHERE review_score IS NOT NULL) AS evaluated_rows,
            COUNT(*) FILTER (WHERE review_score IS NOT NULL AND (review_score < 1 OR review_score > 5)) AS failed_rows
        FROM warehouse.fact_order_fulfillment;
    """)
    evaluated, failed = cursor.fetchone()
    violation_df = None
    if failed > 0:
        query_rev = """
            SELECT order_id, review_score
            FROM warehouse.fact_order_fulfillment
            WHERE review_score IS NOT NULL AND (review_score < 1 OR review_score > 5);
        """
        violation_df = pd.read_sql(query_rev, conn)

    results.append(
        CheckResult(
            category="3. Business Rules",
            name="Review Score Range: 1 <= review_score <= 5",
            total_evaluated=evaluated,
            failed_count=failed,
            severity="WARNING",
            violation_df=violation_df,
            report_filename="business_invalid_review_score.csv",
        )
    )

    # 3.6 order_status distinct valid set
    valid_statuses = {'delivered', 'shipped', 'canceled', 'unavailable', 'invoiced', 'processing', 'created', 'approved'}
    cursor.execute("""
        SELECT DISTINCT order_status, COUNT(*)
        FROM warehouse.fact_order_fulfillment
        GROUP BY order_status;
    """)
    status_counts = cursor.fetchall()
    total_orders = sum(r[1] for r in status_counts)
    invalid_status_orders = sum(r[1] for r in status_counts if r[0] not in valid_statuses)

    violation_df = None
    if invalid_status_orders > 0:
        query_status = f"""
            SELECT order_id, order_status
            FROM warehouse.fact_order_fulfillment
            WHERE order_status NOT IN ({','.join(repr(s) for s in valid_statuses)});
        """
        violation_df = pd.read_sql(query_status, conn)

    status_str = ", ".join(f"'{r[0]}': {r[1]:,}" for r in sorted(status_counts, key=lambda x: x[1], reverse=True))
    results.append(
        CheckResult(
            category="3. Business Rules",
            name="Valid order_status Domain",
            total_evaluated=total_orders,
            failed_count=invalid_status_orders,
            severity="WARNING",
            violation_df=violation_df,
            report_filename="business_invalid_order_status.csv",
            notes=f"Distinct values: {status_str}",
        )
    )

    # 3.7 is_on_time consistency with days_vs_estimate (with 0.01 days margin)
    cursor.execute("""
        SELECT
            COUNT(*) FILTER (WHERE is_on_time IS NOT NULL AND days_vs_estimate IS NOT NULL) AS evaluated_rows,
            COUNT(*) FILTER (WHERE is_on_time IS NOT NULL AND days_vs_estimate IS NOT NULL
                                AND ((days_vs_estimate < -0.01 AND is_on_time = FALSE)
                                  OR (days_vs_estimate > 0.01 AND is_on_time = TRUE))) AS failed_rows
        FROM warehouse.fact_order_fulfillment;
    """)
    evaluated, failed = cursor.fetchone()
    violation_df = None
    if failed > 0:
        query_ontime = """
            SELECT order_id, days_vs_estimate, is_on_time
            FROM warehouse.fact_order_fulfillment
            WHERE is_on_time IS NOT NULL AND days_vs_estimate IS NOT NULL
              AND ((days_vs_estimate < -0.01 AND is_on_time = FALSE)
                OR (days_vs_estimate > 0.01 AND is_on_time = TRUE));
        """
        violation_df = pd.read_sql(query_ontime, conn)

    results.append(
        CheckResult(
            category="3. Business Rules",
            name="On-Time Consistency: is_on_time vs days_vs_estimate",
            total_evaluated=evaluated,
            failed_count=failed,
            severity="WARNING",
            violation_df=violation_df,
            report_filename="business_ontime_estimate_mismatch.csv",
        )
    )

    # 3.8 payment_count >= 1 when total_payment_value > 0
    cursor.execute("""
        SELECT
            COUNT(*) FILTER (WHERE total_payment_value > 0) AS evaluated_rows,
            COUNT(*) FILTER (WHERE total_payment_value > 0 AND (payment_count IS NULL OR payment_count < 1)) AS failed_rows
        FROM warehouse.fact_order_fulfillment;
    """)
    evaluated, failed = cursor.fetchone()
    violation_df = None
    if failed > 0:
        query_pay = """
            SELECT order_id, total_payment_value, payment_count
            FROM warehouse.fact_order_fulfillment
            WHERE total_payment_value > 0 AND (payment_count IS NULL OR payment_count < 1);
        """
        violation_df = pd.read_sql(query_pay, conn)

    results.append(
        CheckResult(
            category="3. Business Rules",
            name="Payment Count >= 1 when total_payment_value > 0",
            total_evaluated=evaluated,
            failed_count=failed,
            severity="WARNING",
            violation_df=violation_df,
            report_filename="business_payment_count_zero.csv",
        )
    )

    return results


# ------------------------------------------------------------------------------
# SECTION 4: Kiá»ƒm tra tÃ­nh nháº¥t quÃ¡n thá»© tá»± thá»i gian (Date Logic)
# ------------------------------------------------------------------------------
def check_date_logic(conn) -> List[CheckResult]:
    results = []
    cursor = conn.cursor()

    # 4.1 purchase <= approved
    cursor.execute("""
        SELECT
            COUNT(*) FILTER (WHERE order_purchase_date_key IS NOT NULL AND order_approved_date_key IS NOT NULL) AS evaluated_rows,
            COUNT(*) FILTER (WHERE order_purchase_date_key IS NOT NULL AND order_approved_date_key IS NOT NULL
                                AND order_purchase_date_key > order_approved_date_key) AS failed_rows
        FROM warehouse.fact_order_fulfillment;
    """)
    evaluated, failed = cursor.fetchone()
    violation_df = None
    if failed > 0:
        query_violation = """
            SELECT order_id, order_purchase_date_key, order_approved_date_key, order_status
            FROM warehouse.fact_order_fulfillment
            WHERE order_purchase_date_key IS NOT NULL AND order_approved_date_key IS NOT NULL
              AND order_purchase_date_key > order_approved_date_key;
        """
        violation_df = pd.read_sql(query_violation, conn)

    results.append(
        CheckResult(
            category="4. Date Logic",
            name="Timeline: purchase_date_key <= approved_date_key",
            total_evaluated=evaluated,
            failed_count=failed,
            severity="CRITICAL",
            violation_df=violation_df,
            report_filename="date_logic_purchase_gt_approved.csv",
        )
    )

    # 4.2 approved <= carrier
    cursor.execute("""
        SELECT
            COUNT(*) FILTER (WHERE order_approved_date_key IS NOT NULL AND carrier_pickup_date_key IS NOT NULL) AS evaluated_rows,
            COUNT(*) FILTER (WHERE order_approved_date_key IS NOT NULL AND carrier_pickup_date_key IS NOT NULL
                                AND order_approved_date_key > carrier_pickup_date_key) AS failed_rows
        FROM warehouse.fact_order_fulfillment;
    """)
    evaluated, failed = cursor.fetchone()
    violation_df = None
    if failed > 0:
        query_violation = """
            SELECT order_id, order_purchase_date_key, order_approved_date_key,
                   carrier_pickup_date_key, delivered_date_key, order_status
            FROM warehouse.fact_order_fulfillment
            WHERE order_approved_date_key IS NOT NULL AND carrier_pickup_date_key IS NOT NULL
              AND order_approved_date_key > carrier_pickup_date_key;
        """
        violation_df = pd.read_sql(query_violation, conn)

    results.append(
        CheckResult(
            category="4. Date Logic",
            name="Timeline: approved_date_key <= carrier_date_key",
            total_evaluated=evaluated,
            failed_count=failed,
            severity="WARNING",  # Known carrier logging delay in source dataset
            violation_df=violation_df,
            report_filename="date_logic_approved_gt_carrier.csv",
            notes="Known source logging anomaly (carrier dispatched before approval logged)",
        )
    )

    # 4.3 carrier <= delivered
    cursor.execute("""
        SELECT
            COUNT(*) FILTER (WHERE carrier_pickup_date_key IS NOT NULL AND delivered_date_key IS NOT NULL) AS evaluated_rows,
            COUNT(*) FILTER (WHERE carrier_pickup_date_key IS NOT NULL AND delivered_date_key IS NOT NULL
                                AND carrier_pickup_date_key > delivered_date_key) AS failed_rows
        FROM warehouse.fact_order_fulfillment;
    """)
    evaluated, failed = cursor.fetchone()
    violation_df = None
    if failed > 0:
        query_violation = """
            SELECT order_id, carrier_pickup_date_key, delivered_date_key, order_status
            FROM warehouse.fact_order_fulfillment
            WHERE carrier_pickup_date_key IS NOT NULL AND delivered_date_key IS NOT NULL
              AND carrier_pickup_date_key > delivered_date_key;
        """
        violation_df = pd.read_sql(query_violation, conn)

    results.append(
        CheckResult(
            category="4. Date Logic",
            name="Timeline: carrier_date_key <= delivered_date_key",
            total_evaluated=evaluated,
            failed_count=failed,
            severity="WARNING",  # Known postal scan anomaly in source dataset
            violation_df=violation_df,
            report_filename="date_logic_carrier_gt_delivered.csv",
            notes="Known source logging anomaly (carrier scan logged post-delivery)",
        )
    )

    return results


# ------------------------------------------------------------------------------
# SECTION 5: Kiá»ƒm tra tÃ­nh Ä‘áº§y Ä‘á»§ cá»§a dim_date
# ------------------------------------------------------------------------------
def check_dim_date_completeness(conn) -> List[CheckResult]:
    results = []
    cursor = conn.cursor()

    # 5.1 date_key format matches full_date (YYYYMMDD)
    cursor.execute("""
        SELECT
            COUNT(*) AS total_rows,
            COUNT(*) FILTER (WHERE TO_CHAR(full_date, 'YYYYMMDD')::INT != date_key) AS failed_rows
        FROM warehouse.dim_date;
    """)
    total, failed = cursor.fetchone()
    violation_df = None
    if failed > 0:
        query_format = """
            SELECT date_key, full_date, TO_CHAR(full_date, 'YYYYMMDD')::INT AS expected_date_key
            FROM warehouse.dim_date
            WHERE TO_CHAR(full_date, 'YYYYMMDD')::INT != date_key;
        """
        violation_df = pd.read_sql(query_format, conn)

    results.append(
        CheckResult(
            category="5. Dim Date",
            name="Date Key Format Match: date_key == YYYYMMDD(full_date)",
            total_evaluated=total,
            failed_count=failed,
            severity="CRITICAL",
            violation_df=violation_df,
            report_filename="dim_date_format_mismatch.csv",
        )
    )

    # 5.2 No gaps in dim_date calendar range
    cursor.execute("""
        WITH expected AS (
            SELECT generate_series(
                (SELECT MIN(full_date) FROM warehouse.dim_date),
                (SELECT MAX(full_date) FROM warehouse.dim_date),
                '1 day'::interval
            )::DATE AS expected_date
        )
        SELECT
            (SELECT COUNT(*) FROM expected) AS total_expected_days,
            COUNT(*) FILTER (WHERE d.full_date IS NULL) AS missing_days
        FROM expected e
        LEFT JOIN warehouse.dim_date d ON e.expected_date = d.full_date;
    """)
    total_days, missing_days = cursor.fetchone()
    violation_df = None
    if missing_days > 0:
        query_gaps = """
            WITH expected AS (
                SELECT generate_series(
                    (SELECT MIN(full_date) FROM warehouse.dim_date),
                    (SELECT MAX(full_date) FROM warehouse.dim_date),
                    '1 day'::interval
                )::DATE AS expected_date
            )
            SELECT e.expected_date AS missing_date
            FROM expected e
            LEFT JOIN warehouse.dim_date d ON e.expected_date = d.full_date
            WHERE d.full_date IS NULL;
        """
        violation_df = pd.read_sql(query_gaps, conn)

    results.append(
        CheckResult(
            category="5. Dim Date",
            name="No Calendar Gaps in dim_date (full_date continuous)",
            total_evaluated=total_days,
            failed_count=missing_days,
            severity="CRITICAL",
            violation_df=violation_df,
            report_filename="dim_date_missing_gaps.csv",
        )
    )

    # 5.3 Fact table dates covered by dim_date
    cursor.execute("""
        SELECT
            MIN(order_purchase_date_key) AS min_fact_date,
            MAX(order_purchase_date_key) AS max_fact_date
        FROM warehouse.fact_order_fulfillment;
    """)
    min_fact, max_fact = cursor.fetchone()

    cursor.execute("""
        SELECT
            MIN(date_key) AS min_dim_date,
            MAX(date_key) AS max_dim_date
        FROM warehouse.dim_date;
    """)
    min_dim, max_dim = cursor.fetchone()

    coverage_failed = 0
    if min_fact < min_dim or max_fact > max_dim:
        coverage_failed = 1

    results.append(
        CheckResult(
            category="5. Dim Date",
            name="Dim Date Range Covers Fact Dates",
            total_evaluated=1,
            failed_count=coverage_failed,
            severity="CRITICAL",
            notes=f"Fact range: [{min_fact}..{max_fact}], Dim range: [{min_dim}..{max_dim}]",
        )
    )

    return results


# ------------------------------------------------------------------------------
# SECTION 6: Kiá»ƒm tra Ä‘á»‹nh dáº¡ng (Format Checks)
# ------------------------------------------------------------------------------
def check_formatting_and_strings(conn) -> List[CheckResult]:
    results = []
    cursor = conn.cursor()

    # 6.1 zip_code_prefix length == 5 in dim_customer and dim_seller
    for tbl in ["dim_customer", "dim_seller"]:
        cursor.execute(f"""
            SELECT
                COUNT(*) FILTER (WHERE zip_code_prefix IS NOT NULL) AS evaluated_rows,
                COUNT(*) FILTER (WHERE zip_code_prefix IS NOT NULL AND LENGTH(TRIM(zip_code_prefix)) != 5) AS failed_rows
            FROM warehouse.{tbl};
        """)
        evaluated, failed = cursor.fetchone()
        violation_df = None
        if failed > 0:
            query_zip = f"""
                SELECT *
                FROM warehouse.{tbl}
                WHERE zip_code_prefix IS NOT NULL AND LENGTH(TRIM(zip_code_prefix)) != 5;
            """
            violation_df = pd.read_sql(query_zip, conn)

        results.append(
            CheckResult(
                category="6. Formatting",
                name=f"Zip Code Length == 5: {tbl}.zip_code_prefix",
                total_evaluated=evaluated,
                failed_count=failed,
                severity="CRITICAL",
                violation_df=violation_df,
                report_filename=f"format_invalid_zip_{tbl}.csv",
            )
        )

    # 6.2 state code length == 2 in dim_customer and dim_seller
    for tbl, state_col in [("dim_customer", "customer_state"), ("dim_seller", "seller_state")]:
        cursor.execute(f"""
            SELECT
                COUNT(*) FILTER (WHERE {state_col} IS NOT NULL) AS evaluated_rows,
                COUNT(*) FILTER (WHERE {state_col} IS NOT NULL AND LENGTH(TRIM({state_col})) != 2) AS failed_rows
            FROM warehouse.{tbl};
        """)
        evaluated, failed = cursor.fetchone()
        violation_df = None
        if failed > 0:
            query_state = f"""
                SELECT *
                FROM warehouse.{tbl}
                WHERE {state_col} IS NOT NULL AND LENGTH(TRIM({state_col})) != 2;
            """
            violation_df = pd.read_sql(query_state, conn)

        results.append(
            CheckResult(
                category="6. Formatting",
                name=f"State Code Length == 2: {tbl}.{state_col}",
                total_evaluated=evaluated,
                failed_count=failed,
                severity="CRITICAL",
                violation_df=violation_df,
                report_filename=f"format_invalid_state_{tbl}.csv",
            )
        )

    # 6.3 Whitespace trimming check (no leading/trailing spaces)
    trim_targets = [
        ("dim_customer", "customer_city"),
        ("dim_seller", "seller_city"),
        ("dim_product", "category_name"),
        ("dim_product", "category_name_english"),
    ]

    for tbl, col in trim_targets:
        cursor.execute(f"""
            SELECT
                COUNT(*) FILTER (WHERE {col} IS NOT NULL) AS evaluated_rows,
                COUNT(*) FILTER (WHERE {col} IS NOT NULL AND {col} != TRIM({col})) AS failed_rows
            FROM warehouse.{tbl};
        """)
        evaluated, failed = cursor.fetchone()
        violation_df = None
        if failed > 0:
            query_trim = f"""
                SELECT {col}
                FROM warehouse.{tbl}
                WHERE {col} IS NOT NULL AND {col} != TRIM({col})
                LIMIT 5000;
            """
            violation_df = pd.read_sql(query_trim, conn)

        results.append(
            CheckResult(
                category="6. Formatting",
                name=f"No Untrimmed Spaces: {tbl}.{col}",
                total_evaluated=evaluated,
                failed_count=failed,
                severity="WARNING",
                violation_df=violation_df,
                report_filename=f"format_untrimmed_{tbl}_{col}.csv",
            )
        )

    return results


# ------------------------------------------------------------------------------
# SECTION 7: Kiá»ƒm tra Ä‘á»‘i soÃ¡t sá»‘ liá»‡u tá»•ng há»£p (Reconciliation)
# ------------------------------------------------------------------------------
def check_reconciliation(conn) -> List[CheckResult]:
    results = []
    cursor = conn.cursor()

    # Total sales_amount in fact_sales vs total_payment_value in fact_order_fulfillment
    # Discrepancy threshold > 1% (0.01)
    query_recon_stats = """
        WITH sales_agg AS (
            SELECT order_id, SUM(sales_amount) AS total_sales_amount
            FROM warehouse.fact_sales
            GROUP BY order_id
        )
        SELECT
            COUNT(*) AS total_matched_orders,
            COUNT(*) FILTER (WHERE f.total_payment_value IS NOT NULL
                               AND f.total_payment_value > 0
                               AND (ABS(s.total_sales_amount - f.total_payment_value) / f.total_payment_value) > 0.01) AS discrepancy_count
        FROM sales_agg s
        JOIN warehouse.fact_order_fulfillment f ON s.order_id = f.order_id;
    """
    cursor.execute(query_recon_stats)
    evaluated, failed = cursor.fetchone()

    violation_df = None
    if failed > 0:
        query_recon_details = """
            WITH sales_agg AS (
                SELECT order_id, SUM(sales_amount) AS total_sales_amount
                FROM warehouse.fact_sales
                GROUP BY order_id
            )
            SELECT
                f.order_id,
                f.order_status,
                s.total_sales_amount,
                f.total_payment_value,
                ROUND(ABS(s.total_sales_amount - f.total_payment_value)::numeric, 2) AS diff_amount,
                ROUND((ABS(s.total_sales_amount - f.total_payment_value) / f.total_payment_value * 100.0)::numeric, 2) AS diff_percent
            FROM sales_agg s
            JOIN warehouse.fact_order_fulfillment f ON s.order_id = f.order_id
            WHERE f.total_payment_value IS NOT NULL
              AND f.total_payment_value > 0
              AND (ABS(s.total_sales_amount - f.total_payment_value) / f.total_payment_value) > 0.01
            ORDER BY diff_percent DESC;
        """
        violation_df = pd.read_sql(query_recon_details, conn)

    results.append(
        CheckResult(
            category="7. Reconciliation",
            name="Order Sales vs Payment Discrepancy (> 1% diff)",
            total_evaluated=evaluated,
            failed_count=failed,
            severity="WARNING",  # Voucher/coupon adjustments in raw dataset
            violation_df=violation_df,
            report_filename="reconciliation_sales_vs_payment_diff_gt_1pct.csv",
            notes="Occurs due to voucher discounts and split installment adjustments in raw source",
        )
    )

    return results


# ------------------------------------------------------------------------------
# Report Generation & Printing
# ------------------------------------------------------------------------------
def generate_reports(all_results: List[CheckResult], null_rates_df: pd.DataFrame) -> List[Path]:
    """Saves detailed violation dataframes and null rates to CSV files in validation_reports/."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    generated_files = []

    # 1. Save complete null rates overview
    null_rates_file = REPORTS_DIR / "warehouse_null_rates_overview.csv"
    null_rates_df.to_csv(null_rates_file, index=False, encoding="utf-8")
    generated_files.append(null_rates_file)

    # 2. Save individual check violation reports
    for res in all_results:
        if res.failed_count > 0 and res.violation_df is not None and res.report_filename:
            report_path = REPORTS_DIR / res.report_filename
            res.violation_df.to_csv(report_path, index=False, encoding="utf-8")
            generated_files.append(report_path)

    return generated_files


def print_summary_table(all_results: List[CheckResult]):
    """Renders a structured summary table to console."""
    print("\n" + "=" * 115)
    print(f"DATA WAREHOUSE QUALITY VALIDATION SUMMARY: {DB_NAME} ({DB_HOST}:{DB_PORT})")
    print("=" * 115)

    headers = f"{'#':<3} | {'Category':<18} | {'Check Name':<45} | {'Total':>10} | {'Failed':>8} | {'Error %':>8} | {'Status':<7} | {'Severity':<8}"
    print(headers)
    print("-" * 115)

    for idx, res in enumerate(all_results, start=1):

        if res.status == "PASS":
            status_tag = "[PASS]"
        elif res.status == "FAIL":
            status_tag = "[FAIL]"
        else:
            status_tag = "[WARN]"

        print(
            f"{idx:<3} | {res.category:<18} | {res.name:<45} | "
            f"{res.total_evaluated:>10,d} | {res.failed_count:>8,d} | "
            f"{res.error_pct:>7.2f}% | {status_tag:<7} | {res.severity:<8}"
        )

    print("=" * 115)


# ------------------------------------------------------------------------------
# Main Controller
# ------------------------------------------------------------------------------
def main():
    start_time = time.time()
    print("=" * 70)
    print("STARTING WAREHOUSE DATA VALIDATION SUITE")
    print(f"Database: {DB_NAME} | Host: {DB_HOST}:{DB_PORT} | Reports: validation_reports/")
    print("=" * 70)

    conn = None
    try:
        conn = get_connection()
        conn.autocommit = True

        all_results: List[CheckResult] = []

        # 1. Keys & Referential Integrity
        print("[*] 1/7 Running Key & Referential Integrity checks...")
        all_results.extend(check_keys_and_referential_integrity(conn))

        # 2. Null Checks & Mandatory Columns
        print("[*] 2/7 Running Null checks on mandatory columns...")
        null_res, null_rates_df = check_null_percentages_and_mandatory_columns(conn)
        all_results.extend(null_res)

        # 3. Business Rules & Value Ranges
        print("[*] 3/7 Running Business Rule & Value Range checks...")
        all_results.extend(check_business_rules_and_ranges(conn))

        # 4. Date Logic & Sequences
        print("[*] 4/7 Running Date Logic & Sequence checks...")
        all_results.extend(check_date_logic(conn))

        # 5. Dim Date Completeness
        print("[*] 5/7 Running Dim Date completeness checks...")
        all_results.extend(check_dim_date_completeness(conn))

        # 6. Formatting & String Integrity
        print("[*] 6/7 Running Format & String integrity checks...")
        all_results.extend(check_formatting_and_strings(conn))

        # 7. Financial Reconciliation
        print("[*] 7/7 Running Financial Reconciliation checks...")
        all_results.extend(check_reconciliation(conn))

        # Print Console Summary Table
        print_summary_table(all_results)

        # Export Detailed CSV Reports
        generated_reports = generate_reports(all_results, null_rates_df)

        print("\n" + "=" * 70)
        print("DETAILED CSV AUDIT REPORTS GENERATED:")
        print("=" * 70)
        for p in generated_reports:
            print(f"  -> {p.relative_to(BASE_DIR)}")

        # Count Critical Failures vs Warnings
        critical_failures = sum(1 for r in all_results if r.severity == "CRITICAL" and r.failed_count > 0)
        warning_anomalies = sum(1 for r in all_results if r.severity == "WARNING" and r.failed_count > 0)
        total_passed = sum(1 for r in all_results if r.failed_count == 0)

        elapsed = time.time() - start_time

        print("\n" + "=" * 70)
        print("FINAL VERDICT:")
        print("=" * 70)
        print(f"  Total Checks Executed : {len(all_results)}")
        print(f"  Checks Passed [PASS]  : {total_passed}")
        print(f"  Business Warnings     : {warning_anomalies}")
        print(f"  Critical Failures     : {critical_failures}")
        print(f"  Execution Time        : {elapsed:.2f}s")
        print("=" * 70)

        if critical_failures > 0:
            print("\n[CRITICAL FAILURE] Referential integrity or critical business rules violated!")
            print("Action: Pipeline halted. Review detailed CSV reports before building dashboards.\n")
            sys.exit(1)
        else:
            print("\n[SUCCESS] All CRITICAL warehouse integrity checks PASSED!")
            print("Data is clean, consistent, and ready for Analytics & BI Dashboards.\n")
            sys.exit(0)

    except Exception as e:
        print(f"\n[FATAL ERROR] Validation process failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(2)
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    main()
