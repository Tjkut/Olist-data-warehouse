-- ==============================================================================
-- Olist E-Commerce Data Pipeline - Staging Views (PostgreSQL)
-- Purpose: Type casting, cleaning, and pre-aggregation layer between raw staging
--          tables and the warehouse INSERT logic.
-- Convention: staging.vw_<entity> reads directly from staging.<entity>
-- Usage: Executed by ensure_staging_views() in load_warehouse.py
-- ==============================================================================

CREATE SCHEMA IF NOT EXISTS staging;

-- ==============================================================================
-- STAGING VIEWS: Type casting, cleaning, and pre-aggregation
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- staging.vw_customers
-- Retains zip_code_prefix as TEXT (preserves leading zeros), trims text columns.
-- Filters out records with NULL/empty customer_unique_id.
-- ------------------------------------------------------------------------------
DROP VIEW IF EXISTS staging.vw_customers CASCADE;
CREATE OR REPLACE VIEW staging.vw_customers AS
SELECT
    customer_id,
    customer_unique_id,
    TRIM(customer_city)            AS customer_city,
    TRIM(customer_state)           AS customer_state,
    TRIM(customer_zip_code_prefix) AS customer_zip_code_prefix
FROM staging.customers
WHERE customer_unique_id IS NOT NULL
  AND TRIM(customer_unique_id) != '';

-- ------------------------------------------------------------------------------
-- staging.vw_orders
-- Casts all timestamp columns from TEXT to TIMESTAMP via NULLIF.
-- Retains order_id, customer_id, order_status as-is (TEXT).
-- ------------------------------------------------------------------------------
DROP VIEW IF EXISTS staging.vw_orders CASCADE;
CREATE OR REPLACE VIEW staging.vw_orders AS
SELECT
    order_id,
    customer_id,
    order_status,
    NULLIF(order_purchase_timestamp,      '')::TIMESTAMP AS order_purchase_timestamp,
    NULLIF(order_approved_at,             '')::TIMESTAMP AS order_approved_at,
    NULLIF(order_delivered_carrier_date,  '')::TIMESTAMP AS order_delivered_carrier_date,
    NULLIF(order_delivered_customer_date, '')::TIMESTAMP AS order_delivered_customer_date,
    NULLIF(order_estimated_delivery_date, '')::TIMESTAMP AS order_estimated_delivery_date
FROM staging.orders;

-- ------------------------------------------------------------------------------
-- staging.vw_order_items
-- Casts order_item_id to SMALLINT, price and freight_value to NUMERIC(12,2).
-- Filters out records with NULL/empty order_id or order_item_id.
-- ------------------------------------------------------------------------------
DROP VIEW IF EXISTS staging.vw_order_items CASCADE;
CREATE OR REPLACE VIEW staging.vw_order_items AS
SELECT
    order_id,
    NULLIF(order_item_id, '')::SMALLINT      AS order_item_id,
    product_id,
    seller_id,
    NULLIF(price,         '')::NUMERIC(12,2) AS price,
    NULLIF(freight_value, '')::NUMERIC(12,2) AS freight_value
FROM staging.order_items
WHERE order_id IS NOT NULL AND TRIM(order_id) != ''
  AND order_item_id IS NOT NULL AND TRIM(order_item_id) != '';

-- ------------------------------------------------------------------------------
-- staging.vw_products
-- Joins with category translation, applies COALESCE for English category name.
-- Casts numeric dimension attributes from TEXT. Filters NULL/empty product_id.
-- ------------------------------------------------------------------------------
DROP VIEW IF EXISTS staging.vw_products CASCADE;
CREATE OR REPLACE VIEW staging.vw_products AS
SELECT
    p.product_id,
    p.product_category_name                  AS category_name,
    COALESCE(
        t.product_category_name_english,
        p.product_category_name,
        'unknown'
    )                                        AS category_name_english,
    NULLIF(p.product_name_lenght,        '')::INT     AS product_name_length,
    NULLIF(p.product_description_lenght, '')::INT     AS product_description_length,
    NULLIF(p.product_photos_qty,         '')::INT     AS product_photos_qty,
    NULLIF(p.product_weight_g,           '')::NUMERIC AS product_weight_g,
    NULLIF(p.product_length_cm,          '')::NUMERIC AS product_length_cm,
    NULLIF(p.product_height_cm,          '')::NUMERIC AS product_height_cm,
    NULLIF(p.product_width_cm,           '')::NUMERIC AS product_width_cm
FROM staging.products p
LEFT JOIN staging.product_category_name_translation t
       ON p.product_category_name = t.product_category_name
WHERE p.product_id IS NOT NULL
  AND TRIM(p.product_id) != '';

-- ------------------------------------------------------------------------------
-- staging.vw_sellers
-- Filters out records with NULL/empty seller_id. Trims text columns.
-- ------------------------------------------------------------------------------
DROP VIEW IF EXISTS staging.vw_sellers CASCADE;
CREATE OR REPLACE VIEW staging.vw_sellers AS
SELECT
    seller_id,
    TRIM(seller_city)            AS seller_city,
    TRIM(seller_state)           AS seller_state,
    TRIM(seller_zip_code_prefix) AS seller_zip_code_prefix
FROM staging.sellers
WHERE seller_id IS NOT NULL
  AND TRIM(seller_id) != '';

-- ------------------------------------------------------------------------------
-- staging.vw_order_payments_agg
-- Pre-aggregates payment data at order level for fact_order_fulfillment.
-- Avoids grain inflation when joined to orders.
-- ------------------------------------------------------------------------------
DROP VIEW IF EXISTS staging.vw_order_payments_agg CASCADE;
CREATE OR REPLACE VIEW staging.vw_order_payments_agg AS
SELECT
    order_id,
    SUM(NULLIF(payment_value, '')::NUMERIC(12,2)) AS total_payment_value,
    COUNT(*)::SMALLINT                             AS payment_count
FROM staging.order_payments
GROUP BY order_id;

-- ------------------------------------------------------------------------------
-- staging.vw_order_reviews_latest
-- Selects the most recent review per order_id by review_creation_date.
-- Uses DISTINCT ON for PostgreSQL-native deduplication.
-- ------------------------------------------------------------------------------
DROP VIEW IF EXISTS staging.vw_order_reviews_latest CASCADE;
CREATE OR REPLACE VIEW staging.vw_order_reviews_latest AS
SELECT DISTINCT ON (order_id)
    order_id,
    NULLIF(review_score, '')::SMALLINT AS review_score
FROM staging.order_reviews
WHERE review_score IS NOT NULL
  AND TRIM(review_score) != ''
ORDER BY order_id, review_creation_date DESC;
