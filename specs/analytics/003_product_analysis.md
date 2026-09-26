# Analytics Spec 003 — Product Category & Catalog Performance

## 1. Objective
Đánh giá hiệu quả kinh doanh của các danh mục sản phẩm (Category Performance), nhận diện các nhóm hàng bán chạy (Top Sellers) và nhóm hàng đóng góp doanh thu lớn nhất (Pareto 80/20), đồng thời phân tích mối tương quan giữa đặc tính vật lý sản phẩm (kích thước, cân nặng, số ảnh) với doanh số và phí vận chuyển.

## 2. Business Questions
1. Top 10 danh mục sản phẩm có doanh thu cao nhất và số lượng bán ra nhiều nhất là gì?
2. Có hiện tượng Pareto (20% danh mục tạo ra 80% doanh thu) trên sàn Olist hay không?
3. Các danh mục nào có phí vận chuyển trung bình cao nhất? Khối lượng (`product_weight_g`) tác động như thế nào tới chi phí vận chuyển?
4. Số lượng ảnh (`product_photos_qty`) hoặc độ dài mô tả sản phẩm có tương quan thuận với số lượng bán ra không?

## 3. Data Source
- Database: PostgreSQL
- Schema: `warehouse`

## 4. Relevant Fact Tables
- `warehouse.fact_sales`: Lưu thông tin chi tiết từng món hàng bán ra (`product_key`, `price`, `freight_value`, `sales_amount`).

## 5. Relevant Dimensions
- `warehouse.dim_product`: Cung cấp danh mục song ngữ (`category_name`, `category_name_english`) và các thuộc tính vật lý (`product_weight_g`, `product_photos_qty`, kích thước kiện hàng).
- `warehouse.dim_date`: Lọc hoặc gom nhóm theo giai đoạn thời gian.

## 6. Fact Grain
- **1 dòng cho mỗi order item (`order_id`, `order_item_id`)**.
- Rất phù hợp vì mỗi dòng bán hàng gắn trực tiếp với chính xác 1 `product_key`.

## 7. Metrics
- **Category GMV** = `SUM(price)` (BRL).
- **Category Total Sales** = `SUM(sales_amount)` (BRL).
- **Category Volume** = `COUNT(*)` (Số lượng sản phẩm bán ra).
- **Average Price per Product** = `AVG(price)` (BRL).
- **Average Freight per Product** = `AVG(freight_value)` (BRL).
- **Freight-to-Price Percentage** = `(SUM(freight_value) / NULLIF(SUM(price), 0)) * 100` (%).
- **Cumulative Revenue Percentage** = Tính bằng hàm cửa sổ `SUM(sales) OVER (...) / SUM(sales) OVER ()` để kiểm chứng Pareto.

## 8. Dimensions / Grouping
- Danh mục sản phẩm: `category_name_english` (hoặc `category_name`).
- Đặc tính sản phẩm: Các khoảng cân nặng (`< 1kg`, `1-5kg`, `> 5kg`), số lượng ảnh (1 ảnh, 2-4 ảnh, 5+ ảnh).

## 9. Expected Output
- Bảng xếp hạng Top 15 Categories: `rank`, `category_name_english`, `items_sold`, `total_revenue`, `avg_price`, `freight_ratio`.
- Biểu đồ phân tán (Scatter plot) giữa Khối lượng sản phẩm và Phí vận chuyển.

## 10. Validation Requirements
- Tổng số item phân bổ qua các danh mục phải bằng 112,650 dòng (hoặc tập con tương ứng sau khi lọc).
- Xử lý giá trị `'unknown'` cho các sản phẩm không có thông tin danh mục.

## 11. Potential Join Risks
- Nối `fact_sales` với `dim_product` qua `product_key`.
- Không join thêm `fact_order_fulfillment` nếu không cần dữ liệu review/payment, tránh làm phức tạp câu truy vấn.

## 12. Deliverables
- Tệp SQL: `analysis/sql/003_product_performance.sql`
- Notebook: `analysis/notebooks/003_product_catalog_analysis.ipynb`
- Báo cáo: `analysis/reports/003_product_category_insights.md`
- Kết quả đầu ra: `analysis/outputs/top_categories_summary.csv`
