# Olist Data Warehouse — ETL Pipeline Specification

Tài liệu này ghi lại chi tiết quy trình Trích xuất, Chuyển đổi và Nạp dữ liệu (ETL / ELT) của dự án Olist E-Commerce, dựa trên mã nguồn thực tế tại `scripts/` và `sql/`.

---

## 1. Tổng quan quy trình xử lý dữ liệu (Pipeline Stages)

Quy trình ETL được thiết kế theo tư duy **Idempotent Full Refresh** với cơ chế bảo vệ giao dịch (ACID Transaction Safety), gồm 4 giai đoạn nối tiếp:

```text
[datasets/*.csv]
       │
       ▼  Giai đoạn 1: Staging Ingestion (scripts/load_staging.py)
[staging tables (All TEXT)]
       │
       ▼  Giai đoạn 2: Transformation via SQL Views (sql/olist_staging_views.sql)
[staging.vw_* views]
       │
       ▼  Giai đoạn 3: Warehouse Loading in Single Transaction (scripts/load_warehouse.py)
[warehouse schema (Star Schema)]
       │
       ▼  Giai đoạn 4: Data Quality Auditing (scripts/validate_warehouse.py)
[validation_reports/*.csv]
```

---

## 2. Giai đoạn 1: Trích xuất & Nạp thô vào Staging (Staging Ingestion)

### 2.1. Nguồn dữ liệu (Source Datasets)
Thư mục `datasets/` chứa 9 tệp CSV nguồn:
1. `olist_customers_dataset.csv` $\rightarrow$ `staging.customers`
2. `olist_orders_dataset.csv` $\rightarrow$ `staging.orders`
3. `olist_order_items_dataset.csv` $\rightarrow$ `staging.order_items`
4. `olist_order_payments_dataset.csv` $\rightarrow$ `staging.order_payments`
5. `olist_order_reviews_dataset.csv` $\rightarrow$ `staging.order_reviews`
6. `olist_products_dataset.csv` $\rightarrow$ `staging.products`
7. `olist_sellers_dataset.csv` $\rightarrow$ `staging.sellers`
8. `olist_geolocation_dataset.csv` $\rightarrow$ `staging.geolocation`
9. `product_category_name_translation.csv` $\rightarrow$ `staging.product_category_name_translation`

### 2.2. Script điều phối: `scripts/load_staging.py`
- **Cơ chế nạp**:
  1. Đọc và thực thi `sql/olist_staging.sql` để tạo schema `staging` và 9 bảng đích.
  2. Mọi cột trong bảng staging đều được định nghĩa là `TEXT`. Điều này loại bỏ hoàn toàn nguy cơ rớt dòng do lỗi parsing ngày tháng hoặc số thực khi nạp ban đầu.
  3. Mở tệp CSV dưới dạng nhị phân với encoding UTF-8.
  4. Thực thi lệnh `cursor.copy_expert()`:
     ```sql
     COPY <staging_table> FROM STDIN WITH (FORMAT CSV, HEADER TRUE, ENCODING 'UTF8');
     ```
  5. Tối ưu tốc độ: Phương pháp streaming nhị phân của PostgreSQL cho phép nạp hàng trăm ngàn bản ghi chỉ trong vài giây.
- **Tính Idempotent**: Mỗi lần chạy `load_staging.py`, các bảng staging cũ đều được `DROP TABLE IF EXISTS ... CASCADE` và tạo mới hoàn toàn trước khi nạp.

---

## 3. Giai đoạn 2: Tầng Chuyển đổi qua SQL Views (Transformation Layer)

Tệp định nghĩa: `sql/olist_staging_views.sql`.
Được tự động triệu gọi bởi hàm `ensure_staging_views()` trong `scripts/load_warehouse.py`.

### 3.1. Ép kiểu an toàn (Safe Type Casting)
- Sử dụng hàm `NULLIF(column, '')` trước khi ép kiểu:
  - Timestamp: `NULLIF(order_purchase_timestamp, '')::TIMESTAMP`
  - Tiền tệ & Đo lường: `NULLIF(price, '')::NUMERIC(12,2)`
  - Số nguyên: `NULLIF(order_item_id, '')::SMALLINT`
- Đảm bảo các chuỗi rỗng `""` không gây lỗi ép kiểu (data type cast exception).

### 3.2. Làm sạch chuỗi (String Sanitization)
- `TRIM()` loại bỏ khoảng trắng ở hai đầu của `customer_city`, `seller_city`, `customer_state`, `seller_state`.
- Giữ nguyên tiền tố mã bưu điện `zip_code_prefix` dạng chuỗi để không làm mất các số 0 ở đầu (ví dụ: `01001` không bị biến thành số nguyên `1001`).

### 3.3. Xử lý đa ngôn ngữ & Bổ khuyết (Enrichment)
- `staging.vw_products` thực hiện `LEFT JOIN` với `staging.product_category_name_translation` để lấy tên danh mục tiếng Anh.
- Sử dụng `COALESCE(category_name_english, category_name, 'unknown')` đảm bảo không bị `NULL` ở tên danh mục tiếng Anh.

