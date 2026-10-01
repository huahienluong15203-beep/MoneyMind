---
name: uml-system-architecture
description: Kỹ năng Thiết kế Kiến trúc và Tự động Sinh Sơ đồ Chuẩn UML (Use Case, Class Diagram, Sequence Diagram, ERD CSDL) bằng Mermaid.js cho MoneyMind.
---

# Kỹ Năng: Thiết Kế & Sinh Sơ Đồ Chuẩn UML (UML Architecture)

Kỹ năng cung cấp bộ tài liệu trực quan hóa toàn diện kiến trúc hệ thống MoneyMind bằng sơ đồ chuẩn UML quốc tế (sử dụng Mermaid.js).

---

## 1. Sơ Đồ Use Case Tổng Thể (System Use Case)

```mermaid
flowchart LR
    User(["👤 Người Dùng"])
    Admin(["👨‍💼 Quản Trị Viên"])
    AI(["🤖 Google Gemini AI"])
    SMTP(["📧 Mail Server SMTP"])

    subgraph MoneyMind ["Hệ Thống Quản Lý Tài Chính MoneyMind"]
        UC1(["Đăng ký & Xác thực OTP"])
        UC2(["Đăng nhập & Quản lý Phiên"])
        UC3(["Quản lý 6 Hũ & Danh mục"])
        UC4(["Ghi nhận Giao dịch Thu/Chi"])
        UC5(["Thiết lập Ngân sách & Cảnh báo"])
        UC6(["Mục tiêu Tiết kiệm & Tích lũy"])
        UC7(["Xem Thống kê & Biểu đồ"])
        UC8(["Trò chuyện & Nhận Báo cáo AI"])
    end

    User --> UC1
    User --> UC2
    User --> UC3
    User --> UC4
    User --> UC5
    User --> UC6
    User --> UC7
    User --> UC8

    UC1 -.-> SMTP
    UC8 -.-> AI
```

---

## 2. Sơ Đồ Thực Thể - CSDL (Entity Relationship Diagram - ERD)

```mermaid
erDiagram
    NGUOI_DUNG ||--o{ DANH_MUC : "sở hữu"
    NGUOI_DUNG ||--o{ GIAO_DICH : "thực hiện"
    NGUOI_DUNG ||--o{ NGAN_SACH : "thiết lập"
    NGUOI_DUNG ||--o{ MUC_TIEU_TIET_KIEM : "đặt mục tiêu"
    NGUOI_DUNG ||--o{ THONG_BAO : "nhận"
    NGUOI_DUNG ||--o{ BAO_CAO_AI : "nhận phân tích"
    DANH_MUC ||--o{ GIAO_DICH : "phân loại"
    DANH_MUC ||--o{ NGAN_SACH : "áp dụng hạn mức"

    NGUOI_DUNG {
        int ma_nd PK
        string email UK
        string mat_khau
        string ho_ten
        string trang_thai
    }

    DANH_MUC {
        int ma_dm PK
        int ma_nd FK
        string ten_dm
        string loai
        string loai_hu
    }

    GIAO_DICH {
        int ma_gd PK
        int ma_nd FK
        int ma_dm FK
        float so_tien
        string loai
        date ngay
    }

    NGAN_SACH {
        int ma_ns PK
        int ma_nd FK
        int ma_dm FK
        int thang
        int nam
        float so_tien_dinh_muc
    }
```

---

## 3. Sơ Đồ Trình Tự (Sequence Diagram): Thêm Giao Dịch & Cảnh Báo

```mermaid
sequenceDiagram
    autonumber
    actor User as Người dùng
    participant UI as Giao diện Web (SPA)
    participant API as GiaoDichController
    participant Svc as NganSachService
    participant DB as SQLite Database

    User->>UI: Điền Form giao dịch (500,000 đ - Ăn uống)
    UI->>API: POST /api/giao-dich/ (Bearer Token)
    API->>API: Xác thực Token & Validate số tiền > 0
    API->>DB: INSERT INTO giao_dich
    API->>Svc: kiem_tra_canh_bao_ngan_sach(ma_nd, ma_dm)
    Svc->>DB: SELECT SUM(so_tien) chi tiêu trong tháng
    DB-->>Svc: Tổng chi = 4,200,000 đ (Định mức 5,000,000 đ = 84%)
    Note over Svc: Vượt ngưỡng 80% (BR-03)
    Svc->>DB: INSERT INTO thong_bao (Mức độ: WARNING)
    Svc-->>API: Trả về alert_info
    API-->>UI: HTTP 201 Created {giao_dich, alert_info}
    UI->>User: Cập nhật số dư & Hiển thị Pop-up Cảnh Báo 84%!
```
