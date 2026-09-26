# Olist Data Warehouse — System Architecture

Tài liệu này mô tả chi tiết kiến trúc tổng thể của hệ thống Olist Brazilian E-Commerce Data Warehouse, làm rõ vai trò, ranh giới trách nhiệm giữa các tầng (layers) từ dữ liệu thô (raw data) đến tầng phân tích kinh doanh (analytics & reporting).

---

## 1. Tổng quan kiến trúc hệ thống (High-Level Architecture)

Hệ thống được thiết kế theo mô hình **ELT (Extract - Load - Transform)** kết hợp với nguyên lý **Kimball Dimensional Modeling (Star Schema)** trên hệ quản trị cơ sở dữ liệu **PostgreSQL**.

```text
+-------------------------------------------------------------------------------+
|                             1. DATA SOURCE LAYER                              |
|   9 Raw CSV Datasets (Kaggle Olist E-Commerce Brazilian Dataset)             |
|   - customers, orders, order_items, payments, reviews, products, sellers...    |
+-------------------------------------------------------------------------------+
                                        |
                                        | Extract & Load (scripts/load_staging.py - COPY)
                                        v
+-------------------------------------------------------------------------------+
|                            2. RAW STAGING LAYER                               |
|   PostgreSQL Schema: staging                                                  |
|   9 Tables (all columns TEXT): customers, orders, order_items, products...    |
|   - Bất biến (lossless), nạp an toàn, không rớt dòng do lỗi ép kiểu           |
+-------------------------------------------------------------------------------+
                                        |
                                        | SQL Transformation Views (sql/olist_staging_views.sql)
                                        v
+-------------------------------------------------------------------------------+
|                        3. TRANSFORMATION & VIEWS LAYER                        |
|   PostgreSQL Views: staging.vw_*                                              |
|   - Type casting (Timestamp, Numeric, Smallint)                               |
|   - String sanitization (TRIM, leading-zero preservation)                     |
|   - Deduplication (DISTINCT ON latest review)                                 |
|   - Pre-aggregation (Order-level payments, Translation fallback)              |
+-------------------------------------------------------------------------------+
                                        |
                                        | Transaction-Safe ETL Load (scripts/load_warehouse.py)
                                        v
+-------------------------------------------------------------------------------+
|                        4. DATA WAREHOUSE LAYER (DWH)                          |
|   PostgreSQL Schema: warehouse (Kimball Star Schema)                          |
|   - Dimensions: dim_customer, dim_date, dim_product, dim_seller               |
|   - Facts:      fact_sales (item grain), fact_order_fulfillment (order grain) |
|   - Surrogate Keys, Foreign Keys, Referential Integrity Constraints          |
+-------------------------------------------------------------------------------+
                                        |
                   +--------------------+--------------------+
                   |                                         |
                   v                                         v
+------------------------------------+   +------------------------------------+
|     5. DATA QUALITY & VALIDATION   |   |        6. ANALYTICS LAYER          |
|   scripts/validate_warehouse.py    |   |   analysis/sql/                    |
|   - 72 automated checks            |   |   analysis/notebooks/              |
|   - 7 test suites                  |   |   - Business Intelligence (BI)     |
|   - Anomaly reporting (CSV)        |   |   - Ad-hoc Queries                 |
+------------------------------------+   +------------------------------------+
                                                             |
                                                             v
                                         +------------------------------------+
                                         |      7. REPORTING & INSIGHTS       |
                                         |   analysis/reports/                |
                                         |   analysis/outputs/                |
                                         |   - Dashboards, Summaries, Slides  |
                                         +------------------------------------+
```

---

## 2. Trách nhiệm của từng tầng dữ liệu (Layer Responsibilities)

### 2.1. Tầng Nguồn (Source Data Layer)
- **Vị trí**: Thư mục `datasets/` (9 tệp CSV).
- **Đặc tính**: Dữ liệu thô thực tế từ sàn thương mại điện tử Olist tại Brazil (giai đoạn 2016 - 2018).
- **Nguyên tắc**: **Bất biến (Immutable)**. Tuyệt đối không chỉnh sửa, đổi tên hoặc xóa các tệp CSV gốc. Mọi sai sót hoặc dữ liệu nhiễu phải được xử lý ở các tầng sau.

