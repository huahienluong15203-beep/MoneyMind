# 🧪 PROMPT GUIDE — backend-test-suite

> **Skill:** Bộ Test Tự Động Backend — Pytest + HTTPX  
> **File SKILL:** [SKILL.md](./SKILL.md)  
> **Cập nhật:** 03/10/2026

---

## 📌 PHẦN 1 — PROMPT SINH SKILL (Tạo SKILL.md)

```
Bạn là Senior QA Engineer chuyên Python Pytest + FastAPI Testing.
Hãy tạo file SKILL.md cho skill 'backend-test-suite' trong MoneyMind.

Nội dung bắt buộc:

1. Kiến trúc bộ test (link file):
   - tests/conftest.py — Setup fixtures dùng chung
   - tests/test_nguoi_dung.py — Auth, OTP, JWT
   - tests/test_giao_dich.py — CRUD giao dịch, BR-02
   - tests/test_ngan_sach.py — Ngân sách, BR-03 (12KB test lớn nhất)
   - tests/test_ai.py — AI mocking (xem skill mocking-ai-engine)
   - tests/test_new_requirements.py — BR-01, BR-06
   - tests/test_security_agent.py — SQLi, XSS, IDOR (10KB)

2. conftest.py đầy đủ:
   - Fixture db_session: SQLite in-memory, auto-rollback per test
   - Fixture test_app: override DATABASE_URL
   - Fixture async_client: httpx.AsyncClient với base_url
   - Fixture user_token: tạo user + đăng nhập → trả JWT
   - Fixture authenticated_client: client có Bearer header sẵn

3. Pattern viết test (AAA — Arrange-Act-Assert):
   - Arrange: chuẩn bị data, fixtures
   - Act: gọi API endpoint
   - Assert: kiểm tra status code + response body

4. Danh sách 6 Business Rules cần test:
   - BR-01: Tổng tỷ lệ 6 hũ = 100%
   - BR-02: Số tiền giao dịch > 0
   - BR-03: Cảnh báo ngưỡng 80% và 100%
   - BR-04: Khóa tài khoản sau 5 lần sai OTP
   - BR-05: Ẩn danh hóa dữ liệu trước AI
   - BR-06: Hoàn tiền khi xóa mục tiêu tiết kiệm

5. Lệnh chạy test:
   - Toàn bộ: .\\venv\\Scripts\\pytest tests/ -v --tb=short
   - Một module: .\\venv\\Scripts\\pytest tests/test_giao_dich.py -v
   - Một BR cụ thể: .\\venv\\Scripts\\pytest -k "test_br03" -v
   - Coverage: .\\venv\\Scripts\\pytest tests/ --cov=app --cov-report=term

Định dạng: YAML frontmatter + Markdown, có bảng, code block, link file.
```

---

## 💻 PHẦN 2 — PROMPT TẠO CODE (Thêm Test Cases)

### 2A. Viết Test Case Đầy Đủ Cho BR-03 (Cảnh Báo Ngân Sách)

```
Hãy đọc `.agents/skills/backend-test-suite/SKILL.md` và `.agents/skills/budget-monitoring/SKILL.md`.
Viết test case đầy đủ cho Business Rule BR-03 trong file tests/test_ngan_sach.py.

Các test case cần có:
1. test_canh_bao_0_phan_tram: chi tiêu 0% → không có cảnh báo
2. test_canh_bao_79_phan_tram: chi 79% → không có cảnh báo
3. test_canh_bao_80_phan_tram: chi đúng 80% → cảnh báo WARNING
4. test_canh_bao_99_phan_tram: chi 99% → cảnh báo WARNING
5. test_canh_bao_100_phan_tram: chi đúng 100% → cảnh báo CRITICAL
6. test_canh_bao_vuot_100_phan_tram: chi 150% → cảnh báo CRITICAL
7. test_khong_canh_bao_neu_chua_co_ngan_sach: không có ngân sách → không cảnh báo

Dùng fixtures: authenticated_client, db_session từ conftest.py.
Pattern AAA. Async test với @pytest.mark.asyncio.
```

### 2B. Viết Test Case Cho Security (SQLi & IDOR)

```
Hãy đọc `.agents/skills/backend-test-suite/SKILL.md` và `.agents/skills/ai-testing-agent/SKILL.md`.
Thêm test case bảo mật vào tests/test_security_agent.py.

Test cases cần có:
1. test_sqli_dang_nhap: gửi email = "' OR '1'='1" → HTTP 422 hoặc 401 (không được 200)
2. test_sqli_giao_dich_ghi_chu: ghi_chu = "'; DROP TABLE giao_dich;--" → HTTP 422
3. test_xss_ten_danh_muc: ten_dm = "<script>alert(1)</script>" → lưu an toàn (escaped)
4. test_idor_xem_giao_dich_nguoi_khac: User A xem giao dịch của User B → HTTP 403/404
5. test_idor_xoa_danh_muc_nguoi_khac: User A xóa danh mục của User B → HTTP 403/404
6. test_jwt_gia_mao: gửi JWT tự tạo (sai secret) → HTTP 401
7. test_jwt_het_han: gửi expired JWT → HTTP 401

Mỗi test: rõ ràng docstring giải thích security risk nếu fail.
```

---

## 🗺️ PHẦN 3 — PROMPT SINH SƠ ĐỒ

### 3A. Flowchart — Luồng Chạy Pytest CI/CD

```
Sinh Flowchart (Mermaid.js flowchart TD) cho luồng chạy test CI/CD:

Start: Developer push code lên GitHub
→ GitHub Actions trigger
→ Checkout code
→ Setup Python 3.8
→ pip install -r requirements.txt
→ Chạy pytest tests/ --tb=short -q
→ Kết quả?
  + PASSED: ✅ Deploy lên Render.com
  + FAILED: ❌ Gửi notification → Block deploy → Developer fix

Chi tiết bước pytest:
→ conftest.py setup: tạo SQLite in-memory
→ Chạy 10 test files song song (xdist nếu có)
→ Thu thập coverage report
→ Nếu coverage < 80% → WARN (không block)
→ Cleanup: drop in-memory DB
```

### 3B. Sequence Diagram — Fixture Lifecycle

```
Sinh Sequence Diagram cho lifecycle của fixtures trong một test run:

1. pytest collect test: test_them_giao_dich_thanh_cong
2. pytest setup fixtures (theo thứ tự dependency):
   a. db_session: tạo SQLite :memory: engine, tạo tất cả tables, BEGIN transaction
   b. test_app: override app dependency DATABASE_URL → dùng in-memory DB
   c. async_client: tạo httpx.AsyncClient(app=test_app)
   d. user_token: POST /api/auth/dang-ky (user test) → POST /api/auth/dang-nhap → lấy token
   e. authenticated_client: client với header Authorization: Bearer {token}
3. Chạy test body: authenticated_client.post("/api/giao-dich/", ...)
4. Assert kết quả
5. pytest teardown (ngược thứ tự):
   e. authenticated_client.aclose()
   d. (user_token cleanup không cần)
   c. async_client.aclose()
   b. (test_app reset)
   a. db_session.rollback() → DROP tất cả tables → đóng engine
6. DB in-memory bị hủy hoàn toàn — không ảnh hưởng DB thật

Participant: Pytest, conftest, SQLiteInMemory, FastAPIApp, HTTPXClient, Database
```
