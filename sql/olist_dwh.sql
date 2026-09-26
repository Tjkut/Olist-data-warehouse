-- ==============================================================================
-- Olist E-Commerce Data Pipeline - Warehouse Schema (PostgreSQL)
-- Strategy: Star Schema with 2 Fact Tables + 4 Dimension Tables
-- Grain:
--   fact_sales             -> 1 row per order_item  (sales measures)
--   fact_order_fulfillment -> 1 row per order       (logistics, payment, review)
-- Key Convention:
--   Surrogate Keys: xxx_key  (e.g. customer_key, product_key)
--   Business Keys:  *_id     (e.g. customer_id, product_id)
-- ==============================================================================

CREATE SCHEMA IF NOT EXISTS warehouse;

-- ==============================================================================
-- DIMENSION TABLES
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- dim_date
-- Grain: 1 row per calendar day
-- date_key format: YYYYMMDD (e.g. 20180105)
-- ------------------------------------------------------------------------------
DROP TABLE IF EXISTS warehouse.dim_date CASCADE;

CREATE TABLE warehouse.dim_date (
    date_key        INT PRIMARY KEY,          -- YYYYMMDD
    full_date       DATE        NOT NULL,
    year            SMALLINT    NOT NULL,
    quarter         SMALLINT    NOT NULL,
    month           SMALLINT    NOT NULL,
    month_name      VARCHAR(9)  NOT NULL,
    week_of_year    SMALLINT    NOT NULL,
    day_of_month    SMALLINT    NOT NULL,
    day_of_week     SMALLINT    NOT NULL,     -- 1=Sun ... 7=Sat
    day_name        VARCHAR(9)  NOT NULL,
    is_weekend      BOOLEAN     NOT NULL
);

-- ------------------------------------------------------------------------------
-- dim_customer
-- Grain: 1 row per customer_unique_id
-- ------------------------------------------------------------------------------
DROP TABLE IF EXISTS warehouse.dim_customer CASCADE;

CREATE TABLE warehouse.dim_customer (
    customer_key        SERIAL PRIMARY KEY,
    customer_unique_id  TEXT    NOT NULL UNIQUE,
    customer_city       TEXT,
    customer_state      CHAR(2),
    zip_code_prefix     CHAR(5)
);

-- ------------------------------------------------------------------------------
-- dim_product
-- Grain: 1 row per product_id
-- category_name_english falls back to Portuguese name, then 'unknown'
-- ------------------------------------------------------------------------------
DROP TABLE IF EXISTS warehouse.dim_product CASCADE;

CREATE TABLE warehouse.dim_product (
    product_key                 SERIAL PRIMARY KEY,
    product_id                  TEXT    NOT NULL UNIQUE,
    category_name               TEXT,
    category_name_english       TEXT,
    product_name_length         INT,
    product_description_length  INT,
    product_photos_qty          INT,
    product_weight_g            NUMERIC(10,2),
    product_length_cm           NUMERIC(8,2),
    product_height_cm           NUMERIC(8,2),
    product_width_cm            NUMERIC(8,2)
);

-- ------------------------------------------------------------------------------
-- dim_seller
-- Grain: 1 row per seller_id
-- ------------------------------------------------------------------------------
DROP TABLE IF EXISTS warehouse.dim_seller CASCADE;

CREATE TABLE warehouse.dim_seller (
    seller_key          SERIAL PRIMARY KEY,
    seller_id           TEXT    NOT NULL UNIQUE,
    seller_city         TEXT,
    seller_state        CHAR(2),
    zip_code_prefix     CHAR(5)
);

-- ==============================================================================
-- FACT TABLES
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- fact_sales
-- Grain: 1 row per order_item (order_id, order_item_id)
-- Measures: price, freight_value, sales_amount
-- ------------------------------------------------------------------------------
DROP TABLE IF EXISTS warehouse.fact_sales CASCADE;

CREATE TABLE warehouse.fact_sales (
    sales_key               BIGSERIAL PRIMARY KEY,
    order_id                TEXT        NOT NULL,
    order_item_id           SMALLINT    NOT NULL,
    customer_key            INT         REFERENCES warehouse.dim_customer(customer_key),
    product_key             INT         REFERENCES warehouse.dim_product(product_key),
    seller_key              INT         REFERENCES warehouse.dim_seller(seller_key),
    date_key                INT         REFERENCES warehouse.dim_date(date_key),
    price                   NUMERIC(12,2),
    freight_value           NUMERIC(12,2),
    sales_amount            NUMERIC(12,2),    -- price + freight_value
    UNIQUE(order_id, order_item_id)
);

-- ------------------------------------------------------------------------------
-- fact_order_fulfillment
-- Grain: 1 row per order
-- Measures: fulfillment durations (hours), days_vs_estimate, review_score,
--           total_payment_value, payment_count
-- Duration rules: NULL when timestamps are out of sequence (no negatives).
-- ------------------------------------------------------------------------------
DROP TABLE IF EXISTS warehouse.fact_order_fulfillment CASCADE;

CREATE TABLE warehouse.fact_order_fulfillment (
    fulfillment_key             BIGSERIAL PRIMARY KEY,
    order_id                    TEXT    NOT NULL UNIQUE,
    customer_key                INT     REFERENCES warehouse.dim_customer(customer_key),
    order_purchase_date_key     INT     REFERENCES warehouse.dim_date(date_key),
    order_approved_date_key     INT     REFERENCES warehouse.dim_date(date_key),
    carrier_pickup_date_key     INT     REFERENCES warehouse.dim_date(date_key),
    delivered_date_key          INT     REFERENCES warehouse.dim_date(date_key),
    estimated_delivery_date_key INT     REFERENCES warehouse.dim_date(date_key),
    hours_to_approval           NUMERIC(8,2),
    hours_to_carrier            NUMERIC(8,2),
    hours_to_customer           NUMERIC(8,2),
    total_fulfillment_hours     NUMERIC(8,2),
    days_vs_estimate            NUMERIC(8,2),
    review_score                SMALLINT,
    order_status                TEXT,
    is_on_time                  BOOLEAN,
    total_payment_value         NUMERIC(12,2),
    payment_count               SMALLINT
);
