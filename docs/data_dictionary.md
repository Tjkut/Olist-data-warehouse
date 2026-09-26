# Olist Data Warehouse — Business Data Dictionary

Tài liệu này là Từ điển dữ liệu nghiệp vụ (Data Dictionary) chuẩn hóa cho toàn bộ schema `warehouse`. Mọi định nghĩa cột, kiểu dữ liệu, ý nghĩa kinh doanh và quy tắc tính toán/tổng hợp (aggregation) được giải thích chi tiết dưới góc nhìn phân tích kinh doanh.

---

## 1. Bảng `warehouse.fact_sales`

- **Mức độ chi tiết (Grain)**: 1 dòng cho mỗi order item (`order_id`, `order_item_id`).

### 1.1. Bảng thuộc tính định danh & Khóa ngoại
| Tên cột | Kiểu dữ liệu | Ý nghĩa kỹ thuật | Định nghĩa nghiệp vụ | Ghi chú & Ràng buộc |
| :--- | :--- | :--- | :--- | :--- |
| `sales_key` | `BIGSERIAL` | Surrogate Key | Khóa chính nhân tạo định danh từng dòng bán hàng | PK, Not Null, Unique |
| `order_id` | `TEXT` | Degenerate Dimension | Mã định danh đơn hàng từ hệ thống nguồn Olist | Dùng để gom nhóm các item cùng một đơn |
| `order_item_id` | `SMALLINT` | Degenerate Dimension | Số thứ tự món hàng trong đơn (1, 2, 3...) | Kết hợp với `order_id` tạo thành Grain |
| `customer_key` | `INT` | Foreign Key | Tham chiếu tới khách hàng đặt mua món hàng này | Nối sang `dim_customer(customer_key)` |
| `product_key` | `INT` | Foreign Key | Tham chiếu tới sản phẩm được bán | Nối sang `dim_product(product_key)` |
| `seller_key` | `INT` | Foreign Key | Tham chiếu tới người bán cung cấp món hàng này | Nối sang `dim_seller(seller_key)` |
| `date_key` | `INT` | Foreign Key | Tham chiếu tới ngày đặt hàng (`order_purchase_timestamp::DATE`) | Nối sang `dim_date(date_key)`, format `YYYYMMDD` |

### 1.2. Các thước đo kinh doanh (Measures)

#### A. `price`
- **Ý nghĩa nghiệp vụ**: Đơn giá bán niêm yết của món hàng.
- **Đơn vị tính**: Đồng Real Brazil (BRL).
- **Quy tắc tổng hợp hợp lệ**:
  - `SUM(price)`: Tính tổng doanh thu sản phẩm (Gross Merchandise Value - GMV, chưa gồm phí ship).
  - `AVG(price)`: Tính giá trị trung bình trên mỗi món hàng bán ra.
  - `MIN(price)` / `MAX(price)`: Mức giá thấp nhất/cao nhất của mặt hàng.
- **Rủi ro nhân đôi (Double-Counting Risk)**: Rất an toàn khi tổng hợp trực tiếp trên `fact_sales`. Tuy nhiên, nếu join `fact_sales` với bất kỳ bảng nào có quan hệ $1:N$ mà không lọc, giá trị này sẽ bị nhân lên.

#### B. `freight_value`
- **Ý nghĩa nghiệp vụ**: Cước phí vận chuyển được phân bổ cho riêng món hàng này.
- **Đơn vị tính**: Đồng Real Brazil (BRL).
- **Quy tắc tổng hợp hợp lệ**:
  - `SUM(freight_value)`: Tổng cước vận chuyển thu từ khách hàng.
  - `AVG(freight_value)`: Cước vận chuyển trung bình trên mỗi sản phẩm.
- **Lưu ý**: Một đơn hàng có nhiều món có thể chia đều hoặc phân bổ cước vận chuyển cho từng món.

#### C. `sales_amount`
- **Ý nghĩa nghiệp vụ**: Tổng giá trị thanh toán cấu thành của món hàng = `price + freight_value`.
- **Đơn vị tính**: Đồng Real Brazil (BRL).
- **Công thức DWH**: `COALESCE(price, 0) + COALESCE(freight_value, 0)`.
- **Quy tắc tổng hợp hợp lệ**:
  - `SUM(sales_amount)`: Tổng doanh số giao dịch (Total Item-level Sales).
  - `AVG(sales_amount)`: Giá trị trung bình của một item giao dịch.

---

## 2. Bảng `warehouse.fact_order_fulfillment`

- **Mức độ chi tiết (Grain)**: 1 dòng cho mỗi đơn hàng (`order_id`).

