# 🔐 PROMPT GUIDE — auth-security

> **Skill:** Xác Thực & Bảo Mật Tài Khoản MoneyMind  
> **File SKILL:** [SKILL.md](./SKILL.md)  
> **Cập nhật:** 03/10/2026

---

## 📌 PHẦN 1 — PROMPT SINH SKILL (Tạo SKILL.md)

> Dùng prompt này để yêu cầu AI tạo hoặc tái tạo file `SKILL.md` từ đầu.

```
Bạn là Chuyên gia Bảo mật & Kiến trúc sư Backend FastAPI.
Hãy tạo file SKILL.md cho skill 'auth-security' trong dự án MoneyMind
(ứng dụng quản lý tài chính Python/FastAPI/SQLite).

Tổng hợp TOÀN BỘ kiến thức về Xác Thực & Bảo Mật tài khoản:

1. Kiến trúc phân tầng (bảng có link file):
   - Backend API: app/controllers/auth_controller.py (FastAPI, OAuth2PasswordBearer)
   - Bảo mật: app/core/security.py (python-jose JWT, passlib Bcrypt)
   - Email SMTP: app/services/email_service.py
   - ORM Models: nguoi_dung.py, xac_nhan_otp.py, dat_lai_mat_khau.py
   - Schema: app/schemas/auth.py (Pydantic v2)
   - Frontend: frontend/js/auth.js (localStorage JWT, Bearer header)

2. Quy trình nghiệp vụ đầy đủ:
   - Đăng ký: email + bcrypt hash + OTP 6 số → gửi Gmail SMTP → trạng thái chua_kich_hoat
   - Kích hoạt: xác nhận OTP (hạn 5 phút) → đổi trạng thái kich_hoat
   - Đăng nhập: xác thực → tạo Access Token (30 phút) + Refresh Token (7 ngày)
   - Quên mật khẩu: gửi Reset Token → đặt lại mật khẩu mới
   - BR-04: Sai OTP > 5 lần → khóa tài khoản, yêu cầu gửi lại

3. Danh sách endpoint API (method, path, mô tả ngắn):
   - POST /api/auth/dang-ky
   - POST /api/auth/xac-nhan-otp
   - POST /api/auth/gui-lai-otp
   - POST /api/auth/dang-nhap
   - POST /api/auth/lam-moi-token
   - POST /api/auth/quen-mat-khau
   - POST /api/auth/dat-lai-mat-khau

4. Câu SQL kiểm tra thủ công người dùng trong CSDL

5. Lệnh Pytest chạy test module xác thực:
   .\\venv\\Scripts\\pytest tests/test_nguoi_dung.py -v

Định dạng đầu ra: YAML frontmatter + Markdown chuẩn.
Có bảng, code block, link file thực tế trong dự án.
```

---

## 💻 PHẦN 2 — PROMPT TẠO CODE (Mở Rộng Tính Năng)

> Dùng các prompt này khi cần AI sinh code mới dựa vào kiến trúc auth hiện có.

### 2A. Thêm Đăng Nhập Google OAuth2

```
Hãy đọc file `.agents/skills/auth-security/SKILL.md` để nắm kiến trúc xác thực.
Sau đó thêm tính năng Đăng nhập Google OAuth2 vào MoneyMind.

Yêu cầu cụ thể:
- Endpoint: GET /api/auth/google/login → redirect đến Google OAuth consent screen
- Endpoint: GET /api/auth/google/callback → nhận authorization code, lấy user info
- Nếu email chưa có trong DB: tạo tài khoản mới (trang thái kich_hoat, bỏ qua OTP)
- Nếu email đã tồn tại: liên kết provider_google vào tài khoản hiện có
- Tạo cặp JWT (access + refresh) giống hệt luồng đăng nhập thường
- Thư viện: pip install authlib httpx
- Frontend auth.js: thêm nút "Đăng nhập với Google" với icon SVG

Giữ TOÀN BỘ code hiện tại, chỉ thêm mới.
Dự án dùng: FastAPI + SQLAlchemy 2.0 + Pydantic v2 + SQLite.
```

### 2B. Thêm Rotating Refresh Token

```
Hãy đọc `.agents/skills/auth-security/SKILL.md`.
Nâng cấp cơ chế refresh token thành Rotating Refresh Token:

- Mỗi lần dùng refresh token → tạo refresh token MỚI + vô hiệu hóa token cũ
- Lưu danh sách refresh token vào bảng mới: refresh_token (token, ma_nd FK, het_han, da_dung)
- Nếu dùng refresh token đã bị thu hồi → khóa toàn bộ phiên của user đó (detect token theft)
- Endpoint: POST /api/auth/lam-moi-token (cập nhật logic hiện có)

Đảm bảo backward-compatible với frontend auth.js hiện tại.
```

