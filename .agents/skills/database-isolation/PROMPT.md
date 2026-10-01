# Prompt Tạo Skill: Database Isolation & Test Rollback

> **Mục tiêu:** Tạo quy trình tự động cô lập cơ sở dữ liệu kiểm thử, ngăn ngừa ghi đè hoặc làm bẩn CSDL vận hành (`tai_chinh.db`), tự động hoàn tác sau mỗi test session.

---

## 📌 Nội Dung Prompt Gốc Đã Sử Dụng

```text
Bạn là Kỹ sư Cơ sở dữ liệu và Chuyên gia Kiểm thử Hệ thống (Database Reliability Engineer).
Hãy xây dựng skill 'database-isolation' cho dự án quản lý tài chính MoneyMind:

1. Vấn đề cốt lõi cần giải quyết:
   - Không được phép chạm vào file CSDL thật `tai_chinh.db` khi chạy test.
   - Mỗi test case phải chạy trên môi trường dữ liệu sạch (clean state).
   - Không có hiện tượng rò rỉ dữ liệu giữa các test cases làm sai lệch kết quả (test pollution).

2. Cơ chế kỹ thuật áp dụng:
   - Sử dụng SQLite In-Memory Database: `sqlite:///:memory:`.
   - Kết hợp `StaticPool` của SQLAlchemy để duy trì kết nối in-memory xuyên suốt phiên làm việc.
   - Cơ chế Override Dependency của FastAPI: ghi đè dependency `get_db` bằng `override_get_db`.
   - Vòng đời Fixture: Tạo bảng (`Base.metadata.create_all`) khi bắt đầu test, dọn dẹp (`Base.metadata.drop_all`) khi kết thúc.

3. Hướng dẫn thao tác & debug:
   - Hướng dẫn truy xuất dữ liệu thủ công: Sử dụng SQLite CLI, DB Browser for SQLite, hoặc Python script trực tiếp để kiểm tra dữ liệu thật.
   - Cách kiểm tra rò rỉ CSDL và xác minh tính độc lập của test.

Định dạng đầu ra: Chuẩn SKILL.md với YAML frontmatter hợp lệ cho Antigravity AI Agent.
```

---

## 🚀 Hướng Dẫn Tái Tạo Hoặc Nâng Cấp Skill Này

Khi muốn yêu cầu AI cập nhật hoặc tái tạo skill này, hãy gửi prompt sau:

```text
Hãy kiểm tra file `app/core/database.py` và `tests/conftest.py` trong dự án MoneyMind.
Cập nhật file `.agents/skills/database-isolation/SKILL.md` để đảm bảo:
- Hướng dẫn xử lý migration khi thêm bảng ORM mới vào `app/models/`.
- Cách cấu hình session rollback ở cấp độ hàm (function-level rollback) vs cấp độ session (session-level recreation).
- Cẩm nang cứu hộ dữ liệu nếu vô tình chạy test vào CSDL production.
```
