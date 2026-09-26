# Analytics Specifications — Framework & Directory Index

Thư mục `specs/analytics/` chứa các bản đặc tả phân tích (Analytical Specifications) trước khi triển khai bất kỳ câu lệnh SQL hoặc mã phân tích nào trong thư mục `analysis/`.

---

## 1. Quy trình làm việc (Specification-First Workflow)

Để bảo đảm tính chính xác, nhất quán và ngăn ngừa các lỗi về grain / join multiplication, mọi tác vụ phân tích kinh doanh phải tuân thủ quy trình 6 bước:

```text
1. Đọc/Viết Spec (specs/analytics/*.md)
   ├── Làm rõ câu hỏi nghiệp vụ
   ├── Xác định đúng Fact, Dimension & Grain
   └── Định nghĩa chính xác công thức metric
                │
                ▼
2. Viết SQL phân tích (analysis/sql/*.sql)
   ├── Sử dụng CTE rõ ràng, có chú thích
   └── Validate số dòng và tổng tiền đối soát
                │
                ▼
3. Phân tích thăm dò & Trực quan hóa (analysis/notebooks/*.ipynb)
   ├── Trực quan hóa xu hướng, phân phối
   └── Xuất biểu đồ / bảng vào analysis/outputs/
                │
                ▼
4. Báo cáo tổng kết Insights (analysis/reports/*.md)
   └── Đúc kết câu trả lời nghiệp vụ và hàm ý quản trị
```

---

## 2. Danh mục các bản đặc tả (Analytics Specs Index)

| Mã Spec | Tên đặc tả | Trọng tâm phân tích | Fact Table chính |
| :--- | :--- | :--- | :--- |
| **[001](001_sales_analysis.md)** | **Sales Performance Analysis** | Doanh số, GMV, phí vận chuyển, tăng trưởng theo tháng/quý, mùa vụ e-commerce (Black Friday). | `fact_sales` |
| **[002](002_customer_analysis.md)** | **Customer & Cohort Analysis** | Phân khúc RFM, tần suất mua lặp lại (Repeat Purchase), CLV, vị trí địa lý khách hàng. | `fact_order_fulfillment`, `fact_sales` |
| **[003](003_product_analysis.md)** | **Product Category & Catalog Analysis** | Top danh mục bán chạy, hiệu quả doanh thu theo ngành hàng, thuộc tính vật lý kiện hàng. | `fact_sales` |
| **[004](004_seller_analysis.md)** | **Seller Performance & Geography** | Phân phối doanh thu người bán, độ trễ xuất kho, khoảng cách địa lý giữa seller và buyer. | `fact_sales`, `fact_order_fulfillment` |
| **[005](005_delivery_analysis.md)** | **Logistics, Delivery SLA & Review Impact** | Thời gian vận chuyển thực tế, tỷ lệ đúng hạn (On-time Rate), tác động của giao trễ lên CSAT Review. | `fact_order_fulfillment` |

---

## 3. Cấu trúc chuẩn của một tệp Spec
Mỗi tệp `specs/analytics/*.md` phải bao gồm đầy đủ 12 mục:
1. `# Objective`: Mục tiêu bài toán.
2. `# Business Questions`: Danh sách câu hỏi kinh doanh cần trả lời.
3. `# Data Source`: Bảng và schema dữ liệu sử dụng.
4. `# Relevant Fact Tables`: Tên bảng Fact.
5. `# Relevant Dimensions`: Tên các bảng Dimension.
6. `# Fact Grain`: Mức độ chi tiết của Fact.
7. `# Metrics`: Công thức và đơn vị tính toán.
8. `# Dimensions / Grouping`: Các trục phân tích / cắt lát.
9. `# Expected Output`: Định dạng bảng hoặc biểu đồ mong muốn.
10. `# Validation Requirements`: Tiêu chí kiểm chứng kết quả.
11. `# Potential Join Risks`: Các rủi ro join và giải pháp phòng tránh.
12. `# Deliverables`: Danh sách file mã nguồn SQL/Notebook/Báo cáo cần bàn giao.
