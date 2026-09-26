# Olist Brazilian E-Commerce Data Warehouse & Analytics

Giải pháp Kho dữ liệu (Data Warehouse) hoàn chỉnh cho bộ dữ liệu thương mại điện tử **Olist Brazilian E-Commerce**, được thiết kế theo nguyên lý **Kimball Dimensional Modeling (Star Schema)** trên nền tảng **PostgreSQL**. Pipeline bao gồm nạp dữ liệu thô (ELT), chuyển đổi chuẩn hóa qua SQL Views, nạp kho dữ liệu an toàn trong single database transaction, kiểm định chất lượng tự động với 72 automated checks, và khung phân tích kinh doanh (Business Intelligence & Analytics).

---

## 1. Trạng thái dự án (Project Status)

Dự án được phân chia thành 6 giai đoạn phát triển rõ ràng:

| Giai đoạn | Nội dung công việc | Trạng thái | Ghi chú kỹ thuật |
| :--- | :--- | :---: | :--- |
| **Phase 1 — Data Ingestion** | Trích xuất 9 tệp CSV nguồn và nạp vào staging | **COMPLETED** | Nạp an toàn bằng `copy_expert` nhị phân (`load_staging.py`). |
| **Phase 2 — Staging Schema** | Thiết kế bảng staging lưu trữ an toàn | **COMPLETED** | 100% cột là `TEXT`, không lo rớt dòng (`olist_staging.sql`). |
| **Phase 3 — Transformation** | Chuẩn hóa, ép kiểu, khử trùng lặp và pre-aggregation | **COMPLETED** | 7 SQL Views xử lý logic sạch sẽ (`olist_staging_views.sql`). |
| **Phase 4 — Data Warehouse** | Thiết kế Star Schema, khóa surrogate và nạp dữ liệu | **COMPLETED** | 4 Dimensions, 2 Facts nạp trong transaction (`load_warehouse.py`). |
| **Phase 5 — Data Quality** | Suite kiểm định tự động và sinh báo cáo anomaly | **COMPLETED** | 72 automated checks, 69 PASS, 3 warnings nguồn (`validate_warehouse.py`). |
| **Phase 6 — Data Analytics** | Triển khai SQL phân tích, Notebooks và Báo cáo BI | **NEXT** | Sẵn sàng thực thi dựa trên `specs/analytics/` và schema `warehouse`. |

---

## 2. Kiến trúc hệ thống & Luồng dữ liệu (Architecture)

```text
datasets/ (9 raw CSV files)
   │
   ▼  scripts/load_staging.py (Streaming binary COPY)
staging schema (All columns TEXT, raw & lossless)
   │
   ▼  sql/olist_staging_views.sql (Type casting, string sanitization, pre-aggregation)
staging views (staging.vw_* layer)
   │
   ▼  scripts/load_warehouse.py (Transaction-safe idempotent full refresh)
warehouse schema (Kimball Star Schema: 4 Dimensions + 2 Facts)
   │
   ▼  scripts/validate_warehouse.py (72 automated quality checks)
validation_reports/ (Anomaly audit reports)
   │
   ▼  analysis/sql/ & analysis/notebooks/ (Analytics Phase)
analysis/reports/ & analysis/outputs/ (Business insights & dashboards)
```

