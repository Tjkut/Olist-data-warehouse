# rules.md — Operational Coding & Data Engineering Rules

Tài liệu này định nghĩa các quy tắc thao tác kỹ thuật bắt buộc dành cho lập trình viên và AI Agent khi làm việc trong repository này. Mục tiêu là giảm thiểu sai sót, bảo toàn tính toàn vẹn của dữ liệu và đảm bảo can thiệp mã nguồn chính xác.

---

## 1. Nguyên tắc lập trình cốt lõi (Core Coding Principles)

### 1.1. Think Before Coding (Tư duy trước khi viết code)
- **Không giả định ngầm**: Nêu rõ giả định trước khi triển khai. Nếu có điểm chưa rõ, hãy dừng lại và đặt câu hỏi.
- **Làm rõ sự đánh đổi**: Nếu có nhiều phương án xử lý, hãy trình bày rõ ưu/nhược điểm (tradeoffs) thay vì tự ý chọn cách âm thầm.
- **Đơn giản hóa**: Luôn ưu tiên giải pháp tối giản, tường minh nhất có thể.

### 1.2. Simplicity First (Đơn giản là trên hết)
- **Code tối thiểu**: Chỉ viết lượng code tối thiểu cần thiết để giải quyết đúng bài toán được yêu cầu.
- **Không suy đoán tương lai (No Speculative Flexibility)**: Không tạo abstraction hoặc helper cho code chỉ dùng một lần. Không tạo cấu hình hay tham số thừa thãi chưa có nhu cầu sử dụng.
- **Loại bỏ ngoại lệ vô lý**: Không viết code bắt lỗi/xử lý ngoại lệ cho những kịch bản không thể xảy ra trong luồng dữ liệu.

### 1.3. Surgical Changes (Can thiệp chính xác như phẫu thuật)
- **Chạm đúng chỗ**: Chỉ chỉnh sửa những dòng code thực sự cần thay đổi theo yêu cầu.
- **Không lan man**: Không tự ý format lại, refactor hay "cải tiến" code/comment lân cận không thuộc phạm vi công việc.
- **Dọn dẹp tàn dư**: Khi thay đổi code sinh ra biến, hàm hoặc import không còn sử dụng, phải dọn dẹp sạch sẽ phần thừa đó của mình.
- **Truy xuất nguồn gốc**: Mọi dòng code thay đổi phải truy xuất trực tiếp được đến yêu cầu của người dùng.

### 1.4. Goal-Driven Execution (Thực thi theo mục tiêu kiểm chứng)
- Biến mọi yêu cầu thành mục tiêu có thể đo lường và kiểm chứng:
  - Sửa bug $\rightarrow$ Viết/chạy kiểm tra tái hiện lỗi $\rightarrow$ Sửa $\rightarrow$ Chạy lại kiểm tra để chứng minh đã hết lỗi.
  - Sửa ETL/SQL $\rightarrow$ Chạy pipeline $\rightarrow$ Chạy validation suite $\rightarrow$ Xác nhận pass toàn bộ critical checks.
- Đối với tác vụ nhiều bước, luôn xác định rõ tiêu chí hoàn thành của từng bước trước khi chuyển sang bước tiếp theo.

---

## 2. Quy tắc bảo vệ Kho dữ liệu & Dữ liệu nguồn (DWH & Data Guardrails)

### 2.1. Tính bất biến của dữ liệu nguồn (Source Immutability)
- **Bất khả xâm phạm**: Tuyệt đối không chỉnh sửa nội dung, không đổi tên, không xóa bất kỳ tệp CSV nào trong thư mục `datasets/`.
- Mọi dữ liệu nhiễu, sai định dạng hoặc thiếu sót phải được xử lý ở tầng chuyển đổi (Staging Views / ETL scripts), không can thiệp vào nguồn.

### 2.2. Quy tắc Chỉ-Đọc trong pha phân tích (Read-Only Analytics Rule)
- Trong các tác vụ phân tích dữ liệu (Analytics), Agent **CHỈ ĐƯỢC PHÉP** sử dụng câu lệnh `SELECT` truy vấn trên schema `warehouse`.
- **TUYỆT ĐỐI KHÔNG**: Chạy các câu lệnh `DROP`, `TRUNCATE`, `ALTER`, `UPDATE`, `DELETE` trên schema `warehouse` trong các tác vụ phân tích trừ khi người dùng có yêu cầu bằng văn bản rõ ràng.

### 2.3. Quy tắc đồng bộ 3 lớp khi thay đổi DWH (Three-Tier Sync Rule)
Khi có yêu cầu kỹ thuật rõ ràng về việc cập nhật hoặc bổ sung cấu trúc kho dữ liệu, bắt buộc phải đồng bộ xuyên suốt 4 thành phần:
1. **DDL Schema**: Cập nhật `sql/olist_dwh.sql` (hoặc `sql/olist_staging.sql`).
2. **Transformation Views**: Cập nhật logic ép kiểu và làm sạch tại `sql/olist_staging_views.sql`.
3. **ETL Loader**: Cập nhật mapping và câu lệnh nạp dữ liệu tại `scripts/load_warehouse.py`.
4. **Validation Suite**: Cập nhật hoặc bổ sung kiểm tra tương ứng tại `scripts/validate_warehouse.py`.

### 2.4. Tính Idempotency & An toàn giao dịch (Transaction Safety)
- Mọi script nạp dữ liệu phải có tính chất **Idempotent** (chạy một lần hay nhiều lần đều cho ra kết quả nhất quán, không sinh trùng lặp bản ghi).
- Quá trình nạp warehouse phải được bọc trong một Database Transaction duy nhất (`conn.autocommit = False`). Nếu có lỗi xảy ra hoặc kiểm tra nội bộ thất bại, phải thực hiện `conn.rollback()` ngay lập tức để bảo vệ dữ liệu cũ.

### 2.5. Bảo đảm bảng mã trên Windows (UTF-8 Encoding)
- Toàn bộ các script Python khi tương tác với terminal Windows phải thiết lập cấu hình UTF-8 ở đầu tệp:
  ```python
  if hasattr(sys.stdout, "reconfigure"):
      sys.stdout.reconfigure(encoding="utf-8")
  if hasattr(sys.stderr, "reconfigure"):
      sys.stderr.reconfigure(encoding="utf-8")
  ```
