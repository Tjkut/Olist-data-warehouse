# AGENTS.md — Central Context & Operating Guide for AI Agents

Tài liệu này là điểm chạm thông tin trung tâm (Main Context Entry Point) dành cho **AI Agents** khi làm việc trong repository Olist E-Commerce Data Warehouse. Tài liệu định nghĩa toàn bộ ngữ cảnh dự án, kiến trúc dữ liệu, các quy tắc truy vấn kho, quy trình làm việc chuẩn và bản đồ tài liệu chi tiết.

---

## 1. Tổng quan dự án (Project Overview)

- **Dự án**: Olist Brazilian E-Commerce Data Warehouse & Analytics.
- **Mục tiêu**: Xây dựng nền tảng Data Warehouse hoàn chỉnh theo phương pháp **Kimball Dimensional Modeling (Star Schema)** trên **PostgreSQL**, sau đó triển khai các bài toán **Data Analytics & BI** để khai phá tri thức kinh doanh từ bộ dữ liệu thương mại điện tử Olist (Brazil).
- **Trạng thái phát triển hiện tại**:
  - Tầng DWH và hạ tầng ETL (Ingestion, Transformation Views, Transaction-Safe Load, Data Quality Suite 72 checks) đã hoàn thiện và đạt trạng thái ổn định (Analytics-Ready).
  - Dự án đang bước vào giai đoạn trọng tâm tiếp theo: **Thực thi phân tích dữ liệu kinh doanh (Data Analytics Phase)**.

---

## 2. Giai đoạn hiện tại & Quy tắc bất biến (Current Phase Guardrails)

> [!IMPORTANT]
> **Hiện trạng**: Tầng DWH / ETL hiện tại là **nền móng dữ liệu vững chắc (Foundation)** đã được kiểm định chất lượng.
> **Nhiệm vụ tiếp theo**: Triển khai các bài toán phân tích kinh doanh (Analytics) dựa trên schema `warehouse`.
> **QUY TẮC CỐT LÕI**: Các AI Agent thực thi tác vụ phân tích (Analytics Agents) **TUYỆT ĐỐI KHÔNG ĐƯỢC PHÉP CHỈNH SỬA** cấu trúc DWH, logic ETL hoặc các bảng trong schema `warehouse` trừ khi có yêu cầu cụ thể, rõ ràng bằng văn bản từ người dùng.

---

## 3. Kiến trúc hệ thống & Luồng dữ liệu (Architecture & Flow)

Dữ liệu luân chuyển tuần tự qua các tầng được chuẩn hóa nghiêm ngặt:

```text
datasets/ (9 raw CSV files)
   │
   ▼  scripts/load_staging.py (psycopg2 copy_expert)
staging (Raw tables, all columns TEXT, lossless)
   │
   ▼  sql/olist_staging_views.sql (Type casting, cleaning, pre-aggregation)
transformation (staging.vw_* views)
   │
   ▼  scripts/load_warehouse.py (Transaction-safe full refresh)
data warehouse (warehouse schema: Kimball Star Schema)
   │
   ▼  analysis/sql/ & analysis/notebooks/ (Analytics & BI queries)
analytics
   │
   ▼  analysis/reports/ & analysis/outputs/
reports / insights (Business decisions, summaries, visual charts)
```

---

## 4. Công nghệ sử dụng (Technology Stack)

Toàn bộ dự án được xây dựng dựa trên các công nghệ thực tế có mặt trong repository:

- **Hệ quản trị cơ sở dữ liệu**: PostgreSQL (hỗ trợ các tính năng cao cấp: `DISTINCT ON`, `generate_series`, `NULLIF`, transaction ACID).
- **Ngôn ngữ lập trình**: Python 3.10+.
- **Thư viện kết nối DB**: `psycopg2-binary` (tận dụng `copy_expert` stream binary CSV nạp tốc độ cao).
- **Thư viện xử lý & kiểm định dữ liệu**: `pandas` (dùng trong validation reports và analytics).
- **Quản lý cấu hình môi trường**: `python-dotenv` (nạp biến từ `.env`).
- **Ngôn ngữ truy vấn**: PostgreSQL SQL (tối ưu hóa với CTE, Window Functions, Aggregate Filter).

---

## 5. Quy tắc truy vấn Kho dữ liệu (DWH Analytical Rules)

