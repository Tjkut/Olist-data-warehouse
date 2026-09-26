# Analytics Spec 002 — Customer Demographics & RFM Segmentation

## 1. Objective
Phân tích hành vi mua sắm của khách hàng Olist, đo lường tỷ lệ khách hàng mua lại (Repeat Purchase Rate), phân bổ địa lý khách hàng trên 27 bang của Brazil, và xây dựng mô hình phân khúc khách hàng RFM (Recency - Frequency - Monetary).

## 2. Business Questions
1. Có bao nhiêu khách hàng thực tế (`customer_unique_id`) đã từng mua hàng trên sàn?
2. Tỷ lệ khách hàng mua từ 2 lần trở lên là bao nhiêu? Olist là sàn giao dịch one-time mua sắm hay có mức độ giữ chân khách hàng (retention) cao?
3. Phân bổ địa lý của khách hàng tập trung chủ yếu ở những bang nào (ví dụ: khu vực Đông Nam Brazil như SP, RJ, MG so với phần còn lại)?
4. Phân khúc RFM chia tập khách hàng thành những nhóm nào (Champions, Loyal Customers, At Risk, Lost)?

## 3. Data Source
- Database: PostgreSQL
- Schema: `warehouse`

## 4. Relevant Fact Tables
- `warehouse.fact_order_fulfillment`: Cung cấp thông tin cấp đơn hàng (`order_id`, `total_payment_value`, `order_status`).
- `warehouse.fact_sales`: (Tùy chọn) Cung cấp danh mục sản phẩm mà từng khách hàng yêu thích.

## 5. Relevant Dimensions
- `warehouse.dim_customer`: Cung cấp `customer_unique_id`, `customer_city`, `customer_state`, `zip_code_prefix`.
- `warehouse.dim_date`: Cung cấp ngày đặt đơn qua `order_purchase_date_key`.

## 6. Fact Grain
- `fact_order_fulfillment`: **1 dòng cho mỗi đơn hàng (`order_id`)**.
- Rất thuận lợi cho bài toán tính RFM vì Recency và Monetary được tính trực tiếp ở cấp order mà không bị nhân đôi.

## 7. Metrics
- **Total Unique Customers** = `COUNT(DISTINCT c.customer_unique_id)`.
- **Total Orders per Customer (Frequency)** = `COUNT(DISTINCT f.order_id)`.
- **Total Monetary Value (Monetary)** = `SUM(f.total_payment_value)`.
- **Recency (Days)** = Số ngày tính từ đơn mua gần nhất của khách hàng tới mốc quan sát cuối cùng của tập dữ liệu: `MAX(d.full_date) - MAX(order_date)`.
- **Repeat Purchase Rate** = $\frac{\text{Số khách hàng có Frequency} \ge 2}{\text{Tổng số khách hàng thực tế}} \times 100\%$.
- **Average Customer Lifetime Value (CLV)** = `AVG(total_spent_per_customer)`.

## 8. Dimensions / Grouping
- Khách hàng: `customer_unique_id`.
- Địa lý: `customer_state`, `customer_city`.
- Phân khúc: Nhóm điểm RFM (1-5).

## 9. Expected Output
- Bảng tỷ lệ phân khúc RFM (Số lượng, Doanh thu đóng góp, % tổng doanh thu).
- Biểu đồ phân bố địa lý theo bang (Top 5 bang chiếm doanh số cao nhất).

## 10. Validation Requirements
- Số khách hàng duy nhất không được vượt quá 96,096 dòng (tổng số khách hàng trong `dim_customer`).
- Loại trừ các đơn hàng bị hủy (`order_status = 'canceled'`) khỏi tính toán chi tiêu tích lũy.

## 11. Potential Join Risks
- Phải nối qua `customer_key` từ `fact_order_fulfillment` sang `dim_customer`.
- Không nhầm lẫn giữa `customer_id` (mã giao dịch đơn lẻ) và `customer_unique_id` (mã định danh khách hàng thực tế).

## 12. Deliverables
- Tệp SQL: `analysis/sql/002_customer_rfm.sql`
- Notebook: `analysis/notebooks/002_customer_segmentation.ipynb`
- Báo cáo: `analysis/reports/002_customer_insights.md`
- Kết quả đầu ra: `analysis/outputs/customer_rfm_segments.csv`
