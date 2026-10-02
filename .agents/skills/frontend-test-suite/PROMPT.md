# 🖥️ PROMPT GUIDE — frontend-test-suite

> **Skill:** Kiểm Thử Giao Diện E2E — Playwright + Pytest  
> **File SKILL:** [SKILL.md](./SKILL.md)  
> **Cập nhật:** 03/10/2026

---

## 📌 PHẦN 1 — PROMPT SINH SKILL (Tạo SKILL.md)

```
Bạn là Senior QA Engineer chuyên E2E Testing với Playwright.
Hãy tạo file SKILL.md cho skill 'frontend-test-suite' trong MoneyMind.
Dự án dùng Vanilla JS ES6+ SPA (không React/Vue/Next.js).

Nội dung bắt buộc:

1. Setup môi trường (lệnh cài đặt):
   pip install playwright pytest-playwright
   playwright install chromium
   playwright install-deps

2. Cấu trúc test E2E:
   tests/e2e/
   ├── conftest.py (fixtures: page, base_url, logged_in_page)
   ├── test_auth_e2e.py (đăng nhập/đăng ký)
   ├── test_giao_dich_e2e.py (thêm/xem giao dịch)
   ├── test_thong_ke_e2e.py (biểu đồ Chart.js render)
   └── test_ai_e2e.py (chat AI)

3. Fixtures Playwright (code block):
   @pytest.fixture(scope="session")
   def browser_context_args(browser_context_args):
       return {**browser_context_args, "base_url": "http://localhost:8000"}

   @pytest.fixture
   async def logged_in_page(page):
       # Đăng nhập qua API → lưu token vào localStorage
       # page.evaluate("localStorage.setItem('access_token', ...)")
       yield page

4. Pattern test E2E SPA:
   - page.goto("/") → page.wait_for_load_state("networkidle")
   - page.locator("#btn-login").click()
   - page.fill("#email-input", "test@example.com")
   - page.wait_for_response("**/api/giao-dich/**") (chờ fetch SPA)
   - expect(page.locator(".so-du-vi")).to_have_text("1,000,000đ")

5. Các kịch bản test E2E chính (9 kịch bản):
   - Đăng nhập thành công → thấy dashboard
   - Đăng nhập sai mật khẩu → thấy thông báo lỗi
   - Thêm giao dịch → số dư cập nhật realtime
   - Xem thống kê → Chart.js render (canvas visible)
   - Mở chat AI → gửi message → nhận reply
   - Tạo ngân sách → thanh tiến trình hiển thị
   - Tạo mục tiêu tiết kiệm → thẻ tiến trình hiển thị
   - Cảnh báo 80% → popup hiển thị đúng
   - Responsive mobile (viewport 375px) → layout không vỡ

6. Lệnh chạy:
   .\\venv\\Scripts\\pytest tests/e2e/ --headed (có giao diện)
   .\\venv\\Scripts\\pytest tests/e2e/ --headless (CI/CD)
   .\\venv\\Scripts\\pytest tests/e2e/ --screenshot=on-failure

Định dạng: YAML frontmatter + Markdown, có code block, link file.
```

---

## 💻 PHẦN 2 — PROMPT TẠO CODE

### 2A. Viết Test E2E Đăng Nhập & Dashboard

```
Hãy đọc `.agents/skills/frontend-test-suite/SKILL.md`.
Viết file tests/e2e/test_auth_e2e.py với test cases E2E.

Test cases:
1. test_dang_nhap_thanh_cong:
   - page.goto("http://localhost:8000")
   - Điền email/mật khẩu → click Đăng nhập
   - Chờ page.wait_for_response("**/api/auth/dang-nhap")
   - Assert: URL vẫn "/" (SPA không reload)
   - Assert: page.locator("#dashboard-section").is_visible()
   - Assert: page.locator(".ten-nguoi-dung").text_content() == "Test User"

2. test_dang_nhap_sai_mat_khau:
   - Điền email đúng + mật khẩu sai
   - Assert: page.locator(".error-toast").is_visible()
   - Assert: .error-toast chứa text "Sai mật khẩu"
   - Assert: dashboard KHÔNG hiển thị

3. test_dang_xuat:
   - Đăng nhập → click nút Đăng xuất
   - Assert: localStorage.getItem('access_token') == null
   - Assert: form đăng nhập visible lại

Dùng fixture logged_in_page cho các test cần trạng thái đã đăng nhập.
Screenshot khi fail: page.screenshot(path=f"artifacts/{test_name}.png")
```

