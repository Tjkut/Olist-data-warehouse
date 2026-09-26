# Olist Data Warehouse — Analytics Guidelines & Best Practices

Tài liệu này là bộ quy chuẩn hướng dẫn (Guidelines) dành cho **AI Agents** và **Data Analysts** khi thực hiện phân tích dữ liệu trên Olist Data Warehouse. Việc tuân thủ nghiêm ngặt 12 nguyên tắc dưới đây giúp ngăn ngừa các lỗi phân tích kinh điển (sai grain, join multiplication, double counting, lệch định nghĩa chỉ số).

---

## 1. Mười hai Nguyên tắc Phân tích DWH (The 12 Analytical Rules)

### Rule 1 — Start from the business question (Bắt đầu từ câu hỏi kinh doanh)
- Trước khi viết bất kỳ dòng SQL nào, hãy phát biểu rõ ràng câu hỏi nghiệp vụ và mục tiêu đầu ra.
- Ví dụ: *"Tỷ lệ giao hàng đúng hạn của từng bang trong năm 2017 là bao nhiêu?"* hoặc *"Top 10 danh mục sản phẩm có tổng doanh số cao nhất là gì?"*.

### Rule 2 — Identify the correct fact table (Xác định đúng bảng Fact)
- **Doanh số, sản phẩm, người bán**: Dùng `warehouse.fact_sales`.
- **Logistics, SLA, trạng thái giao hàng, CSAT review, thanh toán đơn hàng**: Dùng `warehouse.fact_order_fulfillment`.
- Tuyệt đối không chọn bừa bảng Fact. Nếu câu hỏi liên quan đến cả hai khía cạnh, xem kỹ **Rule 6**.

### Rule 3 — Identify fact grain (Xác định rõ mức độ chi tiết của Fact)
- `fact_sales` có grain là **1 dòng cho mỗi order item**. Tổng số dòng là 112,650.
- `fact_order_fulfillment` có grain là **1 dòng cho mỗi order**. Tổng số dòng là 99,441.
- Hiểu grain giúp bạn chọn đúng phép toán tổng hợp và tránh nhầm lẫn giữa "doanh thu trên mỗi sản phẩm" và "giá trị đơn hàng".

### Rule 4 — Identify required dimensions (Xác định các chiều phân tích cần thiết)
- Chỉ join với các Dimension thực sự cần dùng cho việc cắt lát (slice & dice), nhóm dữ liệu (`GROUP BY`) hoặc lọc (`WHERE`).
- Tận dụng `order_id` (degenerate dimension) sẵn có trong Fact nếu chỉ cần đếm số đơn hàng (`COUNT(DISTINCT order_id)`).

### Rule 5 — Define metrics before SQL (Định nghĩa công thức chỉ số trước khi viết code)
- Luôn nêu rõ công thức toán học và đơn vị đo lường:
  - **AOV (Average Order Value)** = $\frac{\sum \text{total\_payment\_value}}{\text{Tổng số đơn hàng}}$ (tính trên `fact_order_fulfillment`).
  - **On-time Delivery Rate** = $\frac{\text{COUNT(*) FILTER (WHERE is\_on\_time = TRUE)}}{\text{COUNT(*) FILTER (WHERE order\_status = 'delivered')}} \times 100\%$.

### Rule 6 — Prevent join multiplication (Chống hiện tượng nhân đôi dữ liệu do Join)
- **CẤM KỴ**: Viết lệnh `FROM fact_sales s JOIN fact_order_fulfillment f ON s.order_id = f.order_id` rồi thực hiện `SUM(f.total_payment_value)`. Với đơn hàng có 3 món, số tiền thanh toán sẽ bị nhân 3 lần!
- **Giải pháp**: Phải tổng hợp một bảng về cùng grain trước khi thực hiện join (dùng CTE hoặc Subquery).

### Rule 7 — Validate row counts (Kiểm tra số dòng trước và sau khi query)
- Kiểm tra tính hợp lý của tập kết quả:
  - Số đơn hàng trong phân tích không bao giờ được vượt quá 99,441.
  - Số item không bao giờ được vượt quá 112,650.
  - Sau khi `LEFT JOIN` với Dimension, số dòng của Fact không được tăng lên (nếu tăng nghĩa là Dimension bị trùng lặp key).

### Rule 8 — Validate NULLs (Kiểm soát và xử lý giá trị NULL)
- Khi tính các chỉ số SLA: Lưu ý các đơn hàng bị hủy hoặc chưa giao sẽ có `delivered_date_key IS NULL` và các cột `hours_*` là `NULL`. Phải dùng điều kiện lọc rõ ràng (ví dụ: `WHERE order_status = 'delivered'`).
- Khi tính tỷ lệ: Tránh lỗi chia cho 0 bằng hàm `NULLIF(denominator, 0)`.

### Rule 9 — Validate duplicates (Kiểm soát trùng lặp)
- Khi tính toán số lượng khách hàng thực: Phải dùng `COUNT(DISTINCT c.customer_unique_id)`, không dùng `COUNT(c.customer_key)` vì cùng một khách hàng có thể mua nhiều lần và liên kết với các đơn khác nhau.

### Rule 10 — Cross-check important metrics (Đối soát chéo các chỉ số cốt lõi)
- Sau khi viết query tính tổng doanh thu: Đối chiếu với tổng doanh số toàn sàn trên `fact_sales` ($\approx 15.86$ triệu BRL) để bảo đảm không bị lệch do join sai hoặc filter thiếu.