### 3.4. Pre-aggregation ngăn ngừa nhân grain (Grain Inflation Prevention)
1. **`staging.vw_order_payments_agg`**:
   - Nhóm theo `order_id` để tính tổng tiền thanh toán `SUM(payment_value)` và đếm số lượt thanh toán `COUNT(*)`.
   - Kết quả: Đưa dữ liệu thanh toán về đúng grain **1 dòng / order_id** trước khi đưa vào bảng `fact_order_fulfillment`.
2. **`staging.vw_order_reviews_latest`**:
   - Sử dụng cú pháp đặc thù tối ưu của PostgreSQL:
     ```sql
     SELECT DISTINCT ON (order_id) order_id, review_score
     FROM staging.order_reviews
     WHERE review_score IS NOT NULL AND TRIM(review_score) != ''
     ORDER BY order_id, review_creation_date DESC;
     ```
   - Chọn ra điểm đánh giá mới nhất cho mỗi đơn hàng, loại bỏ trùng lặp khi khách hàng gửi nhiều review cho một đơn.

---

## 4. Giai đoạn 3: Nạp Kho dữ liệu an toàn (Warehouse Loading)

Script điều phối: `scripts/load_warehouse.py`.

### 4.1. Cơ chế Transaction-Safe Full Refresh
Toàn bộ quá trình nạp kho được thực thi trong **một Database Transaction duy nhất**:
```python
conn = get_connection()
conn.autocommit = False  # Bật chế độ transaction
```
- Nếu bất kỳ bước nào gặp lỗi ngoại lệ hoặc kiểm tra validation nội bộ phát hiện sai sót, hệ thống sẽ lập tức gọi `conn.rollback()`.
- Kho dữ liệu cũ chỉ bị ghi đè sau khi có lệnh `conn.commit()` ở cuối quy trình.

### 4.2. Thứ tự nạp dữ liệu chi tiết
1. **Bước 0 — Tạo staging views**: Triệu gọi `ensure_staging_views(cursor)` áp dụng `sql/olist_staging_views.sql`.
2. **Bước 1 — Xóa dữ liệu cũ (Truncate)**:
   - Xóa bảng Fact trước: `fact_order_fulfillment`, `fact_sales`.
   - Xóa bảng Dimension sau: `dim_seller`, `dim_product`, `dim_customer`, `dim_date`.
   - Dùng lệnh `CASCADE` để tôn trọng ràng buộc khóa ngoại.
3. **Bước 2 — Nạp Dimension Tables**:
   - `load_dim_date()`: Sinh dữ liệu lịch tự động từ `2016-01-01` đến `2019-12-31` bằng `generate_series`. Không phụ thuộc vào staging.
   - `load_dim_customer()`: Nạp từ `staging.vw_customers`. Khử trùng lặp bằng `ROW_NUMBER() OVER (PARTITION BY customer_unique_id ORDER BY COUNT(*) DESC, city, state, zip)` để chọn vị trí cư trú ổn định nhất của khách hàng.
   - `load_dim_product()`: Nạp từ `staging.vw_products`. Sinh surrogate key `product_key`.
   - `load_dim_seller()`: Nạp từ `staging.vw_sellers`. Sinh surrogate key `seller_key`.
4. **Bước 3 — Nạp Fact Tables**:
   - `load_fact_sales()`: Nạp từ `staging.vw_order_items`, join sang `vw_orders`, `vw_customers`, và các bảng dimension để resolve các surrogate keys (`customer_key`, `product_key`, `seller_key`, `date_key`). Dùng `LEFT JOIN` để tránh làm rớt dòng ngầm định.
   - `load_fact_order_fulfillment()`: Nạp từ `staging.vw_orders`, join sang `vw_customers`, `dim_customer`, 5 role-playing `dim_date`, cùng 2 view pre-aggregated (`vw_order_reviews_latest`, `vw_order_payments_agg`). Tính toán các metric SLA durations (bảo đảm không nhận giá trị âm phi lý).
5. **Bước 4 — Pre-commit Validation**:
   - Kiểm tra row count khác 0 trên toàn bộ các bảng.
   - Kiểm tra Uniqueness của Primary Keys.
   - Nếu có lỗi: Rollback ngay lập tức. Nếu pass: Commit transaction.

---

## 5. Giai đoạn 4: Kiểm định chất lượng dữ liệu (Data Quality Suite)

Script điều phối: `scripts/validate_warehouse.py`.

- Chạy độc lập sau khi nạp kho hoàn tất.
- Thực thi 72 automated checks và sinh báo cáo chi tiết ra thư mục `validation_reports/`.
- Chi tiết xem tại `docs/data_quality.md`.

---

## 6. Sổ tay hướng dẫn thực thi (Execution Runbook)

Chạy tuần tự các lệnh sau từ thư mục gốc của repository:

```bash
# 1. Kích hoạt môi trường và cài đặt dependencies
pip install -r requirements.txt

# 2. Khởi tạo schema DDL (chỉ cần chạy lần đầu)
psql -U postgres -d olist_db -f sql/olist_staging.sql
psql -U postgres -d olist_db -f sql/olist_dwh.sql

# 3. Bước 1: Nạp raw staging từ CSV
python scripts/load_staging.py

# 4. Bước 2: Nạp warehouse trong transaction an toàn
python scripts/load_warehouse.py

# 5. Bước 3: Chạy bộ kiểm thử Data Quality toàn diện
python scripts/validate_warehouse.py
```
