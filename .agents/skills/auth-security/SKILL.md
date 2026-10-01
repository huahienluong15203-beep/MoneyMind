---
name: auth-security
description: Chức năng Xác thực người dùng, Đăng ký, Đăng nhập JWT (Access/Refresh Token), Mã OTP xác thực email qua SMTP, Quên mật khẩu và Cơ chế Bảo mật tài khoản MoneyMind.
---

# Kỹ Năng: Chức Năng Xác Thực & Bảo Mật Tài Khoản (Auth & Security)

Chức năng cung cấp toàn bộ quy trình nhận diện, xác thực, cấp phát token và bảo vệ danh tính tài khoản người dùng trong hệ thống MoneyMind.

---

## 1. Kiến Trúc & Công Cụ Sử Dụng

| Tầng | Công nghệ / Thư viện | Tệp tin mã nguồn chính |
| :--- | :--- | :--- |
| **Backend API** | FastAPI, OAuth2PasswordBearer | [auth_controller.py](file:///c:/Users/Admin/OneDrive/Desktop/DỰ ÁN LỚN/app/controllers/auth_controller.py) |
| **Bảo mật & Token** | Python-jose (JWT), Passlib (Bcrypt) | [security.py](file:///c:/Users/Admin/OneDrive/Desktop/DỰ ÁN LỚN/app/core/security.py) |
| **Email SMTP** | Python smtplib, email.mime | [email_service.py](file:///c:/Users/Admin/OneDrive/Desktop/DỰ ÁN LỚN/app/services/email_service.py) |
| **Database ORM** | SQLAlchemy 2.0 | [nguoi_dung.py](file:///c:/Users/Admin/OneDrive/Desktop/DỰ ÁN LỚN/app/models/nguoi_dung.py), [xac_nhan_otp.py](file:///c:/Users/Admin/OneDrive/Desktop/DỰ ÁN LỚN/app/models/xac_nhan_otp.py), [dat_lai_mat_khau.py](file:///c:/Users/Admin/OneDrive/Desktop/DỰ ÁN LỚN/app/models/dat_lai_mat_khau.py) |
| **Validate Schema** | Pydantic v2 | [auth.py](file:///c:/Users/Admin/OneDrive/Desktop/DỰ ÁN LỚN/app/schemas/auth.py) |
| **Frontend UI/Logic** | HTML5 Modal, Vanilla JS, LocalStorage | [auth.js](file:///c:/Users/Admin/OneDrive/Desktop/DỰ ÁN LỚN/frontend/js/auth.js) |

---

## 2. Quy Trình Nghiệp Vụ & Xử Lý Logic

1. **Đăng ký tài khoản (Register)**:
   - Nhận `email`, `mat_khau`, `ho_ten`.
   - Kiểm tra email đã tồn tại hay chưa.
   - Băm mật khẩu bằng Bcrypt (`get_password_hash`).
   - Sinh mã ngẫu nhiên OTP 6 chữ số, lưu vào bảng `xac_nhan_otp` với hạn dùng 5 phút.
   - Gửi email OTP kích hoạt tài khoản qua Gmail SMTP.
   - Tài khoản ở trạng thái `chua_kich_hoat` cho đến khi nhập đúng OTP.

2. **Đăng nhập & Cấp phát JWT (Login)**:
   - Endpoint: `/api/auth/dang-nhap`.
   - Xác thực email & mật khẩu (`verify_password`).
   - Kiểm tra trạng thái tài khoản: Nếu tài khoản bị khóa (`khoa`), từ chối đăng nhập (HTTP 403).
   - Tạo cặp token:
     * **Access Token**: Hết hạn sau 30 phút (`ACCESS_TOKEN_EXPIRE_MINUTES`).
     * **Refresh Token**: Hết hạn sau 7 ngày (`REFRESH_TOKEN_EXPIRE_DAYS`).

3. **Bảo vệ chống Brute-Force & Quy tắc khóa (BR-04)**:
   - Sai mã OTP quá 5 lần -> Vô hiệu hóa mã OTP, khóa tạm thời yêu cầu gửi lại.

---

## 3. Truy Xuất & Kiểm Tra CSDL Thủ Công

Mở terminal tại thư mục gốc dự án và chạy lệnh sau để kiểm tra dữ liệu tài khoản:

```bash
# Kiểm tra danh sách người dùng trong CSDL
python -c "import sqlite3; con = sqlite3.connect('tai_chinh.db'); cur = con.cursor(); print(cur.execute('SELECT ma_nd, email, ho_ten, trang_thai FROM nguoi_dung').fetchall()); con.close()"
```

---

## 4. Kiểm Thử Tự Động (Automated Testing)

Chạy bộ test case chuyên biệt cho Module Xác Thực:
```powershell
.env\Scripts\pytest tests/test_nguoi_dung.py -v
```
