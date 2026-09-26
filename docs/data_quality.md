# Olist Data Warehouse — Data Quality & Validation Framework

Tài liệu này ghi nhận hiện trạng kiểm định chất lượng dữ liệu (Data Quality Framework) của dự án, đối chiếu trực tiếp từ bộ mã nguồn `scripts/validate_warehouse.py` và các báo cáo anomaly tại `validation_reports/`.

---

## 1. Tổng quan bộ kiểm định (Overview)

Hệ thống sở hữu bộ kiểm định tự động gồm **72 automated checks** được tổ chức thành **7 danh mục kiểm tra**.

### Kết quả kiểm định mới nhất:
| Tổng số kiểm tra | Trạng thái PASS | Cảnh báo (WARNING) | Lỗi nghiêm trọng (CRITICAL FAIL) |
| :---: | :---: | :---: | :---: |
| **72** | **69** | **3** | **0** |

Toàn bộ 69 critical checks đều đạt tuyệt đối, đảm bảo dữ liệu trong kho hoàn toàn sẵn sàng cho phân tích (Analytics-Ready). 3 cảnh báo ở mức WARNING phản ánh các đặc thù nhiễu thực tế từ hệ thống nguồn Olist và đã được lưu vết chi tiết trong các tệp CSV.

---

## 2. Chi tiết các hạng mục kiểm tra ĐÃ TRIỂN KHAI (IMPLEMENTED)

### 2.1. Hạng mục 1: Key & Referential Integrity (Tính toàn vẹn khóa & tham chiếu)
- **Kiểm tra 1.1 — Primary Key Uniqueness & Not Null (6 checks)**:
  - Đảm bảo các khóa chính `customer_key`, `date_key`, `product_key`, `seller_key`, `sales_key`, `fulfillment_key` không trùng lặp và không chứa giá trị `NULL`.
  - Trạng thái: **PASS** (100%).
- **Kiểm tra 1.2 — Fact Sales Grain Uniqueness (1 check)**:
  - Kiểm tra tính duy nhất của cặp `(order_id, order_item_id)`.
  - Trạng thái: **PASS** (Không có bản ghi trùng lặp grain).
- **Kiểm tra 1.3 — Fact Order Fulfillment Grain Uniqueness (1 check)**:
  - Kiểm tra tính duy nhất của `order_id` trong `fact_order_fulfillment`.
  - Trạng thái: **PASS** (Chính xác 1 dòng cho mỗi order).
- **Kiểm tra 1.4 — Orphan Foreign Keys (9 checks)**:
  - Quét tìm các bản ghi mồ côi (Foreign Key không tồn tại trong Dimension tương ứng).
  - Kiểm tra các liên kết:
    - `fact_sales` $\rightarrow$ `dim_customer`, `dim_product`, `dim_seller`, `dim_date`.
    - `fact_order_fulfillment` $\rightarrow$ `dim_customer`, và 5 role-playing `dim_date`.
  - Trạng thái: **PASS** (Tỷ lệ mồ côi = 0.0%).

### 2.2. Hạng mục 2: Null Checks & Độ bao phủ (Null Rate Auditing)
- **Tập trung kiểm tra**:
  - Đo lường tỷ lệ `NULL` trên toàn bộ 62 cột của 6 bảng trong kho.
  - Tự động xuất bảng tổng quan vào `validation_reports/warehouse_null_rates_overview.csv`.
  - Kiểm tra nghiêm ngặt: Các cột bắt buộc (`is_mandatory = True`) như Business Keys, Measures chính, và Trạng thái đơn hàng không được phép có bất kỳ giá trị `NULL` nào.
  - Trạng thái: **PASS** (Không có cột bắt buộc nào vi phạm).

### 2.3. Hạng mục 3: Business Rules & Đo lường hợp lệ (Business Rules Validation)
- **Kiểm tra 3.1 — Non-negative Monetary Values**:
  - `fact_sales.price >= 0` và `freight_value >= 0`.
  - `fact_order_fulfillment.total_payment_value >= 0`.
  - Trạng thái: **PASS**.
- **Kiểm tra 3.2 — Sales Amount Formula Consistency**:
  - Xác minh công thức `sales_amount = price + freight_value` trên từng dòng của `fact_sales`.
  - Trạng thái: **PASS** (Đúng tuyệt đối trên 112,650 dòng).
- **Kiểm tra 3.3 — Review Score Boundaries**:
  - Kiểm tra `review_score` chỉ nằm trong tập giá trị nguyên `{1, 2, 3, 4, 5}`.
  - Trạng thái: **PASS**.
- **Kiểm tra 3.4 — Fulfillment SLA Durations (No Negatives)**:
  - `hours_to_approval >= 0`
  - `hours_to_carrier >= 0`
  - `hours_to_customer >= 0`
  - `total_fulfillment_hours >= 0`
  - Trạng thái: **PASS** (Các mốc nghịch lý đã được chuyển thành `NULL` an toàn thay vì để số âm).
