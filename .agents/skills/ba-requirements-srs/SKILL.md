---
name: ba-requirements-srs
description: Phân tích Nghiệp vụ, Quy tắc Ràng buộc và Đặc tả SRS chuẩn IEEE 830 & ISO/IEC 25010 cho MoneyMind. Bao gồm Business Rules BR-01~BR-06, Functional Requirements FR01~FR11, Non-Functional Requirements NFR-01~NFR-06 và Ma trận Đối chiếu Yêu cầu.
---

# Kỹ Năng: Phân Tích Nghiệp Vụ & Đặc Tả SRS (Business Analysis & Requirements)

> **Chuyên môn**: Lead Business Analyst (BA) & Requirements Engineer
> **Nhiệm vụ**: Phân tích và xây dựng Bản đặc tả yêu cầu phần mềm (SRS) chuẩn IEEE 830 & ISO/IEC 25010 cho dự án MoneyMind.

---

## Bộ Nguyên Tắc Bắt Buộc

1. **Quy tắc nghiệp vụ (BR) phải là tiên quyết**: Mọi ràng buộc tính toán, kiểm tra ngân sách, phân quyền và bảo mật phải được mã hóa thành các mã quy tắc `BR-01, BR-02,...` tường minh.
2. **Yêu cầu chức năng (FR) phải có tính nguyên tử (atomic)**, không mơ hồ, chia thành 2 khối rõ ràng: Nghiệp vụ tài chính cốt lõi & Hỗ trợ thông minh AI.
3. **Yêu cầu phi chức năng (NFR) bắt buộc phải có chỉ số đo lường định lượng** (Quantifiable Metrics): Số giây, tỉ lệ %, mã thuật toán.

---

## 1. Danh Sách Quy Tắc Nghiệp Vụ (Business Rules - BR)

| Mã BR | Tên quy tắc | Mô tả chi tiết |
| :--- | :--- | :--- |
| **BR-01** | Tính toán vẹn Danh mục - Giao dịch | Loại của giao dịch (`giao_dich.loai_gd`) phải khớp tuyệt đối với loại của danh mục (`danh_muc.loai_dm`). Chỉ cho phép liên kết giao dịch CHI với danh mục CHI, THU với danh mục THU. |
| **BR-02** | Bảo mật Mật khẩu & Phiên đăng nhập | Mật khẩu bắt buộc băm 1 chiều bằng thuật toán Bcrypt với Salt Rounds >= 12 trước khi lưu vào CSDL. Phiên đăng nhập sử dụng JWT có thời hạn hiệu lực Access Token là 60 phút, Refresh Token là 7 ngày. |
| **BR-03** | Ẩn danh hóa dữ liệu AI - PII Sanitization | 100% dữ liệu trước khi gửi sang Google Gemini API (UC010, UC011, UC012) bắt buộc phải loại bỏ các thông tin định danh cá nhân (Họ tên, Email, Số điện thoại, ID CSDL). Dữ liệu chỉ được gửi dưới dạng JSON thuần số liệu tổng hợp. |
| **BR-04** | Bộ nhớ đệm Báo cáo AI - Caching | Kết quả phân tích báo cáo tháng (UC010) được lưu vào bảng `bao_cao_ai`. Khi người dùng xem lại báo cáo của tháng đã có, hệ thống trả về từ Cache DB, không gọi lại LLM nhằm tối ưu thời gian phản hồi (< 500ms) và tiết kiệm chi phí API. |
| **BR-05** | Ngưỡng cảnh báo ngân sách Real-time | Cảnh báo ngân sách được kích hoạt ngay trong luồng lưu giao dịch (UC004 include UC007). Hạn mức chia làm 2 cấp: Cấp Vàng (Warning): khi tổng chi tiêu đạt từ 80% đến dưới 100% hạn mức. Cấp Đỏ (Over-budget): khi tổng chi tiêu đạt từ 100% hạn mức trở lên. |
| **BR-06** | Phân quyền sở hữu dữ liệu - Chống IDOR | Mỗi người dùng chỉ có quyền đọc/ghi trên các bản ghi thuộc sở hữu của chính mình (`ma_nd = current_user_id`). Mọi thao tác truy cập trái phép sang bản ghi của người khác đều bị từ chối với mã HTTP 403 Forbidden hoặc 404 Not Found. |

---

## 2. Yêu Cầu Chức Năng (Functional Requirements - FR)

### Nhóm 1: Quản lý tài chính cá nhân cốt lõi