Chi tiết kiến trúc 7 tầng xem tại [docs/architecture.md](file:///d:/Olist/docs/architecture.md).

---

## 3. Cấu trúc thư mục (Repository Structure)

```text
Olist/
├── datasets/                         # 9 tệp CSV dữ liệu thô nguồn Olist (Bất biến)
├── image/                            # Hình ảnh kiến trúc và tài liệu minh họa
├── scripts/                          # Bộ mã nguồn vận hành Pipeline (Python)
│   ├── load_staging.py               # Nạp CSV vào staging schema
│   ├── load_warehouse.py             # Nạp Star Schema trong Database Transaction
│   └── validate_warehouse.py         # Suite 72 kiểm tra chất lượng dữ liệu & xuất anomaly
├── sql/                              # Toàn bộ mã nguồn DDL và Views (PostgreSQL)
│   ├── olist_staging.sql             # DDL tạo bảng staging schema (all TEXT)
│   ├── olist_staging_views.sql       # DDL staging views chuyển đổi dữ liệu
│   └── olist_dwh.sql                 # DDL warehouse star schema
├── validation_reports/               # Chứa các báo cáo CSV kiểm định chất lượng
│   ├── date_logic_approved_gt_carrier.csv
│   ├── date_logic_carrier_gt_delivered.csv
│   ├── reconciliation_sales_vs_payment_diff_gt_1pct.csv
│   └── warehouse_null_rates_overview.csv
│
├── docs/                             # Tài liệu kỹ thuật chi tiết của hệ thống
│   ├── architecture.md               # Kiến trúc hệ thống và phân tách ranh giới DE vs DA
│   ├── dw_model.md                   # Chi tiết Star Schema, Fact Grain và cảnh báo Join
│   ├── data_dictionary.md            # Từ điển dữ liệu nghiệp vụ và quy tắc tổng hợp metrics
│   ├── etl_pipeline.md               # Đặc tả quy trình ELT/ETL và tính an toàn giao dịch
│   ├── data_quality.md               # Danh mục 72 checks và phân định IMPLEMENTED vs RECOMMENDED
│   └── analytics_guidelines.md       # 12 nguyên tắc phân tích DWH và template SQL chuẩn
│
├── specs/                            # Đặc tả phân tích nghiệp vụ (Specification-First)
│   └── analytics/
│       ├── README.md                 # Quy trình phân tích và chỉ mục các bài toán
│       ├── 001_sales_analysis.md     # Đặc tả phân tích hiệu quả doanh thu & tính mùa vụ
│       ├── 002_customer_analysis.md  # Đặc tả phân tích hành vi khách hàng & mô hình RFM
│       ├── 003_product_analysis.md   # Đặc tả phân tích danh mục & catalog sản phẩm
│       ├── 004_seller_analysis.md    # Đặc tả phân tích mạng lưới người bán & cung cầu
│       └── 005_delivery_analysis.md  # Đặc tả phân tích SLA logistics & điểm CSAT review
│
├── analysis/                         # Không gian làm việc phân tích dữ liệu
│   ├── sql/                          # Tệp SQL phân tích nghiệp vụ có khả năng tái lập
│   ├── notebooks/                    # Jupyter Notebooks phân tích thăm dò & biểu đồ
│   ├── outputs/                      # Dữ liệu aggregate (.csv) và hình ảnh đồ thị (.png)
│   └── reports/                      # Báo cáo phân tích kinh doanh hoàn chỉnh (.md)
│
├── tests/                            # Kiểm thử chất lượng kho dữ liệu
│   └── dwh_quality/                  # Hướng dẫn kiểm thử chất lượng và tích hợp CI/CD
│
├── .env.example                      # Mẫu cấu hình kết nối PostgreSQL
├── .gitignore                        # Cấu hình git bỏ qua virtualenv, cache, file bí mật
├── AGENTS.md                         # Điểm chạm ngữ cảnh trung tâm cho AI Agent
├── README.md                         # Tài liệu này: Tổng quan dự án cho kỹ sư & người dùng
├── requirements.txt                  # Thư viện Python phụ thuộc
└── rules.md                          # Quy tắc lập trình phẫu thuật và bảo vệ dữ liệu
```

---

## 4. Mô hình Kho dữ liệu (Kimball Star Schema)

Mô hình gồm **4 bảng Dimension** và **2 bảng Fact** phục vụ hai khối nghiệp vụ phân tách rõ ràng:

### 4.1. Dimension Tables
- **`warehouse.dim_customer`** (96,096 dòng): Grain là 1 dòng / `customer_unique_id`. Đã được khử trùng lặp vị trí địa lý của khách hàng thực.
- **`warehouse.dim_date`** (1,461 dòng): Grain là 1 dòng / ngày lịch từ `2016-01-01` đến `2019-12-31`. Đầy đủ các thuộc tính lịch, tuần, cờ cuối tuần (`is_weekend`). Khóa `date_key` định dạng `YYYYMMDD`.
- **`warehouse.dim_product`** (32,951 dòng): Grain là 1 dòng / `product_id`. Cung cấp tên danh mục song ngữ tiếng Bồ Đào Nha và tiếng Anh (fallback `'unknown'`), cùng các thông số kích thước, khối lượng kiện hàng.
- **`warehouse.dim_seller`** (3,095 dòng): Grain là 1 dòng / `seller_id`. Cung cấp vị trí địa lý kho của đối tác người bán.

### 4.2. Fact Tables
- **`warehouse.fact_sales`** (112,650 dòng):
  - **Grain**: **Chính xác 1 dòng cho mỗi order item (`order_id`, `order_item_id`)**.
  - **Measures**: `price` (đơn giá món hàng), `freight_value` (phí vận chuyển phân bổ), `sales_amount` (`price + freight_value`).
  - **Trường hợp sử dụng**: Phân tích doanh số sản phẩm, doanh thu danh mục, hiệu quả bán hàng của người bán.
- **`warehouse.fact_order_fulfillment`** (99,441 dòng):
  - **Grain**: **Chính xác 1 dòng cho mỗi đơn hàng (`order_id`)**.
  - **Role-playing Dates**: Nối với `dim_date` qua 5 mốc: ngày đặt (`purchase`), ngày duyệt (`approved`), ngày xuất kho (`carrier`), ngày giao (`delivered`), ngày dự kiến (`estimated`).
  - **Measures**: Các chỉ số SLA tính theo giờ (`hours_to_approval`, `hours_to_carrier`, `hours_to_customer`, `total_fulfillment_hours`), độ lệch ngày so với cam kết (`days_vs_estimate`), điểm đánh giá (`review_score` từ 1-5), tổng tiền thanh toán đơn hàng (`total_payment_value`), số giao dịch thanh toán (`payment_count`).
  - **Trường hợp sử dụng**: Phân tích SLA chuỗi cung ứng, tỷ lệ giao hàng đúng hẹn, phân tích sự hài lòng của khách hàng (CSAT).

Chi tiết Data Model và cảnh báo Join Multiplication xem tại [docs/dw_model.md](file:///d:/Olist/docs/dw_model.md).

---

## 5. Cài đặt và Chạy Pipeline

### 5.1. Chuẩn bị môi trường
Yêu cầu: Python 3.10+, PostgreSQL 14+ và đã tạo database đích (`olist_db`).

```bash
# Cài đặt thư viện
pip install -r requirements.txt
```

Sao chép `.env.example` thành `.env` và cập nhật thông số kết nối:
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=olist_db
DB_USER=postgres
DB_PASSWORD=your_password
```

Khởi tạo cấu trúc bảng:
```bash
psql -U postgres -d olist_db -f sql/olist_staging.sql
psql -U postgres -d olist_db -f sql/olist_dwh.sql
```

### 5.2. Thứ tự thực thi Pipeline
Chạy tuần tự từ thư mục gốc của repository:

```bash
# Bước 1: Nạp raw CSV vào staging schema
python scripts/load_staging.py

# Bước 2: Tự động khởi tạo views và nạp warehouse trong 1 transaction an toàn
python scripts/load_warehouse.py

# Bước 3: Chạy bộ kiểm thử Data Quality toàn diện và sinh báo cáo anomaly
python scripts/validate_warehouse.py
```

---

## 6. Chất lượng dữ liệu (Data Quality & Validation)

Bộ kiểm định tự động gồm **72 automated checks** được phân loại thành 7 test suites:
- **69 checks PASS tuyệt đối**: Toàn bộ các kiểm tra Uniqueness, Not Null của khóa chính, Grain của Fact tables, Orphan Foreign Keys, công thức tính toán và tính liên tục của lịch thời gian đều đạt 100%.
- **3 checks WARNING (Known Source Anomalies)**: Do dữ liệu nguồn thô của Olist ghi nhận log có độ trễ hệ thống, đã được chuyển đổi an toàn thành `NULL` và lưu vết tại `validation_reports/`:
  1. `date_logic_approved_gt_carrier.csv`: Độ trễ log duyệt đơn so với lúc xuất kho.
  2. `date_logic_carrier_gt_delivered.csv`: Sự kiện quét kiện hàng ghi nhận sau khi giao ở 21 đơn hàng.
  3. `reconciliation_sales_vs_payment_diff_gt_1pct.csv`: Chênh lệch giữa giá niêm yết và tiền thanh toán do voucher/coupon sàn ở 255 đơn hàng.

Chi tiết xem tại [docs/data_quality.md](file:///d:/Olist/docs/data_quality.md).

---

## 7. Quy trình Phân tích dữ liệu (Analytics Workflow)

Khi bắt đầu một bài toán phân tích, lập trình viên và AI Agent phải tuân thủ quy trình **Specification-First**:
1. Tham khảo bản đặc tả bài toán tại `specs/analytics/*.md`.
2. Tuân thủ 12 nguyên tắc phân tích tại [docs/analytics_guidelines.md](file:///d:/Olist/docs/analytics_guidelines.md) (đặc biệt là nguyên tắc phòng chống Join Multiplication giữa `fact_sales` và `fact_order_fulfillment`).
3. Viết câu lệnh SQL có thể tái lập tại `analysis/sql/*.sql`.
4. Khai phá và trực quan hóa tại `analysis/notebooks/*.ipynb`.
5. Tổng hợp báo cáo kinh doanh tại `analysis/reports/*.md`.

---

## 8. Hướng dẫn dành cho AI Agent (Working with AI Agents)

Mọi AI Agent khi làm việc trong repository này cần đọc kỹ:
1. [AGENTS.md](file:///d:/Olist/AGENTS.md): Điểm chạm thông tin trung tâm, quy định về luồng làm việc và ranh giới quyền hạn.
2. [rules.md](file:///d:/Olist/rules.md): Quy tắc lập trình phẫu thuật (Surgical Changes) và quy tắc bảo vệ dữ liệu (chỉ dùng `SELECT` trong pha phân tích, không sửa đổi cấu trúc DWH).
