# DWH Quality Test Suite (`tests/dwh_quality/`)

Thư mục này phục vụ việc tổ chức và tài liệu hóa các bài kiểm thử chất lượng kho dữ liệu (Data Quality Testing) và kiểm thử hồi quy (Regression Testing) cho Olist Data Warehouse.

---

## 1. Cơ chế kiểm thử hiện tại (Current Test Engine)

Dự án đã tích hợp sẵn bộ kiểm định tự động toàn diện tại:
`scripts/validate_warehouse.py`

Bộ kiểm định này thực thi **72 automated test checks** thuộc 7 nhóm kiểm thử:
1. **Key & Referential Integrity Tests**: Uniqueness, NOT NULL của khóa chính, Fact grain uniqueness và Orphan Foreign Keys.
2. **Null Rate Tests**: Quét toàn bộ 62 cột, bảo đảm không có NULL trên các trường bắt buộc (`is_mandatory = True`).
3. **Business Rules Tests**: Giá trị tiền không âm, công thức `sales_amount = price + freight_value`, biên giới hạn `review_score` (1-5 sao), SLA durations không âm.
4. **Temporal / Date Logic Tests**: Thứ tự tuần tự thời gian Purchase $\rightarrow$ Approved $\rightarrow$ Carrier $\rightarrow$ Customer.
5. **Calendar Continuity Tests**: Định dạng `date_key` YYYYMMDD và tính liên tục 1,461 ngày không đứt đoạn.
6. **Data Formatting Tests**: Chuẩn hóa Zip code (5 chữ số) và State code (2 ký tự hoa).
7. **Financial Reconciliation Tests**: Đối soát doanh thu món hàng so với tiền thanh toán ở cấp đơn hàng.

---

## 2. Cách thức chạy kiểm thử (Execution)

Chạy trực tiếp từ thư mục gốc của repository:

```bash
python scripts/validate_warehouse.py
```

- **Mã thoát (Exit Code)**:
  - `0`: Tất cả các kiểm thử Critical đều PASS (có thể có Warnings do dữ liệu nguồn).
  - `1`: Có ít nhất 1 kiểm thử Critical thất bại (pipeline bị coi là lỗi).
- **Báo cáo lỗi**: Bất kỳ kiểm thử nào phát hiện vi phạm sẽ tự động ghi các bản ghi sai lệch vào tệp CSV trong thư mục `validation_reports/`.

---

## 3. Tích hợp tương lai với Pytest (Recommended Enhancement)

Để tích hợp vào quy trình CI/CD (như GitHub Actions), có thể thiết lập wrapper `test_warehouse_quality.py` gọi hàm từ `scripts/validate_warehouse.py` và assert:

```python
import pytest
from scripts.validate_warehouse import get_connection, run_all_checks

def test_warehouse_critical_checks():
    conn = get_connection()
    results = run_all_checks(conn)
    critical_failures = [r for r in results if r.status == "FAIL"]
    assert len(critical_failures) == 0, f"Found {len(critical_failures)} critical failures!"
```
