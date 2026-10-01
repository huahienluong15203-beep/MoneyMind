# Prompt Tạo Skill: Backend Test Suite (Pytest + HTTPX)

> **Mục tiêu:** Tạo bộ hướng dẫn và quy trình tự động hóa kiểm thử Backend cho MoneyMind sử dụng Pytest, HTTPX AsyncClient và SQLAlchemy in-memory.

---

## 📌 Nội Dung Prompt Gốc Đã Sử Dụng

```text
Bạn là Chuyên gia Tự động hóa Kiểm thử Backend (Senior QA/Automation Engineer) và Kiến trúc sư FastAPI/SQLAlchemy.
Hãy xây dựng skill 'backend-test-suite' cho dự án MoneyMind với các tiêu chuẩn sau:

1. Kiến trúc hệ thống:
   - Framework: FastAPI + SQLAlchemy 2.0 ORM + Pydantic v2.
   - Thư viện test: pytest, pytest-asyncio, httpx.
   - CSDL test: SQLite :memory: (StaticPool) tách biệt hoàn toàn với CSDL thật.

2. Cấu trúc bài bản:
   - Giải thích chi tiết fixture conftest.py (client, db_session, test_user, auth_headers).
   - Danh sách các module kiểm thử trọng yếu:
     * test_nguoi_dung.py: Đăng ký, đăng nhập, JWT token, OTP, bảo mật mật khẩu.
     * test_giao_dich.py: CRUD giao dịch thu/chi, xác thực quyền sở hữu (IDOR).
     * test_ngan_sach.py: CRUD ngân sách 6 hũ, kiểm tra cảnh báo vượt hạn mức.
     * test_ai.py: Tích hợp trợ lý Gemini, phân tích chi tiêu, xử lý timeout/mock.
     * test_new_requirements.py: Kiểm tra các quy tắc nghiệp vụ đặc thù (BR-01 đến BR-06).

3. Hướng dẫn thực thi:
   - Các lệnh chạy: chạy toàn bộ, chạy theo file, chạy lọc theo tên hàm (-k), xuất log chi tiết (-v, -s).
   - Cách đọc kết quả kiểm thử (Passed, Failed, Skipped, Warnings).
   - Tích hợp CI/CD pipeline (GitHub Actions).

4. Mở rộng & Bảo trì:
   - Hướng dẫn chuẩn thêm test case mới đúng convention.
   - Checklist nghiệm thu trước khi push code lên production.

Định dạng đầu ra: Chuẩn SKILL.md với YAML frontmatter hợp lệ cho Antigravity AI Agent.
```

---

## 🚀 Hướng Dẫn Tái Tạo Hoặc Nâng Cấp Skill Này

Khi muốn yêu cầu AI cập nhật hoặc tái tạo skill này, hãy gửi prompt sau:

```text
Hãy đọc mã nguồn backend tại thư mục `app/` và các file test tại `tests/` của MoneyMind.
Sau đó cập nhật file `.agents/skills/backend-test-suite/SKILL.md`:
- Bổ sung các fixture mới nhất nếu có thay đổi trong `tests/conftest.py`.
- Đồng bộ danh sách test endpoint với các router mới tại `app/controllers/`.
- Cập nhật các lệnh pytest tối ưu nhất cho môi trường Windows (venv).
```
