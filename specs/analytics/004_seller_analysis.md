# Analytics Spec 004 — Seller Performance & Logistics Efficiency

## 1. Objective
Phân tích mạng lưới đối tác người bán (merchants / sellers), đo lường sự phân bổ doanh thu giữa các nhóm người bán, vị trí địa lý của kho người bán, tốc độ chuẩn bị và xuất kho hàng hóa (`hours_to_carrier`), và phát hiện sự mất cân đối cung - cầu theo vùng miền.

## 2. Business Questions
1. Có bao nhiêu người bán hoạt động tích cực trên sàn? Mức độ tập trung doanh thu ở top người bán (Power Sellers) ra sao?
2. Các bang nào là "thủ phủ" của người bán (ví dụ: São Paulo chiếm bao nhiêu % số lượng seller)?
3. Tốc độ bàn giao hàng cho bưu tá (`hours_to_carrier`) trung bình của người bán theo từng bang là bao lâu?
4. Đơn hàng giao nội bang (cùng bang người bán và khách mua) có thời gian và chi phí khác biệt như thế nào so với đơn liên bang (khác bang)?

## 3. Data Source
- Database: PostgreSQL
- Schema: `warehouse`

## 4. Relevant Fact Tables
- `warehouse.fact_sales`: Cung cấp doanh thu và số lượng item của người bán (`seller_key`, `sales_amount`, `freight_value`).
- `warehouse.fact_order_fulfillment`: Cung cấp thời gian chuẩn bị hàng (`hours_to_carrier`) và điểm đánh giá (`review_score`).

## 5. Relevant Dimensions
- `warehouse.dim_seller`: Cung cấp `seller_id`, `seller_city`, `seller_state`, `zip_code_prefix`.
- `warehouse.dim_customer`: Cung cấp `customer_state` để so sánh vị trí người bán và khách mua.

## 6. Fact Grain
- `fact_sales`: 1 dòng / order item (đo lường doanh số của seller).
- `fact_order_fulfillment`: 1 dòng / order (đo lường thời gian xuất kho).

## 7. Metrics
- **Seller Total GMV** = `SUM(s.price)`.
- **Seller Total Orders** = `COUNT(DISTINCT s.order_id)`.
- **Seller Total Items Sold** = `COUNT(*)`.
- **Average Dispatch Time (Hours)** = `AVG(f.hours_to_carrier)`.
- **Average Dispatch Time (Days)** = `AVG(f.hours_to_carrier) / 24.0`.
- **Same-State Order Rate** = $\frac{\text{Số đơn cùng bang (seller\_state = customer\_state)}}{\text{Tổng số đơn}} \times 100\%$.
- **Average Seller CSAT** = `AVG(f.review_score)`.

## 8. Dimensions / Grouping
- Người bán: `seller_id`, `seller_state`, `seller_city`.
- Địa lý: Phân loại giao hàng nội bang (`Intra-state`) vs liên bang (`Inter-state`).

## 9. Expected Output
- Bảng phân bố người bán theo bang: `seller_state`, `active_sellers`, `total_gmv`, `avg_dispatch_hours`.
- Biểu đồ phân loại Sellers theo phân khúc doanh thu (Tier 1: > 100k BRL, Tier 2: 20k-100k BRL, Tier 3: < 20k BRL).

## 10. Validation Requirements
- Tổng số người bán phân tích không vượt quá 3,095 người bán trong `dim_seller`.
- Loại trừ các giá trị `NULL` trong `hours_to_carrier` khi tính thời gian xuất kho trung bình.

## 11. Potential Join Risks
- Một đơn hàng có thể chứa các món hàng từ **nhiều người bán khác nhau** (multi-seller order).
- Khi tính thời gian xuất kho cho seller, cần cẩn trọng vì `fact_order_fulfillment` ghi nhận mốc `hours_to_carrier` ở cấp toàn đơn hàng.

## 12. Deliverables
- Tệp SQL: `analysis/sql/004_seller_efficiency.sql`
- Notebook: `analysis/notebooks/004_seller_performance.ipynb`
- Báo cáo: `analysis/reports/004_seller_insights.md`
- Kết quả đầu ra: `analysis/outputs/seller_performance_summary.csv`
