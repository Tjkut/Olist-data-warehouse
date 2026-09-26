-- ==============================================================================
-- Olist E-Commerce Data Pipeline - Staging Schema (PostgreSQL)
-- Strategy: Raw Staging (all columns defined as TEXT to ensure safe ingestion)
-- ==============================================================================

CREATE SCHEMA IF NOT EXISTS staging;

-- Clean up any legacy prefixed tables
DROP TABLE IF EXISTS staging.olist_customers CASCADE;
DROP TABLE IF EXISTS staging.olist_orders CASCADE;
DROP TABLE IF EXISTS staging.olist_order_items CASCADE;
DROP TABLE IF EXISTS staging.olist_order_payments CASCADE;
DROP TABLE IF EXISTS staging.olist_order_reviews CASCADE;
DROP TABLE IF EXISTS staging.olist_products CASCADE;
DROP TABLE IF EXISTS staging.olist_sellers CASCADE;
DROP TABLE IF EXISTS staging.olist_geolocation CASCADE;

-- ------------------------------------------------------------------------------
-- 1. Customers
-- Source: olist_customers_dataset.csv
-- ------------------------------------------------------------------------------
DROP TABLE IF EXISTS staging.customers CASCADE;

CREATE TABLE staging.customers (
    customer_id                 TEXT,
    customer_unique_id          TEXT,
    customer_zip_code_prefix    TEXT,
    customer_city               TEXT,
    customer_state              TEXT
);

-- ------------------------------------------------------------------------------
-- 2. Orders
-- Source: olist_orders_dataset.csv
-- ------------------------------------------------------------------------------
DROP TABLE IF EXISTS staging.orders CASCADE;

CREATE TABLE staging.orders (
    order_id                         TEXT,
    customer_id                      TEXT,
    order_status                     TEXT,
    order_purchase_timestamp         TEXT,
    order_approved_at                TEXT,
    order_delivered_carrier_date     TEXT,
    order_delivered_customer_date    TEXT,
    order_estimated_delivery_date    TEXT
);

-- ------------------------------------------------------------------------------
-- 3. Order Items
-- Source: olist_order_items_dataset.csv
-- ------------------------------------------------------------------------------
DROP TABLE IF EXISTS staging.order_items CASCADE;

CREATE TABLE staging.order_items (
    order_id               TEXT,
    order_item_id          TEXT,
    product_id             TEXT,
    seller_id              TEXT,
    shipping_limit_date    TEXT,
    price                  TEXT,
    freight_value          TEXT
);

-- ------------------------------------------------------------------------------
-- 4. Order Payments
-- Source: olist_order_payments_dataset.csv
-- ------------------------------------------------------------------------------
DROP TABLE IF EXISTS staging.order_payments CASCADE;

CREATE TABLE staging.order_payments (
    order_id                TEXT,
    payment_sequential      TEXT,
    payment_type            TEXT,
    payment_installments    TEXT,
    payment_value           TEXT
);

-- ------------------------------------------------------------------------------
-- 5. Order Reviews
-- Source: olist_order_reviews_dataset.csv
-- ------------------------------------------------------------------------------
DROP TABLE IF EXISTS staging.order_reviews CASCADE;

CREATE TABLE staging.order_reviews (
    review_id                  TEXT,
    order_id                   TEXT,
    review_score               TEXT,
    review_comment_title       TEXT,
    review_comment_message     TEXT,
    review_creation_date       TEXT,
    review_answer_timestamp    TEXT
);

-- ------------------------------------------------------------------------------
-- 6. Products
-- Source: olist_products_dataset.csv
-- ------------------------------------------------------------------------------
DROP TABLE IF EXISTS staging.products CASCADE;

CREATE TABLE staging.products (
    product_id                     TEXT,
    product_category_name          TEXT,
    product_name_lenght            TEXT,
    product_description_lenght     TEXT,
    product_photos_qty             TEXT,
    product_weight_g               TEXT,
    product_length_cm              TEXT,
    product_height_cm              TEXT,
    product_width_cm               TEXT
);

-- ------------------------------------------------------------------------------
-- 7. Sellers
-- Source: olist_sellers_dataset.csv
-- ------------------------------------------------------------------------------
DROP TABLE IF EXISTS staging.sellers CASCADE;

CREATE TABLE staging.sellers (
    seller_id                 TEXT,
    seller_zip_code_prefix    TEXT,
    seller_city               TEXT,
    seller_state              TEXT
);

-- ------------------------------------------------------------------------------
-- 8. Geolocation
-- Source: olist_geolocation_dataset.csv
-- ------------------------------------------------------------------------------
DROP TABLE IF EXISTS staging.geolocation CASCADE;

CREATE TABLE staging.geolocation (
    geolocation_zip_code_prefix    TEXT,
    geolocation_lat                TEXT,
    geolocation_lng                TEXT,
    geolocation_city               TEXT,
    geolocation_state              TEXT
);

-- ------------------------------------------------------------------------------
-- 9. Product Category Name Translation
-- Source: product_category_name_translation.csv
-- ------------------------------------------------------------------------------
DROP TABLE IF EXISTS staging.product_category_name_translation CASCADE;

CREATE TABLE staging.product_category_name_translation (
    product_category_name            TEXT,
    product_category_name_english    TEXT
);
