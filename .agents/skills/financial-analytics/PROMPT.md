# 📈 PROMPT GUIDE — financial-analytics

> **Skill:** Thống Kê Thu/Chi & Trực Quan Hóa Biểu Đồ Chart.js  
> **File SKILL:** [SKILL.md](./SKILL.md)  
> **Cập nhật:** 03/10/2026

---

## 📌 PHẦN 1 — PROMPT SINH SKILL (Tạo SKILL.md)

```
Bạn là Kỹ sư Backend FastAPI + Chuyên gia Data Visualization (Chart.js).
Hãy tạo file SKILL.md cho skill 'financial-analytics' trong MoneyMind.

Nội dung bắt buộc:

1. Các loại biểu đồ Chart.js hiển thị:
   - Pie Chart: Cơ cấu chi tiêu theo 6 hũ (màu nhất quán với design system)
   - Bar Chart (grouped): So sánh thu/chi theo tháng (12 tháng gần nhất)
   - Line Chart: Xu hướng số dư theo thời gian (tích lũy)
   - Doughnut: % tiến độ từng mục tiêu tiết kiệm

2. Kiến trúc (bảng + link file):
   - Backend: app/controllers/thong_ke_controller.py
   - Frontend: frontend/js/thong-ke.js (35KB, Chart.js instances)

3. Danh sách endpoint:
   - GET /api/thong-ke/tong-quan — Tổng thu, tổng chi, số dư (tháng hiện tại)
   - GET /api/thong-ke/theo-thang?nam=2026 — Breakdown thu/chi 12 tháng
   - GET /api/thong-ke/theo-danh-muc?thang=10&nam=2026 — Cơ cấu 6 hũ
   - GET /api/thong-ke/so-sanh-thang?thang=10&nam=2026 — So sánh tháng này vs tháng trước

4. SQL aggregation queries cho từng endpoint

5. Cách tổ chức Chart.js:
   - Khởi tạo chart trong hàm init()
   - Hàm update(data) để refresh không destroy chart
   - Color palette nhất quán theo 6 hũ: {NEC: #FF6B35, LTSS: #4ECDC4, EDU: #45B7D1, PLAY: #96CEB4, FFA: #FFEAA7, GIVE: #DDA0DD}

6. Lệnh Pytest: .\\venv\\Scripts\\pytest tests/ -k "thong_ke" -v

Định dạng: YAML frontmatter + Markdown, có bảng và code block.
```

---

## 💻 PHẦN 2 — PROMPT TẠO CODE (Mở Rộng Tính Năng)

### 2A. Thêm Biểu Đồ So Sánh Tháng Này vs Tháng Trước

```
Hãy đọc `.agents/skills/financial-analytics/SKILL.md`.
Thêm widget "So Sánh Tháng" vào trang thống kê.

Yêu cầu:
- Endpoint: GET /api/thong-ke/so-sanh-thang?thang=10&nam=2026
- SQL: JOIN 2 tháng (tháng hiện tại và tháng trước), GROUP BY loai_hu
- Response: [{loai_hu, ten_hu, thang_nay: float, thang_truoc: float, bien_dong: float, phan_tram_thay_doi: float}]
- Frontend thong-ke.js:
  + Grouped Bar Chart (Chart.js): Cột xanh = tháng trước, Cột cam = tháng này
  + Trục X: 6 hũ (NEC, LTSS, EDU, PLAY, FFA, GIVE)
  + Tooltip: "Tháng 9: 2,100,000đ → Tháng 10: 2,450,000đ (+16.7% ↑)"
  + Animation: slideInFromBottom 0.6s ease
  + Badge màu đỏ/xanh cho % thay đổi trên mỗi cột

Màu sắc nhất quán với color palette 6 hũ hiện có.
```

### 2B. Thêm Export Báo Cáo PDF/Excel

