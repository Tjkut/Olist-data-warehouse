-- Olist warehouse data-quality tests
-- Quy uoc:
-- failed_rows = 0: PASS
-- failed_rows > 0: FAIL

-- =========================================================
-- 1. KIEM TRA CAC BANG CO DU LIEU
-- =========================================================

SELECT
    'dim_date_empty' AS test_name,
    CASE WHEN COUNT(*) = 0 THEN 1 ELSE 0 END AS failed_rows
FROM warehouse.dim_date

UNION ALL

SELECT
    'dim_customer_empty',
    CASE WHEN COUNT(*) = 0 THEN 1 ELSE 0 END
FROM warehouse.dim_customer

UNION ALL

SELECT
    'dim_product_empty',
    CASE WHEN COUNT(*) = 0 THEN 1 ELSE 0 END
FROM warehouse.dim_product

UNION ALL

SELECT
    'dim_seller_empty',
    CASE WHEN COUNT(*) = 0 THEN 1 ELSE 0 END
FROM warehouse.dim_seller

UNION ALL

SELECT
    'fact_sales_empty',
    CASE WHEN COUNT(*) = 0 THEN 1 ELSE 0 END
FROM warehouse.fact_sales

UNION ALL

SELECT
    'fact_order_fulfillment_empty',
    CASE WHEN COUNT(*) = 0 THEN 1 ELSE 0 END
FROM warehouse.fact_order_fulfillment


-- =========================================================
-- 2. KIEM TRA TRUNG LAP
-- =========================================================

UNION ALL

SELECT
    'duplicate_dim_date_full_date',
    COUNT(*)
FROM (
    SELECT full_date
    FROM warehouse.dim_date
    GROUP BY full_date
    HAVING COUNT(*) > 1
) AS duplicate_rows

UNION ALL

SELECT
    'duplicate_customer_unique_id',
    COUNT(*)
FROM (
    SELECT customer_unique_id
    FROM warehouse.dim_customer
    GROUP BY customer_unique_id
    HAVING COUNT(*) > 1
) AS duplicate_rows

UNION ALL

SELECT
    'duplicate_product_id',
    COUNT(*)
FROM (
    SELECT product_id
    FROM warehouse.dim_product
    GROUP BY product_id
    HAVING COUNT(*) > 1
) AS duplicate_rows

UNION ALL

SELECT
    'duplicate_seller_id',
    COUNT(*)
FROM (
    SELECT seller_id
    FROM warehouse.dim_seller
    GROUP BY seller_id
    HAVING COUNT(*) > 1
) AS duplicate_rows

-- Grain cua fact_sales: 1 dong = 1 order item
UNION ALL

SELECT
    'duplicate_fact_sales_grain',
    COUNT(*)
FROM (
    SELECT
        order_id,
        order_item_id
    FROM warehouse.fact_sales
    GROUP BY
        order_id,
        order_item_id
    HAVING COUNT(*) > 1
) AS duplicate_rows

-- Grain cua fact_order_fulfillment: 1 dong = 1 don hang
UNION ALL

SELECT
    'duplicate_fulfillment_order_id',
    COUNT(*)
FROM (
    SELECT order_id
    FROM warehouse.fact_order_fulfillment
    GROUP BY order_id
    HAVING COUNT(*) > 1
) AS duplicate_rows


-- =========================================================
-- 3. KIEM TRA KHOA BAT BUOC BI NULL
-- =========================================================

UNION ALL

SELECT
    'fact_sales_null_business_key',
    COUNT(*)
FROM warehouse.fact_sales
WHERE order_id IS NULL
   OR order_item_id IS NULL

UNION ALL

SELECT
    'fulfillment_null_order_id',
    COUNT(*)
FROM warehouse.fact_order_fulfillment
WHERE order_id IS NULL


-- =========================================================
-- 4. KIEM TRA KHOA NGOAI CUA FACT_SALES
-- =========================================================

UNION ALL

SELECT
    'fact_sales_orphan_customer_key',
    COUNT(*)
FROM warehouse.fact_sales AS fs
LEFT JOIN warehouse.dim_customer AS dc
    ON fs.customer_key = dc.customer_key
WHERE fs.customer_key IS NOT NULL
  AND dc.customer_key IS NULL

UNION ALL

SELECT
    'fact_sales_orphan_product_key',
    COUNT(*)
FROM warehouse.fact_sales AS fs
LEFT JOIN warehouse.dim_product AS dp
    ON fs.product_key = dp.product_key
WHERE fs.product_key IS NOT NULL
  AND dp.product_key IS NULL

UNION ALL

