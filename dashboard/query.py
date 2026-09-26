TOTAL_PRODUCT_REVENUE_QUERY = """
SELECT
    ROUND(
        COALESCE(SUM(sales_amount), 0),
        2
    ) AS total_revenue
FROM warehouse.fact_sales;
"""
MONTHLY_REVENUE_QUERY = """
WITH calendar_months AS (
    SELECT
        generate_series(
            DATE '2016-01-01',
            DATE '2018-12-01',
            INTERVAL '1 month'
        )::date AS month_start
),

monthly_revenue AS (
    SELECT
        DATE_TRUNC('month', d.full_date)::date AS month_start,
        SUM(fs.sales_amount) AS total_revenue
    FROM warehouse.fact_sales AS fs
    JOIN warehouse.dim_date AS d
        ON fs.date_key = d.date_key
    WHERE fs.sales_amount IS NOT NULL
    GROUP BY
        DATE_TRUNC('month', d.full_date)::date
)

SELECT
    cm.month_start,
    TO_CHAR(cm.month_start, 'YYYY-MM') AS year_month,
    ROUND(
        COALESCE(mr.total_revenue, 0),
        2
    ) AS total_revenue
FROM calendar_months AS cm
LEFT JOIN monthly_revenue AS mr
    ON cm.month_start = mr.month_start
ORDER BY
    cm.month_start;
"""
TOTAL_ORDERS_QUERY = """
SELECT
    COUNT(DISTINCT order_id) AS total_orders
FROM warehouse.fact_order_fulfillment;
"""
DELIVERD_ORDER= """ 
SELECT
    COUNT(*) AS total_orders,
    COUNT(*) FILTER (WHERE order_status = 'delivered') AS delivered_orders,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE order_status = 'delivered') / COUNT(*),
        2
    ) AS delivery_success_rate_pct
FROM warehouse.fact_order_fulfillment;
"""
TOTAL_ORDERS_BY_DATE_OF_HOURS="""
SELECT
    d.day_of_week,
    d.day_name,
    COUNT(DISTINCT fs.order_id) AS total_orders
FROM warehouse.dim_date AS d
LEFT JOIN warehouse.fact_sales AS fs
    ON d.date_key = fs.date_key
GROUP BY
    d.day_of_week,
    d.day_name
ORDER BY
    CASE
        WHEN d.day_of_week = 1 THEN 8
        ELSE d.day_of_week
    END;
    """
TOP10_CATEGORY_REVENUE_QUERY = """
SELECT
    p.category_name_english AS category,
    ROUND(
        COALESCE(SUM(fs.sales_amount), 0),
        2
    ) AS total_revenue
FROM warehouse.dim_product p
JOIN warehouse.fact_sales fs ON fs.product_key = p.product_key
GROUP BY p.category_name_english
ORDER BY SUM(fs.sales_amount) DESC
LIMIT 10;
"""

TOP_CATEGORY_PERFORMANCE_QUERY = """
SELECT
    p.category_name_english AS category,
    ROUND(
        COALESCE(SUM(fs.sales_amount), 0),
        2
    ) AS total_revenue,
    COUNT(fs.order_item_id) AS total_quantity
FROM warehouse.dim_product p
JOIN warehouse.fact_sales fs ON fs.product_key = p.product_key
WHERE p.category_name_english IS NOT NULL
GROUP BY p.category_name_english;
"""


AVERAGE_PRICE_BY_CATEGORY_QUERY = """
SELECT
    p.category_name_english AS category,
    ROUND(
        AVG(fs.price),
        2
    ) AS avg_price
FROM warehouse.dim_product p
JOIN warehouse.fact_sales fs ON fs.product_key = p.product_key
WHERE p.category_name_english IS NOT NULL
GROUP BY p.category_name_english
ORDER BY avg_price DESC;
"""

TOTAL_CUSTOMERS_QUERY = """
SELECT
    COUNT(DISTINCT customer_unique_id) AS total_customers
FROM warehouse.dim_customer;
"""

CUSTOMERS_BY_STATE_QUERY = """
SELECT
    customer_state AS state,
    COUNT(DISTINCT customer_unique_id) AS total_customers
FROM warehouse.dim_customer
WHERE customer_state IS NOT NULL
GROUP BY customer_state
ORDER BY total_customers DESC;
"""

CUSTOMERS_BY_CITY_QUERY = """
SELECT
    INITCAP(customer_city) AS city,
    customer_state AS state,
    COUNT(DISTINCT customer_unique_id) AS total_customers
FROM warehouse.dim_customer
WHERE customer_city IS NOT NULL
GROUP BY customer_city, customer_state
ORDER BY total_customers DESC;
"""

REPEAT_CUSTOMERS_QUERY = """
SELECT
  COUNT(DISTINCT customer_unique_id) FILTER (WHERE order_count = 1) AS one_time_customers,
  COUNT(DISTINCT customer_unique_id) FILTER (WHERE order_count > 1) AS repeat_customers
FROM (
  SELECT dc.customer_unique_id, COUNT(DISTINCT f.order_id) AS order_count
  FROM warehouse.fact_order_fulfillment f
  JOIN warehouse.dim_customer dc ON f.customer_key = dc.customer_key
  GROUP BY dc.customer_unique_id
) t;
"""

AVG_REVIEW_SCORE_QUERY = """
SELECT
    ROUND(AVG(review_score)::numeric, 2) AS avg_review_score
FROM warehouse.fact_order_fulfillment;
"""

ON_TIME_DELIVERY_RATE_QUERY = """
WITH on_time AS (
    SELECT
        COUNT(*) AS cnt
    FROM warehouse.fact_order_fulfillment
    WHERE is_on_time = true
),

total AS (
    SELECT
        COUNT(*) AS cnt
    FROM warehouse.fact_order_fulfillment
)

SELECT
    ROUND((100.0 * o.cnt / t.cnt), 2) AS on_time_rate_pct
FROM on_time AS o,
     total AS t;
"""

DELIVERY_TIME_VS_REVIEW_QUERY = """
SELECT
    CASE WHEN is_on_time THEN 'On Time' ELSE 'Late' END AS delivery_status,
    ROUND(total_fulfillment_hours / 24.0) AS delivery_day,
    ROUND(AVG(review_score)::numeric, 2) AS avg_review_score,
    COUNT(*) AS order_count
FROM warehouse.fact_order_fulfillment
WHERE review_score IS NOT NULL 
  AND total_fulfillment_hours IS NOT NULL
  AND total_fulfillment_hours / 24.0 >= 0
  AND total_fulfillment_hours / 24.0 <= 80
GROUP BY 1, 2
ORDER BY delivery_day;
"""

AVG_DELIVERY_TIME_BY_STATE_QUERY = """
SELECT
    c.customer_state,
    ROUND(AVG(f.hours_to_customer) / 24, 2) AS avg_delivery_days,
    COUNT(*) AS delivered_orders
FROM warehouse.fact_order_fulfillment AS f
JOIN warehouse.dim_customer AS c
    ON f.customer_key = c.customer_key
WHERE f.order_status = 'delivered'
  AND f.hours_to_customer IS NOT NULL
GROUP BY c.customer_state
ORDER BY avg_delivery_days DESC;
"""

AVG_DELIVERY_DAYS_BY_STATE_QUERY = AVG_DELIVERY_TIME_BY_STATE_QUERY










