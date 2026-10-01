# Prompt Tạo Skill: Frontend Test Suite (Playwright E2E)

> **Mục tiêu:** Xây dựng quy trình tự động hóa kiểm thử giao diện người dùng (UI/UX) cho MoneyMind PWA (Single Page Application - Vanilla JS + CSS thuần) bằng Playwright.

---

## 📌 Nội Dung Prompt Gốc Đã Sử Dụng

```text
Bạn là Chuyên gia Kiểm thử Giao diện Tự động (Senior Frontend QA Automation Engineer).
Hãy xây dựng skill 'frontend-test-suite' cho MoneyMind:

1. Đặc thù công nghệ Frontend:
   - Không sử dụng React/Vue/Node.js build step; Frontend là Single Page App thuần (Vanilla JS, HTML5, CSS3, Service Worker PWA).
   - File trung tâm: `frontend/index.html` (89KB), `frontend/js/app.js`, `frontend/js/thong-ke.js`, `frontend/js/ai.js`.
   - Giao diện có Chart.js vẽ biểu đồ canvas và AI Drawer dạng slide-over.

2. Khung kiểm thử:
   - Sử dụng Microsoft Playwright (Python hoặc Node.js Playwright test).
   - Chế độ Headless Browser (Chromium, Firefox, WebKit) cho môi trường CI/CD và Local.

3. Các luồng E2E quan trọng cần kiểm thử:
   - Luồng Đăng ký / Đăng nhập / Lưu JWT vào localStorage / Đăng xuất.
   - SPA Router: Chuyển tab Tổng quan -> Giao dịch -> Ngân sách -> Tiết kiệm -> Thống kê -> Tra cứu không bị reload trang.
   - Thêm giao dịch mới: Điền form modal, validate số tiền âm/0, kiểm tra cập nhật số dư tức thì trên UI.
   - Biểu đồ thống kê: Xác nhận thẻ `<canvas id="chart-...">` được render thành công.
   - Chat AI: Mở drawer AI, gửi tin nhắn, nhận phản hồi bubble và đóng drawer.
   - Responsive & PWA: Test viewport Mobile (iPhone/Pixel) và Tablet, kiểm tra manifest.json.

4. Báo cáo & Video:
   - Chụp màn hình khi test thất bại (Screenshots on failure).
   - Ghi hình video luồng kiểm thử (Playwright video recording).

Định dạng đầu ra: Chuẩn SKILL.md với YAML frontmatter hợp lệ cho Antigravity AI Agent.
```

---

## 🚀 Hướng Dẫn Tái Tạo Hoặc Nâng Cấp Skill Này

Khi muốn yêu cầu AI cập nhật hoặc tái tạo skill này, hãy gửi prompt sau:

```text
Hãy đọc các file trong `frontend/` (đặc biệt là `index.html`, `js/app.js`, `js/auth.js`, `js/giao-dich.js`).
Cập nhật file `.agents/skills/frontend-test-suite/SKILL.md` với:
- Selector chuẩn (ID/data-test-id) khớp chính xác với DOM hiện tại của `frontend/index.html`.
- Kịch bản kiểm thử luồng đồng bộ Service Worker và offline cache.
- Mẫu script Playwright Python hoàn chỉnh có thể chạy ngay bằng `python tests_e2e/run_tests.py`.
```