Khi thực hiện phân tích, mọi AI Agent bắt buộc phải tuân thủ các quy tắc sau:

1. **Truy vấn đúng nguồn**: Phân tích phải truy vấn từ schema `warehouse`, **tuyệt đối không đọc trực tiếp từ các tệp CSV thô** trong `datasets/`.
2. **Không bỏ qua DWH (No Bypass)**: Không tự ý kết nối vào schema `staging` để tự làm sạch dữ liệu nếu thông tin đó đã có sẵn trong `warehouse`.
3. **Xác định đúng bảng Fact**: Luôn xác định câu hỏi thuộc về nghiệp vụ bán hàng (`fact_sales`) hay vận hành/logistics (`fact_order_fulfillment`) trước khi viết SQL.
4. **Hiểu rõ Grain của Fact**:
   - `fact_sales`: Grain là **1 dòng cho mỗi order item (`order_id`, `order_item_id`)** — tổng cộng 112,650 dòng.
   - `fact_order_fulfillment`: Grain là **1 dòng cho mỗi order (`order_id`)** — tổng cộng 99,441 dòng.
5. **Không tổng hợp trước khi hiểu Grain**: Không bao giờ áp dụng hàm `SUM()` hay `AVG()` khi chưa nắm rõ mức độ chi tiết của các dòng đang được tính toán.
6. **Chống Join Multiplication (Nhân bản dữ liệu do Join)**: Tuyệt đối không join trực tiếp `fact_sales` và `fact_order_fulfillment` mà không gom nhóm (pre-aggregate) trước. Việc join bảng 1-nhiều mà không kiểm soát sẽ làm lạm phát doanh số và tiền thanh toán!
7. **Tránh tính trùng (Double Counting)**: Phân biệt rõ ràng giữa doanh thu sản phẩm trên từng item (`fact_sales.price`), tổng tiền thanh toán đơn hàng (`fact_order_fulfillment.total_payment_value`), và cước vận chuyển.
8. **Phân biệt rạch ròi các cấp độ thực thể**:
   - Order-level: `fact_order_fulfillment`.
   - Order-item-level: `fact_sales`.
   - Customer-level: `dim_customer` (gom nhóm theo `customer_unique_id`, không dùng `customer_id`).
   - Seller-level: `dim_seller`.
   - Product-level: `dim_product`.
