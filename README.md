# 💰 MoneyMind - Hệ Thống Quản Lý Tài Chính Cá Nhân Thông Minh Tích Hợp AI

Ứng dụng quản lý tài chính cá nhân toàn diện theo mô hình **6 Hũ Chi Tiêu (Jars Financial System)** kết hợp **Trí tuệ nhân tạo (Google Gemini AI)** giúp tối ưu hóa ngân sách, lập kế hoạch tiết kiệm và cảnh báo chi tiêu thông minh theo thời gian thực.

---

## 🌟 Tính Năng Nổi Bật

### 1. 🏺 Quản Lý Tài Chính Chuẩn Mô Hình 6 Hũ
- **6 Nhóm Ngân Sách**: Thiết yếu (Ăn uống, sinh hoạt), Đầu tư & Tiết kiệm, Giáo dục & Học tập, Hưởng thụ & Giải trí, Cho đi & Thiện nguyện, Dự phòng khẩn cấp.
- Theo dõi dòng tiền thu - chi minh bạch, trực quan theo từng danh mục.
- Cảnh báo vượt ngân sách tự động theo mức phần trăm thời gian thực (≥ 90% và vượt 100%).

### 2. 🤖 Trợ Lý Ảo Tài Chính Thông Minh (AI Gemini)
- Phân tích thói quen chi tiêu hàng tuần, hàng tháng.
- Dự đoán xu hướng tài chính và đưa ra lời khuyên cá nhân hóa.
- Hỗ trợ giải đáp, gợi ý cắt giảm chi phí bất hợp lý.
- Tự động ẩn danh và mã hóa dữ liệu nhạy cảm trước khi xử lý với AI.

### 3. 🎯 Mục Tiêu Tiết Kiệm & Tự Động Hoàn Tiền
- Thiết lập các mục tiêu tiết kiệm dài hạn (Mua sắm, Du lịch, Quỹ khẩn cấp...).
- Tích lũy linh hoạt từ ví chính vào từng mục tiêu.
- Khi xóa mục tiêu, hệ thống tự động hoàn tiền đã nạp về lại ví chính và gửi thông báo minh bạch.

### 4. 📱 Đa Nền Tảng (PWA & Android App)
- Thiết kế chuẩn **Responsive Mobile-First**, giao diện hiện đại, mượt mà.
- Hỗ trợ **Progressive Web App (PWA)** cài đặt trực tiếp.
- Đóng gói **Android Native APK** hỗ trợ chế độ toàn màn hình (Full-Screen) không thanh URL.

### 5. 🔐 Bảo Mật & Xác Thực Nâng Cao
- Xác thực 2 lớp qua mã **OTP gửi trực tiếp về Gmail**.
- Băm mật khẩu an toàn chuẩn công nghiệp (**Passlib/Bcrypt**).
- Quản lý phiên đăng nhập với **JWT (JSON Web Token)**.

---

## 🛠 Công Nghệ Sử Dụng

- **Backend**: Python 3.8+, FastAPI, SQLAlchemy, SQLite/PostgreSQL, Uvicorn, Pydantic.
- **AI Engine**: Google Gemini API (`gemini-1.5-flash` / `gemini-pro`).
- **Frontend**: HTML5, Vanilla JavaScript (ES6+), Modern Responsive CSS, Glassmorphism UI.
- **Mobile Packaging**: Progressive Web Apps (PWA) / Trusted Web Activities (TWA - Android APK).
- **Email Server**: Google SMTP với App Password.

---

## 🚀 Hướng Dẫn Cài Đặt & Chạy Cục Bộ

### 1. Yêu cầu hệ thống
- Python 3.8 trở lên.
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
Sao chép file `.env.example` thành `.env` và điền thông tin:
```bash
cp .env.example .env
```
Nội dung file `.env`:
```env
SMTP_USERNAME=your_gmail@gmail.com
SMTP_PASSWORD=your_gmail_app_password
SMTP_FROM_EMAIL=your_gmail@gmail.com
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

GEMINI_API_KEY=your_gemini_api_key_here
```

### 4. Khởi chạy ứng dụng
```bash
python main.py
```
Ứng dụng sẽ chạy tại địa chỉ: **`http://127.0.0.1:8000`**

---

## 📁 Cấu Trúc Dự Án

```
MoneyMind/
├── app/                      # Backend Core & MVC Architecture
│   ├── controllers/          # API Routers & Endpoints
│   ├── core/                 # Config, Database Engine, JWT & Security
│   ├── models/               # SQLAlchemy ORM Models
│   ├── schemas/              # Pydantic Schemas & Data Validation
│   └── services/             # Business Logic (AI, Ngân Sách, Email...)
├── frontend/                 # Giao diện Web & PWA
│   ├── css/                  # Styling & Responsive Layouts
│   ├── js/                   # Client-side Logic & API Handlers
│   ├── icons/                # App Icons & Screenshots
│   ├── manifest.json         # PWA Web App Manifest
│   └── sw.js                 # Service Worker (Offline Support)
├── android_app/              # Android Wrapper Studio Source Code
├── tests/                    # Automated Unit & Integration Tests
├── .env.example              # Mẫu cấu hình môi trường
├── .gitignore                # Danh sách loại trừ tệp nhạy cảm
├── requirements.txt          # Thư viện Python phụ thuộc
└── main.py                   # Điểm khởi chạy ứng dụng chính
```

---

## 📄 Bản Quyền & Giấy Phép
Dự án được phát triển phục vụ mục đích học tập, nghiên cứu và quản lý tài chính cá nhân.
Mọi đóng góp (Pull Request / Issue) đều được chào đón!