- **Kiểm tra 3.5 — Valid Order Status Values**:
  - Xác nhận `order_status` chỉ chứa các giá trị chuẩn: `delivered`, `shipped`, `canceled`, `invoiced`, `processing`, `unavailable`.
  - Trạng thái: **PASS**.

### 2.4. Hạng mục 4: Date Logic & Thứ tự thời gian (Temporal Sequencing)
- Kiểm tra tính tuần tự hợp lý của các sự kiện:
  1. `order_purchase_timestamp <= order_approved_at`
  2. `order_approved_at <= order_delivered_carrier_date`
  3. `order_delivered_carrier_date <= order_delivered_customer_date`
- **Kết quả**:
  - 1 check đạt **PASS** (Purchase $\le$ Approved).
  - 2 checks cảnh báo **WARNING** do dữ liệu thô nguồn Olist có độ trễ cập nhật trạng thái:
    - `date_logic_approved_gt_carrier.csv`: Một số đơn ghi nhận xuất kho trước khi hệ thống ghi log duyệt thanh toán.
    - `date_logic_carrier_gt_delivered.csv`: 21 đơn có sự kiện quét nhận hàng ghi sau khi bưu tá đã phát thành công.
  - Đây là đặc thù hệ thống nguồn thực tế, ETL đã xử lý bảo vệ bằng cách gán `NULL` cho duration để không làm méo mó các chỉ số SLA.

### 2.5. Hạng mục 5: Dim Date Integrity (Tính liên tục của chiều thời gian)
- **Kiểm tra 5.1 — Format Key**: Đảm bảo toàn bộ `date_key` theo format `YYYYMMDD`.
- **Kiểm tra 5.2 — Calendar Continuity**:
  - Xác minh không bị nhảy cóc hoặc thiếu bất kỳ ngày nào từ `2016-01-01` đến `2019-12-31`.
  - Tổng số ngày đúng bằng 1,461 ngày.
  - Trạng thái: **PASS**.

### 2.6. Hạng mục 6: Formatting Checks (Định dạng chuỗi chuẩn)
- **Kiểm tra 6.1 — Zip Code Format**: `^\d{5}$` (đúng 5 chữ số, bảo toàn số 0 ở đầu).
- **Kiểm tra 6.2 — State Code Format**: `^[A-Z]{2}$` (đúng 2 ký tự hoa mã bang).
- **Kiểm tra 6.3 — Whitespace Checks**: Không có khoảng trắng thừa ở đầu/cuối chuỗi trong tên thành phố, mã định danh.
- Trạng thái: **PASS**.

### 2.7. Hạng mục 7: Financial Reconciliation (Đối soát tài chính Sales vs Payment)
- **Kiểm tra**: Đối soát giữa tổng giá trị món hàng (`SUM(fact_sales.sales_amount)`) và tổng tiền khách thanh toán (`fact_order_fulfillment.total_payment_value`) ở cấp đơn hàng.
- **Kết quả**:
  - Đa số đơn hàng khớp 100%.
  - 1 check cảnh báo **WARNING**: Có 255 đơn hàng chênh lệch giá trị $> 1\%$ (lưu vết tại `validation_reports/reconciliation_sales_vs_payment_diff_gt_1pct.csv`).
  - Nguyên nhân nghiệp vụ: Khách hàng áp dụng mã giảm giá của sàn (platform voucher), trừ điểm tích lũy hoặc phát sinh phí thanh toán trả góp.

---

## 3. Các khuyến nghị nâng cấp trong tương lai (RECOMMENDED)

Dưới đây là các hạng mục khuyến nghị cho giai đoạn tiếp theo (chưa triển khai trong repo hiện tại):

| Hạng mục khuyến nghị | Chi tiết kỹ thuật | Lợi ích |
| :--- | :--- | :--- |
| **CI/CD Integration** | Tự động chạy `validate_warehouse.py` trong GitHub Actions sau mỗi pull request. | Chặn đứng mã lỗi trước khi merge vào nhánh chính. |
| **Automated Alerts** | Tích hợp Webhook (Slack / Discord / Teams) gửi tin nhắn khi có Critical Failures. | Đội ngũ kỹ sư nhận thông báo sự cố tức thời. |
| **Data Drift Monitoring** | Giám sát độ trôi của phân phối dữ liệu (Distribution Drift) trên `price` và `review_score`. | Phát hiện biến động bất thường của thị trường hoặc lỗi nguồn dữ liệu. |
| **dbt-expectations** | Chuẩn hóa các assertions bằng thư viện Great Expectations hoặc dbt tests nếu chuyển đổi hạ tầng sang dbt. | Tăng tính tiêu chuẩn hóa trong cộng đồng kỹ sư dữ liệu. |