```
Hãy đọc `.agents/skills/financial-analytics/SKILL.md`.
Thêm tính năng Export báo cáo tài chính.

Yêu cầu:
- Endpoint: GET /api/thong-ke/export?dinh_dang=pdf&thang=10&nam=2026
- Hỗ trợ 2 định dạng:
  + PDF: dùng reportlab (pip install reportlab)
    * Header: Logo MoneyMind + Tên người dùng (ẩn danh theo BR-05 nếu share)
    * Bảng: Tất cả giao dịch tháng (Ngày | Danh mục | Hũ | Loại | Số tiền)
    * Footer: Tổng thu | Tổng chi | Số dư
    * Chart ảnh: Nhúng biểu đồ pie vào PDF
  + Excel: dùng openpyxl (pip install openpyxl)
    * Sheet 1: Tổng quan
    * Sheet 2: Chi tiết giao dịch
    * Sheet 3: Phân tích 6 hũ
- Response: file download với Content-Disposition: attachment
- Frontend: Nút "Xuất PDF" + "Xuất Excel" với loading spinner
```

### 2C. Thêm Heatmap Chi Tiêu Theo Ngày

```
Hãy đọc `.agents/skills/financial-analytics/SKILL.md`.
Thêm Heatmap chi tiêu theo ngày trong tháng (như GitHub contribution heatmap).

Yêu cầu:
- Endpoint: GET /api/thong-ke/heatmap?thang=10&nam=2026
- Response: [{ngay: "2026-10-01", tong_chi: 250000, so_giao_dich: 3}, ...]
- Frontend thong-ke.js:
  + Grid 7 cột (thứ 2 → CN) × N hàng
  + Màu sắc theo mức chi: trắng (0) → xanh nhạt → xanh đậm → cam → đỏ
  + Hover tooltip: "01/10: 250,000đ — 3 giao dịch"
  + Dùng thuần CSS Grid + JavaScript (không cần thư viện ngoài)
```

---

## 🗺️ PHẦN 3 — PROMPT SINH SƠ ĐỒ

### 3A. Flowchart — Luồng Lấy & Render Thống Kê

```
Sinh Flowchart (Mermaid.js flowchart LR) cho luồng tải và hiển thị thống kê:

1. Frontend thong-ke.js: tải trang → gọi đồng thời 3 API:
   - GET /api/thong-ke/tong-quan
   - GET /api/thong-ke/theo-danh-muc?thang=10
   - GET /api/thong-ke/theo-thang?nam=2026
2. ThongKeController xác thực JWT → lấy ma_nd
3. Query DB: GROUP BY loai_hu, thang
4. Response JSON về Frontend
5. Frontend:
   - Render tổng quan: 3 card (Thu | Chi | Số dư)
   - Khởi tạo Pie Chart (cơ cấu 6 hũ)
   - Khởi tạo Bar Chart (thu/chi 12 tháng)
6. User filter → thay đổi tháng/năm → gọi lại API → update chart (không destroy)
```

### 3B. Sequence Diagram — Export PDF Báo Cáo

```
Sinh Sequence Diagram cho luồng "Export PDF Báo Cáo Tài Chính":

1. User click "Xuất PDF" → chọn tháng 10/2026
2. Frontend GET /api/thong-ke/export?dinh_dang=pdf&thang=10&nam=2026
3. ThongKeController xác thực JWT
4. Query DB: lấy tất cả giao dịch tháng + tổng hợp 6 hũ
5. PrivacyService: không ẩn danh (dữ liệu của chính user, không gửi AI)
6. ReportGenerator:
   a. Tạo PDF với reportlab
   b. Nhúng biểu đồ dạng ảnh base64
   c. Ghi bảng giao dịch
7. Trả về StreamingResponse(pdf_bytes, content_type="application/pdf")
8. Browser tự động download: "BaoCao_MoneyMind_10_2026.pdf"

Participant: User, FrontendThongKeJS, ThongKeController, Database, ReportGenerator
```
