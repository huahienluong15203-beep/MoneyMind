# 🗺️ PROMPT GUIDE — uml-system-architecture

> **Skill:** Thiết Kế Kiến Trúc & Sinh Sơ Đồ UML Mermaid.js  
> **File SKILL:** [SKILL.md](./SKILL.md)  
> **Cập nhật:** 03/10/2026

---

## 📌 PHẦN 1 — PROMPT SINH SKILL (Tạo SKILL.md)

```
Bạn là Lead Software Architect & UML Specialist.
Hãy tạo file SKILL.md cho skill 'uml-system-architecture' trong MoneyMind.

Skill PHẢI CHỨA SƠ ĐỒ THỰC TẾ render được bằng Mermaid.js.
Tất cả code mermaid phải hợp lệ và render được trực tiếp trong GitHub Markdown.

Danh sách sơ đồ bắt buộc:

1. Use Case Diagram (flowchart LR):
   - Actor: Người Dùng, Google Gemini AI, Gmail SMTP
   - 9 Use Case trong subgraph MoneyMind
   - Quan hệ: User với 9 UC; UC1 -.-> SMTP; UC8 -.-> Gemini

2. ERD (erDiagram):
   - 8 bảng: nguoi_dung, danh_muc, giao_dich, ngan_sach, muc_tieu_tiet_kiem, thong_bao, bao_cao_ai, xac_nhan_otp
   - Đầy đủ: cột quan trọng (PK, FK, type), tên quan hệ tiếng Việt, multiplicity

3. Sequence Diagram 1 — Thêm Giao Dịch → Cảnh Báo (sequenceDiagram, autonumber):
   - 14 bước từ User điền form đến popup cảnh báo 84%
   - Participant: User, FrontendSPA, GiaoDichController, NganSachService, Database, ThongBaoService

4. Sequence Diagram 2 — AI Chat → Autonomous Action → UI Refresh:
   - 15 bước từ User gõ text đến auto-refresh giao diện
   - Participant: User, ChatUI, AIController, PrivacyService, AIService, GeminiAPI, Database

5. Class Diagram (classDiagram):
   - 7 ORM classes với thuộc tính + kiểu dữ liệu
   - Quan hệ multiplicity (1 → 0..*)

Lưu ý: KHÔNG dùng ký tự tiếng Việt có dấu bên trong code Mermaid (dùng label ASCII).
Định dạng: YAML frontmatter + Markdown.
```

---

## 💻 PHẦN 2 — PROMPT TẠO CODE (Sơ Đồ Cụ Thể)

### 2A. Sinh Class Diagram Toàn Bộ ORM Models

```
Hãy đọc `.agents/skills/uml-system-architecture/SKILL.md`.
Sinh Class Diagram Mermaid.js (classDiagram) đầy đủ cho tất cả ORM Models MoneyMind.

Classes cần có (đọc từ app/models/):
- NguoiDung: +ma_nd int PK, +email str UK, +mat_khau str, +ho_ten str, +trang_thai str, +so_du_vi float
- DanhMuc: +ma_dm int PK, +ma_nd int FK, +ten_dm str, +loai str, +loai_hu str, +bieu_tuong str, +mau_sac str
- GiaoDich: +ma_gd int PK, +ma_nd int FK, +ma_dm int FK, +so_tien float, +loai str, +ngay date, +ghi_chu str
- NganSach: +ma_ns int PK, +ma_nd int FK, +ma_dm int FK, +thang int, +nam int, +so_tien_dinh_muc float
- MucTieuTietKiem: +ma_mt int PK, +ma_nd int FK, +ten_mt str, +so_tien_muc_tieu float, +so_tien_hien_tai float, +trang_thai str
- ThongBao: +id int PK, +ma_nd int FK, +tieu_de str, +noi_dung str, +loai str, +da_doc bool
- BaoCaoAI: +id int PK, +ma_nd int FK, +thang int, +nam int, +noi_dung text
- XacNhanOTP: +id int PK, +ma_nd int FK, +ma_otp str, +het_han datetime, +so_lan_sai int

Quan hệ với multiplicity:
NguoiDung "1" --> "0..*" DanhMuc
NguoiDung "1" --> "0..*" GiaoDich
NguoiDung "1" --> "0..*" NganSach
NguoiDung "1" --> "0..*" MucTieuTietKiem
NguoiDung "1" --> "0..*" ThongBao
NguoiDung "1" --> "0..*" BaoCaoAI
NguoiDung "1" --> "0..*" XacNhanOTP
DanhMuc "1" --> "0..*" GiaoDich
DanhMuc "1" --> "0..*" NganSach

Đầu ra: Mermaid.js classDiagram hoàn chỉnh, copy-paste được.
```

### 2B. Sinh Deployment Architecture Diagram

```
Hãy đọc `.agents/skills/uml-system-architecture/SKILL.md`.
Sinh Deployment Architecture Diagram (Mermaid.js flowchart TB) cho MoneyMind.

5 tầng (dùng subgraph):

[Client Layer]
- Web Browser: SPA (index.html + Vanilla JS ES6+)
- Android APK: TWA Wrapper (fullscreen, no URL bar)
- PWA: Service Worker (offline support, cache API responses)

[API Gateway Layer — FastAPI Port 8000]
- JWT Auth Middleware (python-jose)
- Pydantic v2 Request Validation
- 9 API Routers (auth|danh-muc|giao-dich|ngan-sach|muc-tieu|thong-ke|ai|nguoi-dung|thong-bao)

[Business Logic Layer]
- AIService (135KB): Gemini integration + Autonomous Agent
- NganSachService (43KB): Budget monitoring + BR-03
- EmailService (15KB): OTP via Gmail SMTP
- PrivacyService (7KB): Data anonymization (BR-05)

[Data Layer]
- SQLite tai_chinh.db: Development local
- PostgreSQL: Production (Render.com cloud)

[External Services]
- Google Gemini API (gemini-2.5-flash, cascade fallback)
- Gmail SMTP (Port 587, TLS, App Password)

Mũi tên thể hiện data flow. Ghi chú protocol trên mũi tên.
```

