---
name: ai-financial-advisor
description: Chức năng Trợ lý Tài chính Thông minh AI Gemini, Sinh Báo cáo Tài chính Tháng, Đánh giá Sức khỏe Chi tiêu và Bảo vệ Quyền riêng tư Dữ liệu trong MoneyMind.
---

# Kỹ Năng: Trợ Lý Tài Chính AI & Báo Cáo Thông Minh (AI Advisor)

Chức năng ứng dụng mô hình trí tuệ nhân tạo tạo sinh Google Gemini để đóng vai trò Chuyên gia Hoạch định Tài chính Cá nhân (CFP) riêng cho mỗi người dùng.

---

## 1. Kiến Trúc & Công Cụ

- **Dịch vụ AI Trung Tâm**: [ai_service.py](file:///c:/Users/Admin/OneDrive/Desktop/DỰ ÁN LỚN/app/services/ai_service.py) (44KB - Module nghiệp vụ đồ sộ nhất)
  - Sử dụng REST API v1beta / Google Generative AI với mô hình **Gemini 3.8 Flash** thế hệ mới nhất của Google.
  - Tích hợp Prompt Engineering chuyên sâu về phương pháp 6 hũ.
  - Cơ chế Cascade Multi-Model Fallback an toàn (3.8 Flash -> 3.7 Flash -> Flash Latest) khi API gặp sự cố timeout hoặc hết quota (HTTP 429).

- **Bộ Lọc Quyền Riêng Tư**: [privacy_service.py](file:///c:/Users/Admin/OneDrive/Desktop/DỰ ÁN LỚN/app/services/privacy_service.py)
  - **Quy tắc BR-05**: Ẩn danh hóa 100% dữ liệu nhạy cảm (email, họ tên thật, số tài khoản) trước khi gửi payload sang máy chủ Gemini của Google.
- **ORM Model Cache**: [bao_cao_ai.py](file:///c:/Users/Admin/OneDrive/Desktop/DỰ ÁN LỚN/app/models/bao_cao_ai.py)
  - Bảng `bao_cao_ai` lưu trữ kết quả phân tích theo từng tháng để người dùng không phải gọi lại API tốn chi phí.
- **Frontend UI**: [ai.js](file:///c:/Users/Admin/OneDrive/Desktop/DỰ ÁN LỚN/frontend/js/ai.js)
  - Khung chat AI Drawer trượt từ cạnh phải, định dạng tin nhắn Markdown có bảng biểu và icon.

---

## 2. Các Tính Năng AI Cung Cấp

1. **Báo Cáo Tài Chính Tháng Tự Động**:
   - Chấm điểm sức khỏe tài chính trên thang điểm 100.
   - Nhận xét chi tiết việc tuân thủ quy tắc 6 hũ.
   - Đưa ra 3 hành động cụ thể người dùng cần làm trong tháng tới để cải thiện số dư.
2. **Tư Vấn Ngân Sách Thông Minh**:
   - Phân tích thu nhập thực tế và đề xuất mức phân bổ tiền mặt chi tiết cho từng hũ.
3. **Chat Hỏi Đáp Trực Tiếp**:
   - Trả lời các câu hỏi: "Tôi có nên mua điện thoại mới lúc này?", "Làm sao để tiết kiệm tiền ăn uống?".
4. **Đặc Vụ Tài Chính Tự Hành Hoàn Toàn Bằng Giao Tiếp Tự Nhiên (AI Autonomous Financial Agent)**:
   Mọi thao tác thủ công trên MoneyMind giờ đây đều có thể điều khiển trực tiếp qua hội thoại:
   - **Giao dịch**:
     - *Thêm giao dịch*: *"Tôi đi ăn bánh mì 20k"*, *"Vừa mua cafe 35k"*, *"Đổ xăng 50k"*, *"Nhận lương 15tr"*.
     - *Sửa giao dịch*: *"Sửa giao dịch gần nhất thành 45k"*, *"Đổi ghi chú thành ăn trưa"*, *"Sửa số tiền giao dịch cafe thành 40k"*.
     - *Xóa giao dịch*: *"Xóa giao dịch vừa thêm"*, *"Hủy giao dịch gần nhất"*, *"Xóa giao dịch ăn bánh mì 20k"*.
     - *Tra cứu giao dịch*: *"Hôm nay tôi đã tiêu những gì?"*, *"Tìm các giao dịch ăn uống"*, *"Xem các khoản chi trên 200k"*, *"Xem 5 giao dịch gần nhất"*.
   - **Hũ Tiết Kiệm**:
     - *Tạo hũ*: *"Tạo hũ tiết kiệm mua laptop 20 triệu"*, *"Thêm mục tiêu du lịch đà nẵng 5 triệu hạn chót 31/12/2026"*.
     - *Nộp tiền*: *"Nộp 500k vào hũ du lịch"*, *"Trích 200k vào mua laptop"*.
     - *Nâng/Giảm mục tiêu*: *"Nâng mục tiêu du lịch lên 4 triệu"*, *"Giảm mục tiêu xuống 3tr"*.
     - *Rút tiền về ví*: *"Rút 500k từ hũ du lịch về ví chính"*, *"Hoàn 200k từ hũ về ví"*.
     - *Xóa hũ*: *"Xóa hũ du lịch"* (hoàn lại 100% tiền tích lũy về ví chính an toàn).
   - **Danh Mục & Ngân Sách Hũ**:
     - *Tạo danh mục*: *"Tạo danh mục học tập hạn mức 1 triệu"*, *"Thêm hũ từ thiện"*.
     - *Đổi tên danh mục*: *"Đổi tên danh mục đi chơi thành giải trí"*.
     - *Chỉnh hạn mức*: *"Nâng hạn mức ăn uống lên 3 triệu"*, *"Đặt hạn mức đi chơi là 1tr5"*.
     - *Xóa danh mục*: *"Xóa danh mục từ thiện"* (tự động thu hồi hạn mức khả dụng về ví).
   - **Sức Khỏe Tài Chính & 6 Hũ**:
     - *"Đánh giá sức khỏe tài chính"*, *"Chấm điểm tài chính"*, *"Tư vấn phân bổ 6 hũ"*.
   - Frontend tự động kích hoạt cập nhật giao diện thời gian thực (`loadSummary()`, `loadTransactions()`, `loadSavingsGoals()`, `loadCategories()`, `loadNotifications()`) tức thì mà không cần reload trang.

---

## 3. Mocking & Kiểm Thử Offline Không Tốn Phí

Xem chi tiết tại skill [mocking-ai-engine](file:///c:/Users/Admin/OneDrive/Desktop/DỰ ÁN LỚN/.agents/skills/mocking-ai-engine/SKILL.md) để chạy kiểm thử offline mà không cần API Key thật:

```powershell
.env\Scripts\pytest tests/test_ai.py -v
```