### 2B. Viết Test E2E Thêm Giao Dịch & Cập Nhật Số Dư

```
Hãy đọc `.agents/skills/frontend-test-suite/SKILL.md`.
Viết tests/e2e/test_giao_dich_e2e.py.

Test cases:
1. test_them_giao_dich_chi:
   - Dùng logged_in_page
   - Lấy số dư ban đầu: float(page.locator(".so-du-vi").inner_text().replace(",", "").replace("đ", ""))
   - Click "Thêm giao dịch" → điền form: 50,000đ - Ăn uống - Chi
   - Chờ response POST /api/giao-dich/ → assert 201
   - Assert: số dư giảm đúng 50,000đ
   - Assert: giao dịch mới xuất hiện trong danh sách

2. test_hien_thi_canh_bao_ngan_sach:
   - Setup: tạo ngân sách 100,000đ cho "Ăn uống"
   - Thêm giao dịch 85,000đ (chi)
   - Assert: page.locator(".canh-bao-popup").is_visible()
   - Assert: .canh-bao-popup chứa "85%" hoặc "WARNING"

3. test_chart_thong_ke_render:
   - Mở trang thống kê
   - Chờ page.wait_for_selector("canvas#bieu-do-co-cau")
   - Assert: canvas visible (Chart.js đã render)
   - Assert: canvas.bounding_box().width > 0

Dùng Playwright's expect() assertions với timeout 10s.
```

---

## 🗺️ PHẦN 3 — PROMPT SINH SƠ ĐỒ

### 3A. Flowchart — Luồng Test E2E Với Playwright

```
Sinh Flowchart (Mermaid.js flowchart TD) cho luồng test E2E MoneyMind:

Start: pytest chạy tests/e2e/
→ Setup: khởi động Chromium headless browser
→ Setup fixture logged_in_page:
   a. page.goto("http://localhost:8000")
   b. page.evaluate("localStorage.setItem('access_token', ...)")
   c. page.reload() → SPA nhận token → hiển thị dashboard
→ Chạy test: test_them_giao_dich_chi
   a. page.locator("#btn-them-giao-dich").click()
   b. page.fill("#so-tien", "50000")
   c. page.locator("#btn-luu-giao-dich").click()
   d. page.wait_for_response("**/api/giao-dich/**")
   e. expect(page.locator(".so-du-vi")).to_have_text(...)
→ Thành công? → Tiếp test tiếp theo
→ Thất bại? → page.screenshot() → ghi log → báo cáo
→ Teardown: đóng browser context

Ghi chú: Server FastAPI phải đang chạy trên port 8000 khi chạy E2E test.
```

### 3B. Sequence Diagram — SPA Navigation Trong E2E Test

```
Sinh Sequence Diagram cho cách xử lý SPA Navigation trong Playwright test:

Vấn đề: SPA không reload trang khi điều hướng → cần chờ đúng cách

1. Playwright: page.locator("#nav-thong-ke").click()
2. SPA JavaScript: pushState() → thay đổi URL không reload
3. SPA JavaScript: fetch("/api/thong-ke/tong-quan") (async)
4. Playwright: KHÔNG nên dùng page.wait_for_navigation() (sẽ timeout)
5. Playwright: NÊN dùng:
   a. page.wait_for_response("**/api/thong-ke/**") — chờ fetch hoàn tất
   b. HOẶC: page.wait_for_selector("#section-thong-ke:visible") — chờ element
   c. HOẶC: page.wait_for_load_state("networkidle") — chờ không còn request
6. FastAPI: xử lý request → trả JSON
7. SPA: nhận JSON → render Chart.js
8. Playwright: expect(page.locator("canvas")).to_be_visible() — Assert

Kết luận: Luôn dùng wait_for_response() hoặc wait_for_selector() khi test SPA.

Participant: Playwright, BrowserChromium, SPAJavaScript, FastAPIServer
```