| Mã FR | Tên yêu cầu | Mô tả chi tiết |
| :--- | :--- | :--- |
| **FR01** | Quản lý tài khoản | Đăng ký, đăng nhập, khôi phục mật khẩu qua mã OTP gửi về Email, cập nhật hồ sơ cá nhân. |
| **FR02** | Quản lý danh mục | Tạo mới, chỉnh sửa, xóa và gắn biểu tượng cho các danh mục Thu/Chi cá nhân hóa. |
| **FR03** | Quản lý giao dịch | Thêm, sửa, xóa các khoản giao dịch thu nhập và chi tiêu. |
| **FR04** | Tra cứu & Lọc giao dịch | Tìm kiếm theo từ khóa ghi chú, lọc theo khoảng thời gian, danh mục hoặc khoảng số tiền. |
| **FR05** | Quản lý ngân sách | Thiết lập hạn mức chi tiêu theo từng tháng cho từng danh mục. |
| **FR06** | Cảnh báo ngân sách | Tự động tính toán tổng chi và bắn cảnh báo tức thời khi chạm ngưỡng 80% hoặc vượt 100%. |
| **FR07** | Quản lý mục tiêu tiết kiệm | Tạo mục tiêu tích lũy, nạp thêm tiền và theo dõi thanh tiến độ hoàn thành. |
| **FR08** | Thống kê & Biểu đồ | Hiển thị bảng điều khiển (Dashboard) trực quan gồm thẻ số dư, biểu đồ tròn cơ cấu chi tiêu và biểu đồ cột thu/chi theo thời gian. |

### Nhóm 2: Chức năng thông minh tích hợp AI

| Mã FR | Tên yêu cầu | Mô tả chi tiết |
| :--- | :--- | :--- |
| **FR09** | Phân tích & Báo cáo AI tháng | Sử dụng Google Gemini Flash phân tích thói quen tài chính và xuất báo cáo bằng ngôn ngữ tự nhiên gồm tóm tắt xu hướng và 3 lời khuyên hành động. |
| **FR10** | Gợi ý ngân sách thông minh | AI tự động tính toán lịch sử chi tiêu các tháng trước để đề xuất hạn mức ngân sách hợp lý cho tháng tiếp theo (áp dụng quy tắc 50/30/20). |
| **FR11** | Trợ lý Chatbot hỏi đáp tài chính | Cho phép người dùng đặt câu hỏi tự nhiên về dữ liệu thu chi và nhận câu trả lời súc tích dựa trên số liệu thực tế. |

---

## 3. Yêu Cầu Phi Chức Năng (NFR theo ISO 25010)

| Mã NFR | Loại | Chỉ số đo lường định lượng |
| :--- | :--- | :--- |
| **NFR-01** | Usability & Efficiency | Thao tác ghi nhận một giao dịch chi tiêu mới phải hoàn tất trong tối đa 3-5 giây với số lần nhấp chuột tối thiểu. |
| **NFR-02** | Performance - Response Time | Tốc độ phản hồi của các API nghiệp vụ CRUD giao dịch và tính toán ngân sách đạt trung bình < 300ms (với tải 10.000 bản ghi). |
| **NFR-03** | AI Latency & Fallback | Thời gian phản hồi báo cáo AI qua LLM không quá 5 giây; phản hồi qua Cache không quá 500ms. Nếu gọi LLM quá 5 giây hoặc gặp lỗi HTTP 429/503, hệ thống phải kích hoạt cơ chế Fallback thân thiện. |
| **NFR-04** | Privacy & Data Protection | Đảm bảo 100% dữ liệu gửi sang API bên thứ ba được ẩn danh hóa; giao diện người dùng hiển thị biểu tượng xác nhận Privacy Badge. |
| **NFR-05** | Availability & Reliability | Hệ thống đạt độ sẵn sàng tối thiểu 99.5%; dữ liệu giao dịch tài chính không bị mất mát khi có sự cố mạng. |
| **NFR-06** | Software Quality & Testing | Bộ kiểm thử tự động (Pytest) đạt độ bao phủ nghiệp vụ (Code Coverage) >= 85%, với tối thiểu 70+ test cases tự động. |

---

## 4. Ma Trận Đối Chiếu Yêu Cầu (Traceability Matrix)

| Mã FR | Tên yêu cầu chức năng | Use Case tương ứng | Quy tắc nghiệp vụ liên quan |
| :--- | :--- | :--- | :--- |
| FR01 | Quản lý tài khoản | UC001, UC002 | BR-02, BR-06 |
| FR02 | Quản lý danh mục | UC003 | BR-01, BR-06 |
| FR03 | Quản lý giao dịch | UC004 | BR-01, BR-05, BR-06 |
| FR04 | Tra cứu giao dịch | UC005 | BR-06 |
| FR05 | Quản lý ngân sách | UC006 | BR-05, BR-06 |
| FR06 | Cảnh báo ngân sách | UC007 | BR-05, BR-06 |
| FR07 | Quản lý mục tiêu tiết kiệm | UC008 | BR-06 |
| FR08 | Thống kê và báo cáo | UC009 | BR-06 |
| FR09 | Phân tích báo cáo AI | UC010 | BR-03, BR-04, BR-06 |
| FR10 | Gợi ý ngân sách AI | UC011 | BR-03, BR-06 |
| FR11 | Trợ lý Chatbot AI | UC012 | BR-03, BR-06 |