9. **Định nghĩa Metric trước khi code**: Xác định rõ công thức toán học và đơn vị đo lường trước khi viết câu lệnh SQL.
10. **Kiểm chứng kết quả**: Luôn đối soát lại tổng số dòng (`COUNT`), giá trị tổng (`SUM`) sau khi chạy truy vấn để bảo đảm không bị mất dòng hoặc nhân đôi dòng.
11. **Không âm thầm thay đổi định nghĩa**: Giữ nguyên vẹn các định nghĩa nghiệp vụ đã được quy ước tại [docs/data_dictionary.md](file:///d:/Olist/docs/data_dictionary.md).
12. **Bất biến mã nguồn ETL/DWH**: Không chỉnh sửa mã nguồn nạp dữ liệu hoặc DDL trong suốt quá trình phân tích.

---

## 6. Quy trình làm việc chuẩn của AI Agent (AI Workflows)

### 6.1. Quy trình tổng quát (General Engineering Workflow)

Áp dụng khi được giao tác vụ nghiên cứu hoặc kỹ thuật dữ liệu:

```text
Research (Nghiên cứu yêu cầu & đọc tài liệu)
   ↓
Understand Context (Xác minh trạng thái code & schema thực tế)
   ↓
Plan (Lập kế hoạch các bước can thiệp rõ ràng)
   ↓
Implement (Thực thi code tối giản, phẫu thuật chính xác)
   ↓
Validate (Kiểm chứng bằng test suite / SQL checks)
   ↓
Review (Rà soát lại sự nhất quán toàn hệ thống)
   ↓
Report (Báo cáo kết quả rõ ràng, súc tích cho người dùng)
```

### 6.2. Quy trình phân tích dữ liệu chuẩn (Analytics Workflow)

Áp dụng khi triển khai bất kỳ câu hỏi phân tích kinh doanh nào:

```text
Business Question (Đọc và hiểu rõ bài toán kinh doanh)
   ↓
Identify Relevant Fact (Chọn fact_sales hay fact_order_fulfillment)
   ↓
Identify Grain (Xác định mức độ chi tiết của dòng)
   ↓
Identify Dimensions (Chọn các chiều cần join: date, customer, product, seller)
   ↓
Define Metric (Viết rõ công thức tính toán và đơn vị đo lường)
   ↓
Write SQL (Viết truy vấn rõ ràng, dùng CTE tại analysis/sql/)
   ↓
Validate (Đối soát số dòng, kiểm tra NULL, kiểm tra join multiplication)
   ↓
Analyze (Khai phá phân phối, xu hướng, vẽ biểu đồ tại analysis/notebooks/)
   ↓
Report (Tổng kết báo cáo kinh doanh tại analysis/reports/)
```

---

## 7. Bản đồ tài liệu chi tiết (Project Documentation Map)

Mọi thông tin chuyên sâu đã được phân rã thành các tài liệu chuyên biệt dưới đây:

### 7.1. Thư mục Kiến trúc & Kỹ thuật (`docs/`)

- [docs/architecture.md](file:///d:/Olist/docs/architecture.md): Kiến trúc hệ thống tổng thể, 7 tầng xử lý và ranh giới trách nhiệm giữa Data Engineering vs Analytics.
- [docs/dw_model.md](file:///d:/Olist/docs/dw_model.md): Chi tiết mô hình Kimball Star Schema, đặc tả 2 bảng Fact, 4 bảng Dimension, khóa ngoại và rủi ro Join.
- [docs/data_dictionary.md](file:///d:/Olist/docs/data_dictionary.md): Từ điển dữ liệu nghiệp vụ, định nghĩa từng cột, đơn vị đo lường và quy tắc tổng hợp measures.
- [docs/etl_pipeline.md](file:///d:/Olist/docs/etl_pipeline.md): Quy trình trích xuất, nạp staging, view chuyển đổi và nạp DWH trong single transaction an toàn.
- [docs/data_quality.md](file:///d:/Olist/docs/data_quality.md): Danh mục 72 automated checks, 7 nhóm kiểm thử và phân định IMPLEMENTED vs RECOMMENDED.
- [docs/analytics_guidelines.md](file:///d:/Olist/docs/analytics_guidelines.md): 12 nguyên tắc phân tích DWH và các mẫu template SQL chuẩn chống join multiplication.

### 7.2. Thư mục Đặc tả Phân tích (`specs/analytics/`)

- [specs/analytics/README.md](file:///d:/Olist/specs/analytics/README.md): Hướng dẫn quy trình Specification-First và chỉ mục các specs.
- [specs/analytics/001_sales_analysis.md](file:///d:/Olist/specs/analytics/001_sales_analysis.md): Đặc tả phân tích hiệu quả doanh thu và tính mùa vụ.
- [specs/analytics/002_customer_analysis.md](file:///d:/Olist/specs/analytics/002_customer_analysis.md): Đặc tả phân tích hành vi khách hàng, địa lý và phân khúc RFM.
- [specs/analytics/003_product_analysis.md](file:///d:/Olist/specs/analytics/003_product_analysis.md): Đặc tả phân tích danh mục sản phẩm, xếp hạng doanh số và đặc tính vật lý.
- [specs/analytics/004_seller_analysis.md](file:///d:/Olist/specs/analytics/004_seller_analysis.md): Đặc tả phân tích mạng lưới người bán, hiệu quả xuất kho và địa lý cung - cầu.
- [specs/analytics/005_delivery_analysis.md](file:///d:/Olist/specs/analytics/005_delivery_analysis.md): Đặc tả phân tích SLA logistics, tỷ lệ đúng hạn và tác động tới review CSAT.

### 7.3. Thư mục Thực thi & Kiểm thử

- `analysis/sql/`: Chứa các tệp SQL phân tích nghiệp vụ có khả năng tái lập.
- `analysis/notebooks/`: Chứa các Jupyter Notebooks dùng cho phân tích thăm dò và biểu đồ.
- `analysis/outputs/`: Chứa dữ liệu aggregate (.csv) và hình ảnh đồ thị (.png).
- `analysis/reports/`: Chứa báo cáo phân tích kinh doanh cuối cùng (.md).
- `tests/dwh_quality/`: Cơ chế kiểm thử chất lượng DWH và tích hợp CI/CD.
- [rules.md](file:///d:/Olist/rules.md): Quy tắc lập trình phẫu thuật và bảo vệ dữ liệu bắt buộc.