### Rule 11 — Keep analytical SQL reproducible (Đảm bảo tính tái lập và tường minh)
- Đặt bí danh cột rõ ràng bằng tiếng Anh hoặc tiếng Việt chuẩn.
- Sử dụng CTE (`WITH ... AS`) để phân tách các bước logic thay vì lồng ghép quá nhiều tầng subquery phức tạp.
- Lưu lại các file truy vấn quan trọng vào thư mục `analysis/sql/`.

### Rule 12 — Never modify DWH definitions silently (Tuyệt đối không tự ý sửa DWH)
- Nhà phân tích chỉ có quyền đọc (`SELECT`). Không bao giờ tự ý chạy `UPDATE`, `ALTER`, `DROP` trên các bảng warehouse. Nếu phát hiện thiếu sót dữ liệu, hãy ghi chú vào tài liệu đề xuất.

---

## 2. Các mẫu truy vấn chuẩn (Best Practice SQL Templates)

### Template 1: Xu hướng Doanh thu & Cước vận chuyển theo tháng (Monthly Trend)
Sử dụng `fact_sales` nối với `dim_date`:

```sql
-- Thống kê doanh thu sản phẩm, phí vận chuyển và số món hàng theo từng tháng
SELECT 
    d.year,
    d.month,
    d.month_name,
    COUNT(DISTINCT s.order_id)           AS total_orders,
    COUNT(*)                             AS total_items_sold,
    SUM(s.price)                         AS total_product_revenue,
    SUM(s.freight_value)                 AS total_freight_value,
    SUM(s.sales_amount)                  AS total_sales_amount,
    ROUND(AVG(s.price), 2)               AS avg_item_price
FROM warehouse.fact_sales s
JOIN warehouse.dim_date d 
  ON s.date_key = d.date_key
GROUP BY d.year, d.month, d.month_name
ORDER BY d.year, d.month;
```

---

### Template 2: Phân tích SLA Giao hàng & CSAT Review theo Bang khách hàng
Sử dụng `fact_order_fulfillment` nối với `dim_customer`:

```sql
-- Đánh giá chất lượng dịch vụ giao hàng và điểm đánh giá theo từng bang
SELECT 
    c.customer_state,
    COUNT(*)                                                         AS total_delivered_orders,
    ROUND(AVG(f.total_fulfillment_hours), 1)                         AS avg_lead_time_hours,
    ROUND(AVG(f.total_fulfillment_hours / 24.0), 1)                  AS avg_lead_time_days,
    ROUND(AVG(f.days_vs_estimate), 1)                                AS avg_days_vs_estimate,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE f.is_on_time = TRUE) / NULLIF(COUNT(*), 0), 
        2
    )                                                                AS on_time_delivery_rate_pct,
    ROUND(AVG(f.review_score), 2)                                   AS avg_review_score
FROM warehouse.fact_order_fulfillment f
JOIN warehouse.dim_customer c 
  ON f.customer_key = c.customer_key
WHERE f.order_status = 'delivered'
  AND f.delivered_date_key IS NOT NULL
GROUP BY c.customer_state
HAVING COUNT(*) >= 100
ORDER BY avg_lead_time_days ASC;
```

---

### Template 3: Phân tích Khách hàng Trung thành (Customer Lifetime Value - CLV)
Nhóm theo `customer_unique_id`:

```sql
-- Phân loại khách hàng theo số lần mua hàng và tổng chi tiêu
WITH customer_orders AS (
    SELECT 
        c.customer_unique_id,
        c.customer_state,
        COUNT(DISTINCT f.order_id)   AS order_frequency,
        SUM(f.total_payment_value)   AS total_spent,
        MIN(d.full_date)             AS first_purchase_date,
        MAX(d.full_date)             AS latest_purchase_date
    FROM warehouse.fact_order_fulfillment f
    JOIN warehouse.dim_customer c 
      ON f.customer_key = c.customer_key
    JOIN warehouse.dim_date d 
      ON f.order_purchase_date_key = d.date_key
    WHERE f.order_status NOT IN ('canceled', 'unavailable')
    GROUP BY c.customer_unique_id, c.customer_state
)
SELECT 
    CASE 
        WHEN order_frequency = 1 THEN '1. One-time Buyer'
        WHEN order_frequency = 2 THEN '2. Repeat Buyer (2 orders)'
        ELSE '3. Loyal Buyer (3+ orders)'
    END AS customer_segment,
    COUNT(*)                             AS customer_count,
    ROUND(AVG(total_spent), 2)           AS avg_spending_per_customer,
    SUM(total_spent)                     AS total_revenue_contribution
FROM customer_orders
GROUP BY 1
ORDER BY 1;
```

---

### Template 4: Mẫu kết hợp an toàn giữa Fact Sales và Fact Fulfillment (Safe Multi-Fact Join)
Khi cần liên kết dữ liệu món hàng với dữ liệu thanh toán đơn hàng:

```sql
-- Tính tỷ lệ đóng góp của từng danh mục sản phẩm vào các đơn hàng giao thành công
WITH order_item_summary AS (
    SELECT 
        s.order_id,
        dp.category_name_english,
        SUM(s.sales_amount) AS category_sales
    FROM warehouse.fact_sales s
    JOIN warehouse.dim_product dp 
      ON s.product_key = dp.product_key
    GROUP BY s.order_id, dp.category_name_english
)
SELECT 
    ois.category_name_english,
    COUNT(DISTINCT f.order_id)           AS order_count,
    SUM(ois.category_sales)              AS total_sales,
    ROUND(AVG(f.review_score), 2)        AS avg_order_review_score
FROM warehouse.fact_order_fulfillment f
JOIN order_item_summary ois 
  ON f.order_id = ois.order_id
WHERE f.order_status = 'delivered'
GROUP BY ois.category_name_english
ORDER BY total_sales DESC
LIMIT 20;
```
