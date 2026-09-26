# Analytics Spec 001 — Sales Performance Analysis

## 1. Objective
Phân tích toàn diện hiệu quả kinh doanh của sàn thương mại điện tử Olist theo thời gian, đo lường tổng doanh số (GMV), phí vận chuyển, số lượng đơn hàng, giá trị trung bình đơn hàng (AOV), và nhận diện tính mùa vụ kinh doanh (ví dụ: cú hích doanh số mùa Black Friday 2017).

## 2. Business Questions
1. Tổng doanh thu (GMV), tổng phí vận chuyển và số lượng món hàng bán ra theo từng tháng/năm biến động như thế nào?
2. Tốc độ tăng trưởng doanh thu hàng tháng (MoM Growth Rate) và hàng năm (YoY) là bao nhiêu?
3. Tỷ trọng phí vận chuyển trên tổng doanh thu (`freight_ratio`) thay đổi ra sao qua các giai đoạn?
4. Đâu là những ngày/tuần đạt đỉnh doanh số cao nhất trong lịch sử hoạt động của sàn?

## 3. Data Source
- Database: PostgreSQL
- Schema: `warehouse`

## 4. Relevant Fact Tables
- `warehouse.fact_sales`: Cung cấp giá trị món hàng (`price`), cước vận chuyển (`freight_value`), và doanh số (`sales_amount`).

## 5. Relevant Dimensions
- `warehouse.dim_date`: Cung cấp trục thời gian chuẩn hóa (`year`, `quarter`, `month`, `month_name`, `full_date`, `is_weekend`).

## 6. Fact Grain
- **1 dòng cho mỗi order item (`order_id`, `order_item_id`)**.
- Lưu ý: Doanh số món hàng tính trực tiếp bằng `SUM(sales_amount)`. Khi đếm số đơn hàng, phải sử dụng `COUNT(DISTINCT order_id)`.

## 7. Metrics
- **Gross Merchandise Value (GMV)** = `SUM(price)` (BRL).
- **Total Freight Revenue** = `SUM(freight_value)` (BRL).
- **Total Sales Amount** = `SUM(sales_amount)` = `GMV + Total Freight Revenue` (BRL).
- **Total Items Sold** = `COUNT(*)` (Số lượng món hàng).
- **Total Orders** = `COUNT(DISTINCT order_id)` (Số đơn hàng phát sinh giao dịch).
- **Average Item Price** = `AVG(price)` (BRL).
- **Average Freight per Item** = `AVG(freight_value)` (BRL).
- **Freight to Price Ratio** = `(SUM(freight_value) / NULLIF(SUM(price), 0)) * 100` (%).

## 8. Dimensions / Grouping
- Thời gian: `year`, `quarter`, `month`, `full_date`.
- Cờ cuối tuần: `is_weekend`.

## 9. Expected Output
- Bảng tổng hợp theo tháng: `year`, `month`, `total_orders`, `total_items`, `gmv`, `freight`, `total_sales`, `mom_growth_pct`.
- Biểu đồ đường (Line chart) biểu diễn xu hướng doanh số theo tháng giai đoạn 2016-2018.

## 10. Validation Requirements
- Tổng doanh số cả giai đoạn phải khớp với tổng `fact_sales.sales_amount` toàn sàn ($\approx 15,860,000$ BRL).
- Không có tháng nào có doanh thu âm.
- Tỷ lệ tăng trưởng MoM của tháng đầu tiên (tháng 9/2016) nhận giá trị `NULL`.

## 11. Potential Join Risks
- Chỉ join giữa `fact_sales` và `dim_date` trên khóa `date_key`.
- Không join thêm `fact_order_fulfillment` ở cấp item để tránh nhân bản dữ liệu nếu chỉ phân tích doanh số bán hàng thuần túy.

## 12. Deliverables
- Tệp SQL: `analysis/sql/001_sales_performance.sql`
- Notebook: `analysis/notebooks/001_sales_performance.ipynb`
- Báo cáo: `analysis/reports/001_sales_performance_report.md`
- Kết quả đầu ra: `analysis/outputs/monthly_sales_trend.csv`
