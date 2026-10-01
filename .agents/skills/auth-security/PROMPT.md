# Prompt Tạo Skill: Xác Thực & Bảo Mật Tài Khoản (Auth & Security)

> **Mục tiêu:** Tạo skill hướng dẫn xây dựng, vận hành và kiểm thử toàn bộ hệ thống xác thực người dùng, OTP email và bảo mật JWT của MoneyMind.

---

## 📌 Nội Dung Prompt Gốc Đã Sử Dụng

```text
Bạn là Chuyên gia Bảo mật & Kiến trúc sư Backend FastAPI. Hãy tạo skill 'auth-security' cho MoneyMind:

1. Mô tả chi tiết toàn bộ luồng nghiệp vụ:
   - Đăng ký tài khoản, mã hóa Bcrypt, tạo mã OTP 6 số ngẫu nhiên.
   - Gửi OTP kích hoạt qua SMTP Gmail với timeout an toàn.
   - Đăng nhập xác thực, tạo JWT access token (30p) và refresh token (7 ngày).
   - Đổi mật khẩu, quên mật khẩu (Reset Token) và thu hồi phiên.

2. Kiến trúc mã nguồn:
   - Backend: app/controllers/auth_controller.py, app/core/security.py, app/services/email_service.py.
   - Models: NguoiDung, XacNhanOTP, DatLaiMatKhau.
   - Frontend: frontend/js/auth.js, lưu trữ JWT vào localStorage, tự động đính kèm Bearer header.

3. Cơ chế kiểm soát an toàn & Quy tắc nghiệp vụ BR-04:
   - Chống Brute-force OTP (giới hạn 5 lần thử).
   - Kiểm tra trạng thái tài khoản bị khóa/chưa kích hoạt.

4. Hướng dẫn test tự động bằng Pytest và truy vấn SQL kiểm tra thủ công.

Định dạng đầu ra: Chuẩn SKILL.md với YAML frontmatter cho Antigravity AI Agent.
```

---

## 🚀 Hướng Dẫn Tái Tạo Hoặc Cập Nhật Skill Này

Khi muốn nâng cấp skill, gửi prompt:
```text
Hãy đọc các file `app/controllers/auth_controller.py`, `app/core/security.py` và `frontend/js/auth.js`.
Cập nhật file `.agents/skills/auth-security/SKILL.md`:
- Bổ sung cơ chế bảo mật OAuth2 Google Login nếu có.
- Cập nhật các endpoint refresh token xoay vòng (rotating refresh token).
```