SELECT
    'fact_sales_orphan_seller_key',
    COUNT(*)
FROM warehouse.fact_sales AS fs
LEFT JOIN warehouse.dim_seller AS ds
    ON fs.seller_key = ds.seller_key
WHERE fs.seller_key IS NOT NULL
  AND ds.seller_key IS NULL

UNION ALL

SELECT
    'fact_sales_orphan_date_key',
    COUNT(*)
FROM warehouse.fact_sales AS fs
LEFT JOIN warehouse.dim_date AS dd
    ON fs.date_key = dd.date_key
WHERE fs.date_key IS NOT NULL
  AND dd.date_key IS NULL


-- =========================================================
-- 5. KIEM TRA KHOA NGOAI CUA FACT_ORDER_FULFILLMENT
-- =========================================================

UNION ALL

SELECT
    'fulfillment_orphan_customer_key',
    COUNT(*)
FROM warehouse.fact_order_fulfillment AS fof
LEFT JOIN warehouse.dim_customer AS dc
    ON fof.customer_key = dc.customer_key
WHERE fof.customer_key IS NOT NULL
  AND dc.customer_key IS NULL

UNION ALL

SELECT
    'fulfillment_orphan_purchase_date_key',
    COUNT(*)
FROM warehouse.fact_order_fulfillment AS fof
LEFT JOIN warehouse.dim_date AS dd
    ON fof.order_purchase_date_key = dd.date_key
WHERE fof.order_purchase_date_key IS NOT NULL
  AND dd.date_key IS NULL

UNION ALL

SELECT
    'fulfillment_orphan_approved_date_key',
    COUNT(*)
FROM warehouse.fact_order_fulfillment AS fof
LEFT JOIN warehouse.dim_date AS dd
    ON fof.order_approved_date_key = dd.date_key
WHERE fof.order_approved_date_key IS NOT NULL
  AND dd.date_key IS NULL

UNION ALL

SELECT
    'fulfillment_orphan_carrier_date_key',
    COUNT(*)
FROM warehouse.fact_order_fulfillment AS fof
LEFT JOIN warehouse.dim_date AS dd
    ON fof.carrier_pickup_date_key = dd.date_key
WHERE fof.carrier_pickup_date_key IS NOT NULL
  AND dd.date_key IS NULL

UNION ALL

SELECT
    'fulfillment_orphan_delivered_date_key',
    COUNT(*)
FROM warehouse.fact_order_fulfillment AS fof
LEFT JOIN warehouse.dim_date AS dd
    ON fof.delivered_date_key = dd.date_key
WHERE fof.delivered_date_key IS NOT NULL
  AND dd.date_key IS NULL

UNION ALL

SELECT
    'fulfillment_orphan_estimated_date_key',
    COUNT(*)
FROM warehouse.fact_order_fulfillment AS fof
LEFT JOIN warehouse.dim_date AS dd
    ON fof.estimated_delivery_date_key = dd.date_key
WHERE fof.estimated_delivery_date_key IS NOT NULL
  AND dd.date_key IS NULL


-- =========================================================
-- 6. KIEM TRA CAC GIA TRI DO LUONG
-- =========================================================

-- sales_amount phai bang price + freight_value
UNION ALL

SELECT
    'invalid_sales_amount',
    COUNT(*)
FROM warehouse.fact_sales
WHERE sales_amount IS DISTINCT FROM
      ROUND(
          COALESCE(price, 0) + COALESCE(freight_value, 0),
          2
      )

-- Tien khong duoc am
UNION ALL

SELECT
    'negative_sales_values',
    COUNT(*)
FROM warehouse.fact_sales
WHERE price < 0
   OR freight_value < 0
   OR sales_amount < 0

-- Thoi gian xu ly va van chuyen khong duoc am
UNION ALL

SELECT
    'negative_fulfillment_hours',
    COUNT(*)
FROM warehouse.fact_order_fulfillment
WHERE hours_to_approval < 0
   OR hours_to_carrier < 0
   OR hours_to_customer < 0
   OR total_fulfillment_hours < 0

-- Diem danh gia chi duoc nam tu 1 den 5
UNION ALL

SELECT
    'invalid_review_score',
    COUNT(*)
FROM warehouse.fact_order_fulfillment
WHERE review_score IS NOT NULL
  AND review_score NOT BETWEEN 1 AND 5

-- Gia tri thanh toan va so lan thanh toan khong duoc am
UNION ALL

SELECT
    'negative_payment_values',
    COUNT(*)
FROM warehouse.fact_order_fulfillment
WHERE total_payment_value < 0
   OR payment_count < 0

ORDER BY test_name;
