# Analytics Spec 005 — Delivery SLA, Logistics & Review Impact

## 1. Objective
Phân tích hiệu quả chuỗi cung ứng và vận hành giao hàng của Olist trên phạm vi toàn quốc gia Brazil, đo lường tỷ lệ giao hàng đúng hẹn (On-Time Delivery Rate), thời gian vận chuyển thực tế qua từng chặng, độ sai lệch so với ngày cam kết (`days_vs_estimate`), và chứng minh tác động trực tiếp của độ trễ giao hàng đến điểm hài lòng của khách hàng (`review_score`).

## 2. Business Questions
1. Tỷ lệ giao hàng đúng hẹn (On-time Delivery Rate) toàn sàn là bao nhiêu? Xu hướng qua các tháng có được cải thiện không?
2. Thời gian giao hàng trung bình từ lúc đặt đơn đến khi nhận hàng (`total_fulfillment_hours`) theo từng bang khách hàng là bao lâu?
3. Sự khác biệt giữa ngày giao dự kiến và ngày giao thực tế (`days_vs_estimate`) phân bổ như thế nào? Sàn thường hứa hẹn dư thừa thời gian (under-promise) hay thường xuyên giao trễ?
4. Mối tương quan định lượng giữa việc giao trễ hạn và điểm đánh giá review của khách hàng (CSAT) là gì? Đơn giao trễ bị giảm bao nhiêu điểm sao so với đơn đúng hẹn?

## 3. Data Source
- Database: PostgreSQL
- Schema: `warehouse`

## 4. Relevant Fact Tables
- `warehouse.fact_order_fulfillment`: Chứa toàn bộ các thước đo SLA, cờ đúng hạn và điểm review (`hours_to_approval`, `hours_to_carrier`, `hours_to_customer`, `total_fulfillment_hours`, `days_vs_estimate`, `is_on_time`, `review_score`, `order_status`).

## 5. Relevant Dimensions
- `warehouse.dim_customer`: Vị trí bang/thành phố nhận hàng (`customer_state`, `customer_city`).
- `warehouse.dim_date`: Trục thời gian qua 5 role-playing dates (chủ yếu là `order_purchase_date_key` và `delivered_date_key`).

## 6. Fact Grain
- **1 dòng cho mỗi order (`order_id`)**.
- Rất lý tưởng vì không cần xử lý nhân đôi dòng do order item.

## 7. Metrics
- **Total Delivered Orders** = `COUNT(*) FILTER (WHERE order_status = 'delivered')`.
- **On-time Orders** = `COUNT(*) FILTER (WHERE is_on_time = TRUE)`.
- **Delayed Orders** = `COUNT(*) FILTER (WHERE is_on_time = FALSE)`.
- **On-time Delivery Rate (%)** = `(On-time Orders / NULLIF(Total Delivered Orders, 0)) * 100`.
- **Average Lead Time (Days)** = `AVG(total_fulfillment_hours) / 24.0`.
- **Average Carrier Transit Time (Days)** = `AVG(hours_to_customer) / 24.0`.
- **Average Days vs Estimate** = `AVG(days_vs_estimate)`.
- **Average CSAT On-time** = `AVG(review_score) FILTER (WHERE is_on_time = TRUE)`.
- **Average CSAT Delayed** = `AVG(review_score) FILTER (WHERE is_on_time = FALSE)`.
- **CSAT Penalty for Delay** = `Average CSAT On-time - Average CSAT Delayed`.

## 8. Dimensions / Grouping
- Bang nhận hàng: `customer_state`.
- Thời gian đặt đơn: Tháng/Năm (`dim_date.year`, `dim_date.month`).
- Trạng thái giao hàng: Đúng hạn (`is_on_time = TRUE`) vs Trễ hạn (`is_on_time = FALSE`).

## 9. Expected Output
- Bảng SLA theo bang: `customer_state`, `delivered_orders`, `avg_lead_time_days`, `on_time_rate_pct`, `avg_review_score`.
- Bảng so sánh CSAT: Phân phối điểm sao (1 đến 5) giữa nhóm đơn đúng hẹn và nhóm đơn trễ hẹn.

## 10. Validation Requirements
- Chỉ tính toán trên các đơn hàng đã giao thành công (`order_status = 'delivered'` và `delivered_date_key IS NOT NULL`).
- Tỷ lệ đúng hẹn toàn sàn kỳ vọng nằm trong khoảng $90\% - 95\%$.

## 11. Potential Join Risks
- Lưu ý sử dụng đúng role-playing date: Khi phân tích xu hướng logistics theo thời gian cam kết/đặt hàng, dùng `order_purchase_date_key`. Khi phân tích năng lực tiếp nhận giao hàng theo tháng, dùng `delivered_date_key`.

## 12. Deliverables
- Tệp SQL: `analysis/sql/005_logistics_sla.sql`
- Notebook: `analysis/notebooks/005_delivery_sla_analysis.ipynb`
- Báo cáo: `analysis/reports/005_delivery_performance_report.md`
- Kết quả đầu ra: `analysis/outputs/delivery_sla_by_state.csv`
