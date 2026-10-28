# 💰 MoneyMind — Hệ Thống Quản Lý Tài Chính Cá Nhân Thông Minh Tích Hợp AI

[![CI/CD Pipeline](https://github.com/huahienluong15203-beep/MoneyMind/actions/workflows/ci.yml/badge.svg)](https://github.com/huahienluong15203-beep/MoneyMind/actions)
[![Test Suite](https://img.shields.io/badge/Pytest-96%2F96%20Passed%20(100%25)-success)](file:///c:/Users/Admin/OneDrive/Desktop/DỰ ÁN LỚN/tests/)
[![Python Version](https://img.shields.io/badge/Python-3.8%20%7C%203.10%20%7C%203.11-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-2.0.0-009688)](https://fastapi.tiangolo.com/)
[![AI Engine](https://img.shields.io/badge/AI%20Engine-Gemini%203.8%20Flash-orange)](https://ai.google.dev/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

Ứng dụng quản lý tài chính cá nhân thông minh kết hợp **Trí tuệ nhân tạo (Google Gemini AI)** giúp tối ưu hóa ngân sách theo phương pháp 6 hũ, lập kế hoạch tiết kiệm tự động hoàn tiền và cảnh báo chi tiêu thông minh theo thời gian thực.

---

## 📚 Hồ Sơ Báo Cáo Kỹ Thuật Đồ Án (Academic Deliverables)

Dự án được xây dựng và tài liệu hóa chuẩn mực, đáp ứng toàn diện các tiêu chí đánh giá môn học (CLO1, CLO2, CLO3, CLO4, CLO5, PLO7):

| Tài liệu / Hồ sơ kỹ thuật | Mô tả chi tiết | Tiêu chí đáp ứng |
| :--- | :--- | :--- |
| 📘 [**Quyển Báo Cáo Kỹ Thuật Đồ Án**](BAO_CAO_DU_AN_MONEYMIND.md) | Báo cáo hoàn chỉnh 7 chương: Phân tích bài toán, SRS chuẩn IEEE 830, CSDL 3NF 12 bảng, Kiến trúc AI, SDLC Factory, Thực nghiệm 96 tests và Đóng gói. | **Tiêu chí 1** (3.0đ) & **Tiêu chí 4** (2.0đ) |
| 📊 [**Thực Nghiệm So Sánh Prompt**](docs/THUC_NGHIEM_SO_SANH_PROMPT.md) | Báo cáo đo lường định lượng so sánh 3 phiên bản Prompt (v1 vs v2 vs v3) trên 60 mẫu thử: Độ chính xác, Latency, Token usage, Hallucination. | **Tiêu chí 3.2** (CLO3, CLO4) |
| 🏭 [**Kiến Trúc AI Agent SDLC Factory**](docs/AI_AGENT_SDLC_FACTORY.md) | Thiết kế hệ thống đa tác tử theo Context Engineering, 18 Skills phân tầng, Rào chắn an toàn 3 lớp và Cơ chế kiểm thử tự động. | **Tiêu chí 2** (Ảnh 1 — 4.0đ) |
| 🧠 [**Minh Chứng Sửa Lỗi AI & Vấn Đáp**](docs/MINH_CHUNG_SUA_LOI_AI_VA_VAN_DAP.md) | Phân tích 4 ca sai sót ảo giác của AI và cách nhóm sửa lỗi, ngân hàng câu hỏi vấn đáp độc lập từng thành viên và các đóng góp sáng tạo riêng. | **Tiêu chí 5** (CLO1, CLO5 — 2.0đ) |
| 🎬 [**Kịch Bản Demo Trực Tiếp (5 Phút)**](docs/KICH_BAN_DEMO.md) | Kịch bản trình diễn mượt mà từng bước: Đăng nhập đơn thiết bị, cảnh báo ngân sách đỏ, tác tử tự hành AI, hoàn tiền tiết kiệm và PWA/Android. | **Tiêu chí 4.4** (Demo thành công) |

---

## 🌟 Tính Năng Nổi Bật

### 1. 📊 Quản Lý Ngân Sách 6 Hũ & Cảnh Báo Real-time
- **Tùy chỉnh danh mục chi tiêu**: Người dùng hoàn toàn chủ động tạo, đổi tên, điều chỉnh hạn mức theo 6 hũ tài chính (NEC, LTSS, EDU, PLAY, FFA, GIVE).
- **Cơ chế tự động kết chuyển ngân sách (Auto Carryover)**: Tự động cộng dồn số dư chưa chi hết của tháng cũ sang tháng mới và cấp bù theo cơ chế thác nước khi có thu nhập mới.
- **Cảnh báo ngưỡng chi tiêu thông minh**: Kích hoạt cảnh báo tức thời trong chu kỳ request (< 300ms) tại các ngưỡng: $\ge 80\%$ (Vàng), $\ge 90\%$ (Cam) và $\ge 100\%$ (Đỏ - Vượt hạn mức).

### 2. 🤖 Trợ Lý Tài Chính Thông Minh (AI Gemini 3.8 Flash)
- **Tác tử tự hành (Autonomous Financial Agent)**: Nhận diện hơn 20 câu lệnh đời thường (*"ăn phở 45k"*, *"tạo hũ du lịch 5tr"*, *"nộp 500k vào hũ"*, *"hôm nay tôi tiêu gì?"*).
- **Phản hồi siêu tốc (< 1.5 giây)**: Tích hợp HTTP Keep-Alive Connection Pooling và Cascade Multi-Model Fallback (Gemini 3.8 Flash $\rightarrow$ 3.5 Flash-Lite $\rightarrow$ Flash-Latest).
- **Bảo mật quyền riêng tư (BR-03)**: Lớp lọc PII Sanitization tự động ẩn danh hóa 100% dữ liệu trước khi gửi sang Google API.
- **Bộ nhớ đệm báo cáo tháng (BR-04)**: Kết quả phân tích được lưu vào Cache DB, xem lại chỉ mất < 50ms, không tốn chi phí gọi lại LLM.

### 3. 🎯 Mục Tiêu Tiết Kiệm & Tự Động Hoàn Tiền (BR-02)
- Thiết lập các mục tiêu tích lũy dài hạn với thanh tiến độ trực quan.
- Nạp tiền tích lũy trực tiếp từ số dư ví chính khả dụng. Tự động gửi thông báo chúc mừng khi đạt 90% và 100%.
- **Bảo toàn dòng tiền**: Khi xóa mục tiêu, hệ thống tự động hoàn trả 100% số tiền đã tích lũy về ví chính.

### 4. 📱 Đa Nền Tảng Kép (PWA & Android Native APK)
- Giao diện **Responsive Mobile-First** mô phỏng khung điện thoại tinh tế trên máy tính và toàn màn hình trên di động.
- **Progressive Web App (PWA)**: Hỗ trợ Service Worker lưu cache offline, cho phép cài đặt trực tiếp lên màn hình chính.
- **Android Studio APK Native Wrapper**: Đóng gói WebView phần cứng tăng tốc với tính năng vuốt để tải lại trang (SwipeRefreshLayout).

### 5. 🔐 Bảo Mật Đa Tầng Cấp Doanh Nghiệp
- Xác thực 2 lớp qua mã **OTP 6 chữ số gửi trực tiếp về Gmail qua SMTP TLS**.
- **Quản lý phiên đơn thiết bị (Single Active Session)**: Tự động đăng xuất (Kickout) các thiết bị cũ khi tài khoản đăng nhập ở nơi khác.
- Khóa tài khoản tự động trong 15 phút khi nhập sai mật khẩu 5 lần (TC-02).
- Mật khẩu băm an toàn 1 chiều bằng thuật toán **Bcrypt Salt Rounds $\ge 12$**.

---

## 🛠 Công Nghệ Sử Dụng

- **Backend**: Python 3.8 - 3.11, FastAPI 2.0, SQLAlchemy 2.0, SQLite (In-Memory cho Test) / PostgreSQL, Uvicorn, Pydantic v2.
- **AI Engine**: Google Gemini API (`gemini-3.8-flash`, `gemini-3.5-flash-lite`), HTTPX Connection Pool.
- **Frontend**: HTML5, Vanilla JavaScript (ES6+ Module), Modern Responsive CSS, Glassmorphism UI, Chart.js, Flatpickr.
- **Mobile Packaging**: Progressive Web App (PWA Service Worker) & Android Studio Native APK (TWA/WebView).
- **Testing & Security**: Pytest (96 test cases), HTTPX TestClient, OWASP SQLi/XSS Fuzzing, Database StaticPool Isolation.
- **DevOps**: Docker, Docker-Compose, GitHub Actions CI/CD Pipeline.

---

## 🚀 Hướng Dẫn Cài Đặt & Chạy Cục Bộ

### 1. Yêu cầu hệ thống
- Python 3.8 trở lên (khuyên dùng Python 3.10 hoặc 3.11).
- Git.

### 2. Cài đặt dự án
```bash
# Clone dự án từ GitHub
git clone https://github.com/huahienluong15203-beep/MoneyMind.git
cd MoneyMind

# Tạo môi trường ảo
python -m venv venv

# Kích hoạt môi trường ảo
# Trên Windows:
.\venv\Scripts\activate
# Trên macOS / Linux:
source venv/bin/activate

# Cài đặt các thư viện phụ thuộc
pip install -r requirements.txt
```

### 3. Cấu hình biến môi trường
Sao chép tệp `.env.example` thành `.env` và cập nhật cấu hình:
```bash
cp .env.example .env
```
Nội dung tệp `.env`:
```env
# Cấu hình bảo mật JWT
SECRET_KEY=CHUOI_BI_MAT_SIEU_CAP_CHO_DO_AN_MONEYMIND_2026
REFRESH_SECRET_KEY=CHUOI_BI_MAT_REFRESH_TOKEN_MONEYMIND_2026

# Cấu hình gửi mail OTP qua Gmail SMTP
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_gmail@gmail.com
SMTP_PASSWORD=your_gmail_app_password
SMTP_FROM_EMAIL=your_gmail@gmail.com

# Cấu hình Google Gemini AI API Key
GEMINI_API_KEY=your_gemini_api_key_here
```

### 4. Khởi chạy ứng dụng
```bash
python main.py
```
Ứng dụng sẽ hoạt động tại địa chỉ: **`http://127.0.0.1:8000`**

### 5. Chạy bộ kiểm thử tự động (Automated Test Suite)
```bash
pytest -v
```
Kết quả kiểm thử: **96/96 passed (100% thành công)**.

### 6. Khởi chạy với Docker
```bash
docker-compose up -d --build
```

---

## 📁 Cấu Trúc Dự Án

```
MoneyMind/
├── .agents/skills/           # 18 Skills chuẩn Context Engineering cho AI Agents
│   ├── ba-requirements-srs/  # Đặc tả yêu cầu SRS & Business Rules BR-01..BR-06
│   ├── ai-financial-advisor/ # Module AI Gemini & 20+ lệnh autonomous
│   ├── ai-testing-agent/     # Fuzzing SQLi/XSS, Boundary Values, BR validation
│   └── PROMPTS.md            # Tổng hợp 13 Prompt gốc dùng trong dự án
├── .github/workflows/        # CI/CD Automation Pipeline (GitHub Actions)
│   └── ci.yml
├── app/                      # Backend Core & MVC Architecture
│   ├── controllers/          # API Routers (auth, giao-dich, ngan-sach, muc-tieu, ai, thong-ke...)
│   ├── core/                 # Config, Database Engine, Security & Lifespan
│   ├── models/               # SQLAlchemy ORM Entities (12 bảng CSDL chuẩn 3NF)
│   ├── schemas/              # Pydantic Schemas v2 & Validation DTOs
│   └── services/             # Business Logic (ai_service, privacy_service, ngan_sach_service...)
├── frontend/                 # Giao diện Web SPA Mobile-First & PWA
│   ├── css/                  # Styling & Responsive Layouts
│   ├── js/                   # 11 modules JavaScript ES6 phân tách chức năng
│   ├── icons/                # Biểu tượng PWA đa kích thước
│   ├── manifest.json         # PWA Manifest khai báo standalone app
│   └── sw.js                 # Service Worker Cache Storage offline
├── android_app/              # Mã nguồn dự án Android Studio Native Wrapper
├── docs/                     # Tài liệu chuyên sâu đáp ứng Rubric chấm điểm
│   ├── THUC_NGHIEM_SO_SANH_PROMPT.md  # Thực nghiệm so sánh prompt v1-v2-v3 (Tiêu chí 3.2)
│   ├── AI_AGENT_SDLC_FACTORY.md       # Thiết kế SDLC Factory 4.0 điểm (Tiêu chí 2)
│   ├── MINH_CHUNG_SUA_LOI_AI_VA_VAN_DAP.md # Minh chứng sửa lỗi AI & Vấn đáp (Tiêu chí 5)
│   └── KICH_BAN_DEMO.md               # Kịch bản demo 5 phút trực tiếp (Tiêu chí 4.4)
├── tests/                    # 96 Automated Tests (Unit, Integration, Security, Boundary)
├── BAO_CAO_DU_AN_MONEYMIND.md# Quyển Báo Cáo Kỹ Thuật Đồ Án Hoàn Chỉnh 7 Chương
├── Dockerfile                # Cấu hình đóng gói container Docker
├── docker-compose.yml        # Điều phối dịch vụ container
├── requirements.txt          # Thư viện phụ thuộc Python
└── main.py                   # Điểm khởi chạy server chính
```

---

## 📄 Giấy Phép & Đóng Góp
Dự án được xây dựng phục vụ mục đích nghiên cứu, học tập và quản lý tài chính cá nhân.  
Mọi đóng góp (Pull Request / Issue) đều được chào đón!
