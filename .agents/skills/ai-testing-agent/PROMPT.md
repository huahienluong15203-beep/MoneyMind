# Prompt Tạo Skill: AI Testing Agent (Security Pentest & Business Rules)

> **Mục tiêu:** Xây dựng AI Testing Agent tự trị cấp cao, có khả năng tự động sinh payload tấn công bảo mật (SQLi, XSS, IDOR, CSRF, Brute-force) và kiểm tra nghiêm ngặt 6 quy tắc nghiệp vụ tài chính (BR-01 đến BR-06).

---

## 📌 Nội Dung Prompt Gốc Đã Sử Dụng

```text
Bạn là Chuyên gia An toàn Thông tin (Senior Penetration Tester & Lead QA Architect).
Hãy xây dựng skill 'ai-testing-agent' nhằm biến trợ lý AI thành một Testing Agent tự trị tinh nhuệ cho MoneyMind:

1. Mục tiêu tối thượng:
   - Tự động phân tích code, phát hiện rủi ro logic và lỗ hổng bảo mật.
   - Tự động sinh dữ liệu đầu vào nguy hiểm (Malicious Inputs/Fuzzing).
   - Kiểm tra toàn diện 6 quy tắc nghiệp vụ vàng (Business Rules BR-01 đến BR-06).

2. Danh mục tấn công & Kịch bản cần triển khai:
   - SQL Injection (SQLi): Tấn công qua filter tìm kiếm giao dịch, tên danh mục, ghi chú. Kiểm tra xem ORM parameterized query có chặn 100% không.
   - Stored / Reflected XSS: Chèn các payload `<script>alert(1)</script>`, `<img src=x onerror=...>` vào tên người dùng, tên hũ ngân sách, ghi chú giao dịch.
   - Broken Authentication & Brute-force: Kiểm tra cơ chế Rate Limit khi đăng nhập sai nhiều lần, xác thực mã OTP email hết hạn.
   - Insecure Direct Object References (IDOR): User A sử dụng token hợp lệ nhưng cố tình truy xuất / cập nhật / xóa giao dịch của User B.
   - Mass Assignment / Schema Poisoning: Gửi trường `la_admin=true` hoặc `trang_thai=active` trái phép khi đăng ký tài khoản.

3. Kiểm tra 6 quy tắc nghiệp vụ tài chính (BR-01 -> BR-06):
   - BR-01: Ngân sách 6 hũ (Tổng tỷ lệ phân bổ các hũ phải đúng 100%).
   - BR-02: Không cho phép giao dịch có số tiền âm hoặc bằng 0.
   - BR-03: Cảnh báo chi tiêu vượt ngưỡng ngân sách hũ (80%, 100%).
   - BR-04: Đóng băng/khóa tài khoản khi nhập sai OTP quá 5 lần.
   - BR-05: Bảo vệ quyền riêng tư: Ẩn danh hóa họ tên, số tài khoản trước khi gửi sang Gemini API.
   - BR-06: Hoàn tác số dư chính xác khi xóa hoặc sửa đổi giao dịch.

4. Sản phẩm đính kèm:
   - Bộ test case tự động mẫu bằng pytest: `tests/test_security_agent.py` bao gồm 38+ test cases chứng minh toàn bộ các lỗ hổng đã được phòng vệ thành công.

Định dạng đầu ra: Chuẩn SKILL.md với YAML frontmatter hợp lệ cho Antigravity AI Agent.
```

---

## 🚀 Hướng Dẫn Tái Tạo Hoặc Nâng Cấp Skill Này

Khi muốn yêu cầu AI cập nhật hoặc tái tạo skill này, hãy gửi prompt sau:

```text
Hãy đọc toàn bộ `app/models/`, `app/controllers/`, `app/services/` và `tests/test_security_agent.py`.
Cập nhật file `.agents/skills/ai-testing-agent/SKILL.md`:
- Bổ sung thêm các vector tấn công mới (ví dụ: JWT alg=none exploit, Replay Attack, Timing Attack).
- Cập nhật ma trận rủi ro và bảng chấm điểm mức độ nghiêm trọng CVE/CWE.
- Mở rộng thêm các quy tắc nghiệp vụ tài chính mới (BR-07, BR-08) nếu ứng dụng bổ sung thêm tính năng ví liên kết hoặc đầu tư.
```