### 2.2. Tầng Staging Thô (Raw Staging Layer)
- **Vị trí**: PostgreSQL schema `staging` (định nghĩa tại `sql/olist_staging.sql`).
- **Cơ chế nạp**: `scripts/load_staging.py` sử dụng lệnh `copy_expert` (COPY binary stream) của `psycopg2`.
- **Đặc tính**:
  - Mọi cột đều có kiểu dữ liệu `TEXT`.
  - Không đặt bất kỳ ràng buộc khóa chính (PK), khóa ngoại (FK), hay kiểm tra NOT NULL ở tầng này.
  - Mục tiêu là nạp 100% dữ liệu từ CSV vào database với tốc độ cao nhất mà không bị gián đoạn bởi lỗi cú pháp hay định dạng dữ liệu.

### 2.3. Tầng Chuyển đổi & Staging Views (Transformation Layer)
- **Vị trí**: PostgreSQL schema `staging` (các view `vw_*` định nghĩa tại `sql/olist_staging_views.sql`).
- **Trách nhiệm**:
  1. **Ép kiểu an toàn (Type Casting)**: Dùng `NULLIF(col, '')::TYPE` để chuyển chuỗi rỗng thành `NULL` trước khi ép sang `TIMESTAMP`, `NUMERIC`, `SMALLINT`, `INT`.
  2. **Chuẩn hóa chuỗi (String Cleansing)**: Dùng `TRIM()` loại bỏ khoảng trắng thừa ở hai đầu chuỗi cho mã định danh, tên thành phố, mã bang.
  3. **Bảo toàn định dạng (Formatting Preservation)**: Giữ nguyên `zip_code_prefix` dạng chuỗi (`TEXT`) để không bị mất số 0 ở đầu (ví dụ: mã bưu điện Brazil `01001`).
  4. **Bổ sung ngữ nghĩa**: Kết hợp bảng dịch danh mục sản phẩm (`product_category_name_translation`), fallback về tên gốc hoặc `'unknown'`.
  5. **Pre-aggregation ngăn ngừa nhân grain (Row Inflation Prevention)**:
     - `vw_order_payments_agg`: Gom nhóm tổng tiền thanh toán và số lượng giao dịch ở cấp `order_id`.
     - `vw_order_reviews_latest`: Sử dụng cú pháp `DISTINCT ON (order_id) ... ORDER BY order_id, review_creation_date DESC` để chọn review mới nhất cho mỗi đơn hàng.

### 2.4. Tầng Kho dữ liệu (Data Warehouse Layer)
- **Vị trí**: PostgreSQL schema `warehouse` (định nghĩa tại `sql/olist_dwh.sql`).
- **Mô hình**: Kimball Star Schema tối ưu hóa cho truy vấn phân tích OLAP.
- **Trách nhiệm**:
  - Quản lý Surrogate Keys (`*_key`) sinh tự động bằng `SERIAL` / `BIGSERIAL` / `INT`.
  - Quản lý khóa tự nhiên/nghiệp vụ (`*_id`) để liên kết truy vết với hệ thống nguồn.
  - Thiết lập ràng buộc toàn vẹn tham chiếu (Foreign Keys) giữa Fact và Dimension.
  - Đảm bảo tính toán đúng các thước đo kinh doanh (business measures) và SLA (durations tính theo giờ).
  - Tách biệt rõ ràng grain giữa các Fact (`fact_sales` ở cấp Order Item; `fact_order_fulfillment` ở cấp Order).

### 2.5. Tầng Kiểm định chất lượng dữ liệu (Data Quality & Auditing Layer)
- **Vị trí**: `scripts/validate_warehouse.py` và thư mục báo cáo `validation_reports/`.
- **Trách nhiệm**:
  - Chạy 72 automated checks sau khi nạp kho để kiểm tra Uniqueness, Not Null, Referential Integrity, Date Logic, Calendar Continuity, Business Rules, và Financial Reconciliation.
  - Tự động phát hiện bất thường (anomalies), xuất tệp CSV chứa danh sách bản ghi lỗi vào `validation_reports/` để phục vụ truy vết.

### 2.6. Tầng Phân tích dữ liệu (Analytics Layer)
- **Vị trí**: Thư mục `analysis/` (`sql/`, `notebooks/`, `outputs/`, `reports/`).
- **Trách nhiệm**:
  - Thực thi các câu lệnh SQL phân tích nghiệp vụ, tính toán KPI, phân khúc khách hàng (RFM), phân tích hiệu quả người bán, đánh giá SLA vận chuyển, v.v.
  - Xây dựng mô hình thống kê, trực quan hóa biểu đồ trên Jupyter Notebooks.