### 2C. Thêm Xác Thực 2 Yếu Tố (2FA TOTP)

```
Hãy đọc `.agents/skills/auth-security/SKILL.md`.
Thêm tính năng 2FA bằng Google Authenticator (TOTP):

- Thư viện: pip install pyotp qrcode pillow
- Người dùng bật 2FA: GET /api/auth/2fa/setup → trả về QR code base64
- Xác nhận bật: POST /api/auth/2fa/enable {totp_code}
- Đăng nhập khi có 2FA: sau bước xác thực email/mật khẩu → POST /api/auth/2fa/verify {totp_code}
- Backup codes: 8 mã dùng một lần khi mất thiết bị
- Thêm cột vào bảng nguoi_dung: totp_secret, is_2fa_enabled

Không phá vỡ luồng đăng nhập hiện tại cho user không dùng 2FA.
```

---

## 🗺️ PHẦN 3 — PROMPT SINH SƠ ĐỒ

> Dùng các prompt này để yêu cầu AI sinh sơ đồ kỹ thuật cho module Auth.

### 3A. Sequence Diagram — Đăng Ký & Kích Hoạt OTP

```
Sinh Sequence Diagram (Mermaid.js sequenceDiagram) cho luồng:
"Người dùng Đăng Ký → Nhận OTP → Kích Hoạt Tài Khoản" trong MoneyMind.

Chi tiết từng bước (có autonumber):
1. User điền form (email, mật khẩu, họ tên) → click Đăng ký
2. Frontend (auth.js) gọi POST /api/auth/dang-ky
3. AuthController kiểm tra email đã tồn tại chưa → HTTP 409 nếu trùng
4. Hash mật khẩu với bcrypt (cost factor 12)
5. INSERT INTO nguoi_dung (trang_thai = 'chua_kich_hoat')
6. Sinh mã OTP 6 chữ số ngẫu nhiên
7. INSERT INTO xac_nhan_otp (ma_otp, het_han = now + 5 phút, so_lan_sai = 0)
8. EmailService gửi email OTP qua Gmail SMTP TLS Port 587
9. HTTP 201 → Frontend hiển thị form nhập OTP
10. User nhập OTP → POST /api/auth/xac-nhan-otp
11. AuthController: kiểm tra còn hạn? đúng mã? so_lan_sai < 5?
12. Nếu sai: tăng so_lan_sai; nếu >= 5 → HTTP 423 Locked
13. Nếu đúng: UPDATE nguoi_dung SET trang_thai = 'kich_hoat'
14. HTTP 200 → Frontend tự động đăng nhập → Tạo JWT

Participant: User, FrontendAuthJS, AuthController, Database, EmailService, GmailSMTP
```

### 3B. Sequence Diagram — Đăng Nhập & JWT Refresh

```
Sinh Sequence Diagram cho luồng "Đăng Nhập & Làm Mới Token" trong MoneyMind.

Luồng:
1. User nhập email + mật khẩu → POST /api/auth/dang-nhap
2. AuthController: SELECT user WHERE email = ?
3. Kiểm tra trang_thai: 'khoa' → HTTP 403; 'chua_kich_hoat' → HTTP 403
4. verify_password (bcrypt compare)
5. Nếu sai: HTTP 401 Unauthorized
6. Nếu đúng: tạo Access Token JWT (exp: 30 phút)
7. Tạo Refresh Token JWT (exp: 7 ngày)
8. HTTP 200 {access_token, refresh_token, token_type: "bearer"}
9. Frontend lưu vào localStorage
--- (30 phút sau) ---
10. API call thất bại HTTP 401
11. Frontend tự động gọi POST /api/auth/lam-moi-token {refresh_token}
12. AuthController xác thực Refresh Token signature + exp
13. Tạo Access Token mới
14. HTTP 200 {access_token mới}
15. Frontend retry request gốc với token mới

Participant: User, FrontendAuthJS, AuthController, Database
```

### 3C. State Diagram — Trạng Thái Tài Khoản

```
Sinh State Diagram (Mermaid.js stateDiagram-v2) cho vòng đời trạng thái tài khoản người dùng MoneyMind:

Các trạng thái:
- [*] → chua_kich_hoat: Khi đăng ký thành công
- chua_kich_hoat → kich_hoat: Xác nhận OTP đúng trong 5 phút
- chua_kich_hoat → [*]: OTP hết hạn, tài khoản tự xóa sau 24h
- kich_hoat → khoa: Sai OTP quá 5 lần (BR-04)
- khoa → kich_hoat: Admin mở khóa hoặc người dùng gửi lại OTP xác thực
- kich_hoat → dat_lai_mat_khau: Nhấn quên mật khẩu
- dat_lai_mat_khau → kich_hoat: Đổi mật khẩu thành công (trong 15 phút)

Ghi chú trạng thái: Dùng note right of cho mỗi trạng thái.
```