### 2C. Sinh Component Diagram Kiến Trúc MVC

```
Hãy đọc `.agents/skills/uml-system-architecture/SKILL.md`.
Sinh Component Diagram (Mermaid.js flowchart LR) thể hiện kiến trúc MVC của MoneyMind.

Components:

Frontend (SPA):
- auth.js → Quản lý đăng nhập/đăng ký
- app.js → Router điều hướng SPA
- giao-dich.js → UI giao dịch
- thong-ke.js → Chart.js biểu đồ
- ai.js → Chat AI drawer

Backend MVC:
- Controllers layer: nhận HTTP request, validate, trả response
- Services layer: business logic, rule enforcement
- Models layer: ORM SQLAlchemy, CSDL mapping

External:
- Gemini API
- Gmail SMTP

Luồng: Frontend → HTTPS → Controllers → Services → Models → SQLite/PostgreSQL
                                       ↓
                              External Services (Gemini, Gmail)
```

---

## 🗺️ PHẦN 3 — PROMPT SINH SƠ ĐỒ

### 3A. Use Case Diagram Tổng Thể

```
Sinh Use Case Diagram (Mermaid.js flowchart LR) cho toàn bộ hệ thống MoneyMind.

Actors:
- NguoiDung (Người Dùng)
- GeminiAI (Google Gemini AI)
- GmailSMTP (Gmail SMTP Server)

9 Use Cases trong subgraph MoneyMind:
UC1: Dang ky & Xac thuc OTP
UC2: Dang nhap & Quan ly Phien JWT
UC3: Quan ly 6 Hu & Danh muc
UC4: Ghi nhan Giao dich Thu Chi
UC5: Ngan sach & Canh bao 80-100%
UC6: Muc tieu Tiet kiem & Tich luy
UC7: Thong ke & Bieu do Chart.js
UC8: Chat AI & Bao cao Thang
UC9: Cai dat PWA & Android APK

Quan hệ:
NguoiDung --> UC1..UC9 (tất cả)
UC1 -.->|Gui OTP| GmailSMTP
UC8 -.->|API Call| GeminiAI

Dùng style để highlight UC8 (màu đặc biệt vì tích hợp AI).
```

### 3B. ERD Đầy Đủ 8 Bảng

```
Sinh ERD (Mermaid.js erDiagram) cho 8 bảng CSDL MoneyMind.

Bảng và cột (chỉ cột quan trọng):
NGUOI_DUNG: ma_nd PK, email UK, mat_khau, ho_ten, trang_thai, so_du_vi
DANH_MUC: ma_dm PK, ma_nd FK, ten_dm, loai, loai_hu, bieu_tuong, mau_sac
GIAO_DICH: ma_gd PK, ma_nd FK, ma_dm FK, so_tien, loai, ngay, ghi_chu
NGAN_SACH: ma_ns PK, ma_nd FK, ma_dm FK, thang, nam, so_tien_dinh_muc
MUC_TIEU_TIET_KIEM: ma_mt PK, ma_nd FK, ten_mt, so_tien_muc_tieu, so_tien_hien_tai, trang_thai
THONG_BAO: id PK, ma_nd FK, tieu_de, noi_dung, loai, da_doc
BAO_CAO_AI: id PK, ma_nd FK, thang, nam, noi_dung
XAC_NHAN_OTP: id PK, ma_nd FK, ma_otp, het_han, so_lan_sai

Quan hệ (tên bằng tiếng Việt phiên âm không dấu):
NGUOI_DUNG ||--o{ DANH_MUC : "so huu"
NGUOI_DUNG ||--o{ GIAO_DICH : "thuc hien"
NGUOI_DUNG ||--o{ NGAN_SACH : "thiet lap"
NGUOI_DUNG ||--o{ MUC_TIEU_TIET_KIEM : "dat muc tieu"
NGUOI_DUNG ||--o{ THONG_BAO : "nhan"
NGUOI_DUNG ||--o{ BAO_CAO_AI : "nhan phan tich"
NGUOI_DUNG ||--o{ XAC_NHAN_OTP : "xac thuc"
DANH_MUC ||--o{ GIAO_DICH : "phan loai"
DANH_MUC ||--o{ NGAN_SACH : "ap dung han muc"
```

### 3C. Sequence Diagram — Đăng Nhập JWT Đầy Đủ

```
Sinh Sequence Diagram (Mermaid.js, autonumber) cho luồng đăng nhập và sử dụng JWT:

Participant: User, FrontendAuthJS, AuthController, Database

1. User nhap email + mat khau
2. FrontendAuthJS → POST /api/auth/dang-nhap {email, mat_khau}
3. AuthController: SELECT nguoi_dung WHERE email=?
4. Kiem tra trang_thai: khoa → HTTP 403
5. verify_password(mat_khau, hash) → sai → HTTP 401
6. Tao Access Token (exp 30p) + Refresh Token (exp 7 ngay)
7. HTTP 200 {access_token, refresh_token}
8. FrontendAuthJS: luu localStorage
9. (30 phut sau) API call → HTTP 401 Token expired
10. FrontendAuthJS → POST /api/auth/lam-moi-token {refresh_token}
11. AuthController: verify refresh_token signature + exp
12. Tao access_token moi
13. HTTP 200 {access_token}
14. FrontendAuthJS: retry request goc voi token moi
```