### 2.1. Bảng thuộc tính định danh, Trạng thái & Khóa ngoại
| Tên cột | Kiểu dữ liệu | Ý nghĩa kỹ thuật | Định nghĩa nghiệp vụ | Ghi chú & Ràng buộc |
| :--- | :--- | :--- | :--- | :--- |
| `fulfillment_key` | `BIGSERIAL` | Surrogate Key | Khóa chính nhân tạo định danh vòng đời xử lý đơn hàng | PK, Not Null, Unique |
| `order_id` | `TEXT` | Natural Key / Degenerate Dim | Mã định danh đơn vị giao dịch duy nhất | Unique, Not Null |
| `customer_key` | `INT` | Foreign Key | Tham chiếu tới khách hàng đặt đơn hàng này | Nối sang `dim_customer(customer_key)` |
| `order_purchase_date_key` | `INT` | Role-playing Date FK | Ngày đơn hàng được khách khởi tạo trên sàn | Format `YYYYMMDD` |
| `order_approved_date_key` | `INT` | Role-playing Date FK | Ngày khoản thanh toán đơn hàng được hệ thống duyệt | Nhận `NULL` nếu đơn chưa duyệt hoặc hủy |
| `carrier_pickup_date_key` | `INT` | Role-playing Date FK | Ngày kiện hàng được bàn giao cho đối tác vận chuyển | Nhận `NULL` nếu chưa xuất kho |
| `delivered_date_key` | `INT` | Role-playing Date FK | Ngày khách hàng ký nhận kiện hàng thành công | Nhận `NULL` nếu đơn đang giao hoặc thất lạc |
| `estimated_delivery_date_key`| `INT` | Role-playing Date FK | Ngày giao hàng dự kiến ban đầu cam kết với khách | Luôn có sẵn từ thời điểm đặt đơn |
| `order_status` | `TEXT` | Degenerate Dimension | Trạng thái hiện tại của đơn hàng | `delivered`, `shipped`, `canceled`, `invoiced`, `processing`, `unavailable` |
| `is_on_time` | `BOOLEAN` | SLA Flag | Đánh dấu đơn hàng có được giao đúng hoặc trước ngày dự kiến | `TRUE`: đúng hạn, `FALSE`: trễ hạn, `NULL`: chưa giao |

### 2.2. Các thước đo kinh doanh (Measures)

#### A. `hours_to_approval`
- **Ý nghĩa nghiệp vụ**: Thời gian từ lúc khách nhấn đặt hàng đến khi cổng thanh toán phê duyệt giao dịch.
- **Đơn vị tính**: Giờ (Hours, làm tròn 2 chữ số thập phân).
- **Công thức**: `(order_approved_at - order_purchase_timestamp) / 3600`.
- **Quy tắc**: Nhận `NULL` nếu mốc thời gian thiếu hoặc ngược thứ tự (approved < purchase).
- **Quy tắc tổng hợp**: `AVG(hours_to_approval)`, `PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY hours_to_approval)`.

#### B. `hours_to_carrier`
- **Ý nghĩa nghiệp vụ**: Thời gian người bán chuẩn bị hàng, đóng gói và bàn giao cho bưu tá / đơn vị vận chuyển.
- **Đơn vị tính**: Giờ (Hours).
- **Công thức**: `(order_delivered_carrier_date - order_approved_at) / 3600`.
- **Quy tắc tổng hợp**: `AVG(hours_to_carrier)` (thước đo đánh giá tốc độ xử lý kho của Merchant).

#### C. `hours_to_customer`
- **Ý nghĩa nghiệp vụ**: Thời gian hàng di chuyển trên mạng lưới bưu chính từ kho vận chuyển đến tay khách hàng (Transit time).
- **Đơn vị tính**: Giờ (Hours).
- **Công thức**: `(order_delivered_customer_date - order_delivered_carrier_date) / 3600`.
- **Quy tắc tổng hợp**: `AVG(hours_to_customer)` (thước đo đánh giá năng lực logistics).

#### D. `total_fulfillment_hours`
- **Ý nghĩa nghiệp vụ**: Tổng thời gian hoàn tất đơn hàng từ lúc đặt đến lúc nhận hàng thành công (End-to-End Fulfillment Lead Time).
- **Đơn vị tính**: Giờ (Hours).
- **Công thức**: `(order_delivered_customer_date - order_purchase_timestamp) / 3600`.
- **Quy tắc tổng hợp**: `AVG(total_fulfillment_hours)`, `MEDIAN`.