### 2.7. Tầng Báo cáo & Đóng gói Tri thức (Reporting & Insights Layer)
- **Vị trí**: `analysis/reports/` và `analysis/outputs/`.
- **Trách nhiệm**: Tổng hợp các kết quả phân tích thành báo cáo kinh doanh (Markdown, CSV, Chart PNG/SVG) phục vụ ra quyết định quản trị.

---

## 3. Phân tách ranh giới: Data Engineering vs. Data Analytics

Để đảm bảo tính toàn vẹn và độ tin cậy của toàn bộ dự án, ranh giới giữa hai khối công việc được quy định nghiêm ngặt như sau:

| Khía cạnh | Khối Kỹ thuật dữ liệu (Data Engineering) | Khối Phân tích dữ liệu (Data Analytics) |
| :--- | :--- | :--- |
| **Phạm vi tác động** | `datasets/`, `staging`, `sql/`, `scripts/`, `warehouse` DDL/ETL. | `analysis/`, `specs/analytics/`, đọc dữ liệu từ `warehouse`. |
| **Dữ liệu đầu vào** | CSV thô, staging tables, staging views. | **Chỉ truy vấn schema `warehouse`**. |
| **Quyền hạn DDL/DML** | `CREATE`, `DROP`, `TRUNCATE`, `INSERT` trên `staging` và `warehouse`. | **Chỉ dùng `SELECT`** trên schema `warehouse`. Tuyệt đối không `ALTER`, `UPDATE`, `DELETE`, `TRUNCATE`. |
| **Xử lý logic nghiệp vụ** | Chuẩn hóa, làm sạch, khử trùng lặp, duy trì star schema và grain. | Viết truy vấn nhóm (aggregation), lọc (filtering), phân tích cohort, tính toán tỷ lệ. |
| **Quy tắc cốt lõi** | Không được để lọt dữ liệu lỗi/mồ côi vào warehouse. | **Không bao giờ đọc trực tiếp CSV thô để tự làm sạch lại**. Không tự ý viết lại pipeline ETL khi làm phân tích. |

---

## 4. Luồng dữ liệu chi tiết (End-to-End Data Flow)

```text
[datasets/olist_*.csv]
         │
         │  (python scripts/load_staging.py)
         ▼
[staging.customers, orders, order_items, payments, reviews, products, sellers, geolocation, translation]
         │
         │  (sql/olist_staging_views.sql)
         ▼
[staging.vw_customers, vw_orders, vw_order_items, vw_products, vw_sellers, vw_order_payments_agg, vw_order_reviews_latest]
         │
         │  (python scripts/load_warehouse.py - In a single ACID Transaction)
         ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        warehouse Schema                                │
│                                                                        │
│   Dimensions:                                                          │
│     ├── dim_date      (Calendar generation 2016-2019)                  │
│     ├── dim_customer  (Deduped by customer_unique_id)                  │
│     ├── dim_product   (Category translation + dimension attributes)   │
│     └── dim_seller    (Location of sellers)                            │
│                                                                        │
│   Facts:                                                               │
│     ├── fact_sales             (Grain: 1 row / order_item)             │
│     └── fact_order_fulfillment (Grain: 1 row / order)                  │
└────────────────────────────────────────────────────────────────────────┘
         │
         │  (python scripts/validate_warehouse.py)
         ▼
[validation_reports/*.csv] (Passed 69/72 checks, 3 known source warnings)
         │
         ▼  (Analytics Ready)
[analysis/sql/*.sql, analysis/notebooks/*.ipynb]
         │
         ▼
[analysis/reports/*.md, analysis/outputs/*.csv, *.png]
```

---

## 5. Nguyên tắc vàng cho Analytics Agents

1. **Warehouse là nguồn chân lý duy nhất (Single Source of Truth)**: Mọi báo cáo phải dựa trên dữ liệu tại `warehouse.fact_*` và `warehouse.dim_*`.
2. **Không tái tạo bánh xe**: Các logic như tiền thanh toán gộp, review mới nhất, ngày giao trễ/đúng hạn đã được tính sẵn trong `warehouse.fact_order_fulfillment`. Hãy tận dụng thay vì join ngược về staging.
3. **Bất biến**: Không sửa đổi cấu trúc DWH trong pha phân tích dữ liệu trừ khi có yêu cầu bằng văn bản rõ ràng từ người dùng.
