-- Olist Staging Views — Data Quality Tests
-- Quy ước:
-- failed_rows = 0: PASS
-- failed_rows > 0: FAIL

SELECT
    'vw_customers_empty' AS test_name,
    CASE WHEN COUNT(*) = 0 THEN 1 ELSE 0 END AS failed_rows
FROM staging.vw_customers

UNION ALL

SELECT
    'vw_orders_empty',
    CASE WHEN COUNT(*) = 0 THEN 1 ELSE 0 END
FROM staging.vw_orders

UNION ALL

SELECT
    'orders_null_order_id',
    COUNT(*)
FROM staging.vw_orders
WHERE order_id IS NULL

UNION ALL

SELECT
    'duplicate_orders',
    COUNT(*)
FROM (
    SELECT order_id
    FROM staging.vw_orders
    GROUP BY order_id
    HAVING COUNT(*) > 1
) AS duplicate_rows

UNION ALL

SELECT
    'duplicate_order_items',
    COUNT(*)
FROM (
    SELECT order_id, order_item_id
    FROM staging.vw_order_items
    GROUP BY order_id, order_item_id
    HAVING COUNT(*) > 1
) AS duplicate_rows

ORDER BY test_name;