#### E. `days_vs_estimate`
- **Ý nghĩa nghiệp vụ**: Mức độ sai lệch giữa ngày giao thực tế so với ngày giao dự kiến.
- **Đơn vị tính**: Ngày (Days, số thực).
- **Ý nghĩa giá trị**:
  - `> 0`: Giao trễ hẹn (ví dụ: `+3.5` là giao trễ 3.5 ngày).
  - `< 0`: Giao sớm hơn cam kết (ví dụ: `-4.0` là giao trước hẹn 4 ngày).
  - `= 0`: Giao đúng ngày dự kiến.
- **Quy tắc tổng hợp**: `AVG(days_vs_estimate)`, `COUNT(*) FILTER (WHERE days_vs_estimate > 0)` (số đơn trễ hạn).

#### F. `review_score`
- **Ý nghĩa nghiệp vụ**: Mức độ hài lòng của khách hàng (CSAT), thang điểm từ 1 đến 5 sao.
- **Đơn vị tính**: Điểm nguyên (1 đến 5).
- **Nguồn gốc**: Lấy điểm đánh giá mới nhất theo thời gian tạo review (`DISTINCT ON (order_id) ORDER BY review_creation_date DESC`).
- **Quy tắc tổng hợp**: `AVG(review_score)` (Điểm đánh giá trung bình), phân phối tần suất điểm review.

#### G. `total_payment_value`
- **Ý nghĩa nghiệp vụ**: Tổng số tiền thực tế khách hàng thanh toán cho đơn hàng (đã gộp các phương thức thẻ, boleto, voucher).
- **Đơn vị tính**: Đồng Real Brazil (BRL).
- **Quy tắc tổng hợp**:
  - `SUM(total_payment_value)`: Tổng tiền thanh toán thu về ở cấp đơn hàng.
  - `AVG(total_payment_value)`: Giá trị trung bình trên một đơn hàng (Average Order Value - AOV).
- **Cảnh báo quan trọng**: **KHÔNG ĐƯỢC** tính `SUM(total_payment_value)` sau khi join với `fact_sales` mà không gom nhóm trước!

#### H. `payment_count`
- **Ý nghĩa nghiệp vụ**: Số lần quẹt thẻ / số giao dịch thanh toán tạo nên đơn hàng (phản ánh việc thanh toán bằng nhiều thẻ hoặc kết hợp voucher).
- **Đơn vị tính**: Số lần (Integer).
- **Quy tắc tổng hợp**: `AVG(payment_count)`, `MAX(payment_count)`.

---

## 3. Bảng `warehouse.dim_customer`

- **Mức độ chi tiết (Grain)**: 1 dòng cho mỗi khách hàng thực (`customer_unique_id`).

| Tên cột | Kiểu dữ liệu | Ý nghĩa kỹ thuật | Định nghĩa nghiệp vụ | Ghi chú |
| :--- | :--- | :--- | :--- | :--- |
| `customer_key` | `SERIAL` | Surrogate Key | Khóa chính nhân tạo định danh khách hàng trong kho | PK, Not Null, Unique |
| `customer_unique_id` | `TEXT` | Natural Key | Mã định danh duy nhất của khách hàng thực tế (tồn tại xuyên suốt nhiều đơn hàng) | Business Key, Unique |
| `customer_city` | `TEXT` | Attribute | Tên thành phố cư trú chính của khách hàng | Đã chuẩn hóa chuỗi (`TRIM`) |
| `customer_state` | `CHAR(2)` | Attribute | Mã 2 ký tự viết hoa của bang (Brazil) | Ví dụ: `SP` (São Paulo), `RJ` (Rio de Janeiro) |
| `zip_code_prefix` | `CHAR(5)` | Attribute | 5 chữ số đầu của mã bưu chính (CEP) | Bảo toàn số 0 ở đầu (dạng TEXT) |

---

## 4. Bảng `warehouse.dim_product`

- **Mức độ chi tiết (Grain)**: 1 dòng cho mỗi mã sản phẩm (`product_id`).

| Tên cột | Kiểu dữ liệu | Ý nghĩa kỹ thuật | Định nghĩa nghiệp vụ | Ghi chú |
| :--- | :--- | :--- | :--- | :--- |
| `product_key` | `SERIAL` | Surrogate Key | Khóa chính nhân tạo của sản phẩm | PK, Not Null, Unique |
| `product_id` | `TEXT` | Natural Key | Mã sản phẩm duy nhất từ hệ thống nguồn | Business Key, Unique |
| `category_name` | `TEXT` | Dimension Attribute | Tên danh mục gốc bằng tiếng Bồ Đào Nha | Ví dụ: `beleza_saude`, `cama_mesa_banho` |
| `category_name_english` | `TEXT` | Dimension Attribute | Tên danh mục tiếng Anh chuẩn hóa | Ví dụ: `health_beauty`. Fallback `'unknown'` nếu thiếu |
| `product_name_length` | `INT` | Attribute | Độ dài (số ký tự) của tiêu đề sản phẩm | Phục vụ phân tích tối ưu nội dung niêm yết |
| `product_description_length`| `INT` | Attribute | Độ dài (số ký tự) của bài viết mô tả sản phẩm | Phục vụ phân tích SEO / Content |
| `product_photos_qty` | `INT` | Attribute | Số lượng hình ảnh minh họa của sản phẩm | Thống kê chất lượng hình ảnh gian hàng |
| `product_weight_g` | `NUMERIC(10,2)` | Attribute | Khối lượng sản phẩm tính bằng gram | Ảnh hưởng trực tiếp đến phí vận chuyển |
| `product_length_cm` | `NUMERIC(8,2)` | Attribute | Chiều dài kiện hàng (cm) | Tính toán thể tích quy đổi cước |
| `product_height_cm` | `NUMERIC(8,2)` | Attribute | Chiều cao kiện hàng (cm) | Tính toán thể tích quy đổi cước |
| `product_width_cm` | `NUMERIC(8,2)` | Attribute | Chiều rộng kiện hàng (cm) | Tính toán thể tích quy đổi cước |

---

## 5. Bảng `warehouse.dim_seller`

- **Mức độ chi tiết (Grain)**: 1 dòng cho mỗi người bán đối tác (`seller_id`).

| Tên cột | Kiểu dữ liệu | Ý nghĩa kỹ thuật | Định nghĩa nghiệp vụ | Ghi chú |
| :--- | :--- | :--- | :--- | :--- |
| `seller_key` | `SERIAL` | Surrogate Key | Khóa chính nhân tạo của người bán | PK, Not Null, Unique |
| `seller_id` | `TEXT` | Natural Key | Mã định danh duy nhất của người bán trên Olist | Business Key, Unique |
| `seller_city` | `TEXT` | Attribute | Tên thành phố đặt trụ sở/kho của người bán | Đã chuẩn hóa chuỗi (`TRIM`) |
| `seller_state` | `CHAR(2)` | Attribute | Mã 2 ký tự của bang người bán đăng ký hoạt động | Ví dụ: `SP`, `PR`, `MG` |
| `zip_code_prefix` | `CHAR(5)` | Attribute | 5 chữ số đầu mã bưu chính kho hàng của người bán | Giữ nguyên định dạng chuỗi |

---

## 6. Bảng `warehouse.dim_date`

- **Mức độ chi tiết (Grain)**: 1 dòng cho mỗi ngày lịch (2016-01-01 đến 2019-12-31).

| Tên cột | Kiểu dữ liệu | Ý nghĩa kỹ thuật | Định nghĩa nghiệp vụ | Ghi chú / Ví dụ |
| :--- | :--- | :--- | :--- | :--- |
| `date_key` | `INT` | Primary Key | Khóa ngày theo chuẩn YYYYMMDD | Ví dụ: `20180105` |
| `full_date` | `DATE` | Calendar Date | Ngày chuẩn ISO | `2018-01-05` |
| `year` | `SMALLINT` | Calendar Year | Năm lịch | `2016`, `2017`, `2018`, `2019` |
| `quarter` | `SMALLINT` | Quarter | Quý trong năm (1 đến 4) | `1`, `2`, `3`, `4` |
| `month` | `SMALLINT` | Month Number | Tháng trong năm (1 đến 12) | `1` đến `12` |
| `month_name` | `VARCHAR(9)` | Month Name | Tên tiếng Anh đầy đủ của tháng | `January`, `February`, ... |
| `week_of_year` | `SMALLINT` | Week Number | Tuần trong năm theo chuẩn ISO (1 đến 53) | `1` đến `53` |
| `day_of_month` | `SMALLINT` | Day | Ngày trong tháng (1 đến 31) | `1` đến `31` |
| `day_of_week` | `SMALLINT` | Day of Week | Thứ trong tuần theo chuẩn PostgreSQL (1=CN, 7=T7) | `1=Sunday` ... `7=Saturday` |
| `day_name` | `VARCHAR(9)` | Day Name | Tên tiếng Anh của thứ trong tuần | `Monday`, `Tuesday`, ... |
| `is_weekend` | `BOOLEAN` | Weekend Flag | Cờ đánh dấu ngày cuối tuần | `TRUE` nếu Thứ Bảy hoặc Chủ Nhật |
