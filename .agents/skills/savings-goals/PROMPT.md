# 🎯 PROMPT GUIDE — savings-goals

> **Skill:** Quản Lý Mục Tiêu Tiết Kiệm & Tích Lũy  
> **File SKILL:** [SKILL.md](./SKILL.md)  
> **Cập nhật:** 03/10/2026

---

## 📌 PHẦN 1 — PROMPT SINH SKILL (Tạo SKILL.md)

```
Bạn là Kỹ sư Backend FastAPI và Chuyên gia Tài chính Cá nhân.
Hãy tạo file SKILL.md cho skill 'savings-goals' trong MoneyMind.

Nội dung bắt buộc:

1. Luồng CRUD mục tiêu tiết kiệm đầy đủ:
   - Tạo: tên mục tiêu, số tiền mục tiêu, hạn chót (ngày)
   - Nộp tiền: trừ so_du_vi ví chính, cộng vào so_tien_hien_tai của mục tiêu
   - Rút tiền: hoàn tiền từ mục tiêu về ví chính
   - Xóa: hoàn TOÀN BỘ so_tien_hien_tai về ví chính + ghi thông báo (BR-06)
   - Tự động đánh dấu "hoàn thành" khi so_tien_hien_tai >= so_tien_muc_tieu

2. Công thức dự báo thời gian hoàn thành:
   - Tính muc_nap_tb_thang = trung bình các lần nạp trong 3 tháng gần nhất
   - con_lai = so_tien_muc_tieu - so_tien_hien_tai
   - thang_du_kien = con_lai / muc_nap_tb_thang (làm tròn lên)
   - ngay_hoan_thanh_du_kien = today + thang_du_kien tháng

3. Kiến trúc (bảng + link file):
   - Backend: app/controllers/muc_tieu_controller.py
   - ORM: app/models/muc_tieu_tiet_kiem.py
     + Cột: ma_mt, ma_nd, ten_mt, so_tien_muc_tieu, so_tien_hien_tai, han_chot, trang_thai (dang_tiet_kiem|hoan_thanh|da_huy)
   - Frontend: frontend/js/tiet-kiem.js
     + Thẻ mục tiêu với thanh tiến trình % + ngày dự kiến

4. Endpoint đầy đủ:
   - POST /api/muc-tieu/ — Tạo mục tiêu
   - GET /api/muc-tieu/ — Danh sách mục tiêu
   - GET /api/muc-tieu/{id} — Chi tiết + lịch sử nạp tiền
   - POST /api/muc-tieu/{id}/nop-tien {so_tien} — Nạp tiền
   - POST /api/muc-tieu/{id}/rut-tien {so_tien} — Rút tiền về ví
   - PUT /api/muc-tieu/{id} — Sửa tên/mục tiêu/hạn chót
   - DELETE /api/muc-tieu/{id} — Xóa + hoàn tiền (BR-06)

5. Câu SQL kiểm tra thủ công

6. Lệnh Pytest: .\\venv\\Scripts\\pytest tests/test_new_requirements.py -k "test_br06" -v

Định dạng: YAML frontmatter + Markdown, có bảng và code block, link file.
```

---

## 💻 PHẦN 2 — PROMPT TẠO CODE (Mở Rộng Tính Năng)

### 2A. Thêm Auto-Save — Nạp Tiền Tự Động Định Kỳ

```
Hãy đọc `.agents/skills/savings-goals/SKILL.md`.
Thêm tính năng "Auto-Save": tự động nạp tiền vào mục tiêu tiết kiệm theo lịch.

Yêu cầu:
- Người dùng cấu hình cho mỗi mục tiêu: so_tien_auto, chu_ky (weekly|monthly), ngay_trong_thang (1-28)
- Model: thêm cột vào muc_tieu_tiet_kiem: auto_save_amount, auto_save_chu_ky, auto_save_ngay, auto_save_active
- Cron job kiểm tra mỗi ngày: tìm auto-save đến hạn → tự nạp
- Nếu ví không đủ: ghi thông báo "Không đủ số dư cho Auto-Save [tên mục tiêu]", bỏ qua lần này
- Khi xóa mục tiêu: tự động hủy lịch auto-save + hoàn tiền (BR-06 giữ nguyên)
- Endpoint: PUT /api/muc-tieu/{id}/auto-save {so_tien, chu_ky, ngay, is_active}
- GET /api/muc-tieu/{id}/lich-su — Lịch sử nạp (thường + auto)
- Frontend tiet-kiem.js: Toggle ⚡ Auto-Save với form cấu hình
```

### 2B. Thêm Chia Sẻ Mục Tiêu (Group Saving)

```
Hãy đọc `.agents/skills/savings-goals/SKILL.md`.
Thêm tính năng "Mục Tiêu Chung" — nhiều người cùng góp vào 1 mục tiêu.

Yêu cầu:
- Model mới: muc_tieu_chung (ma_mt_chung PK, ten, so_tien_muc_tieu, ngay_tao, nguoi_tao FK, ma_pin)
- Model: thanh_vien_mt (ma_mt_chung FK, ma_nd FK, vai_tro: owner|member)
- Endpoint:
  + POST /api/muc-tieu/chung/ — Tạo mục tiêu chung (tạo mã PIN 6 số để mời)
  + POST /api/muc-tieu/chung/tham-gia {ma_pin} — Tham gia qua mã PIN
  + POST /api/muc-tieu/chung/{id}/nop-tien {so_tien} — Mỗi thành viên nạp
  + GET /api/muc-tieu/chung/{id}/thanh-vien — Danh sách + % đóng góp
- Frontend: Hiển thị avatar các thành viên + thanh đóng góp riêng từng người
```

### 2C. Thêm Gợi Ý Mức Nạp Tiền Từ AI

```
Hãy đọc `.agents/skills/savings-goals/SKILL.md` và `.agents/skills/ai-financial-advisor/SKILL.md`.
Thêm tính năng "Gợi Ý AI" cho mức nạp tiền vào mục tiêu.

Khi user xem mục tiêu → nút "Hỏi AI":
- Backend gọi Gemini với context: thu nhập tháng, chi tiêu hiện tại, mục tiêu (số tiền còn lại, hạn chót)
- Ẩn danh qua privacy_service.py trước khi gửi (BR-05)
- AI trả về: mức nạp khuyến nghị/tháng + lý do + timeline
- Endpoint: GET /api/muc-tieu/{id}/goi-y-ai
- Cache 7 ngày vào bảng bao_cao_ai để không gọi lại API tốn phí
- Frontend: Card gợi ý AI với animation loading + nút "Áp dụng ngay"
```

---

## 🗺️ PHẦN 3 — PROMPT SINH SƠ ĐỒ

### 3A. Sequence Diagram — Xóa Mục Tiêu & Hoàn Tiền (BR-06)

```
Sinh Sequence Diagram cho luồng "Xóa Mục Tiêu Tiết Kiệm → Hoàn Tiền Về Ví" (BR-06):

1. User nhấn "Xóa mục tiêu" → Popup xác nhận "Bạn có chắc? [số tiền] sẽ hoàn về ví"
2. Frontend DELETE /api/muc-tieu/{id}
3. MucTieuController xác thực JWT + kiểm tra ma_nd sở hữu mục tiêu (IDOR check)
4. Lấy so_tien_hien_tai = tiền đã tích lũy (ví dụ: 2,000,000đ)
5. Nếu so_tien_hien_tai > 0:
   a. UPDATE nguoi_dung SET so_du_vi = so_du_vi + 2,000,000 (hoàn tiền)
   b. INSERT INTO giao_dich {loai=thu, so_tien=2000000, ghi_chu="Hoàn tiền mục tiêu [tên]"}
   c. INSERT INTO thong_bao "Đã hoàn 2,000,000đ từ mục tiêu [tên] về ví chính"
6. DELETE FROM muc_tieu_tiet_kiem WHERE ma_mt = ?
7. HTTP 200 {so_tien_hoan: 2000000, so_du_vi_moi: X}
8. Frontend cập nhật số dư + hiển thị thông báo xanh "Đã hoàn 2,000,000đ về ví!"

Participant: User, FrontendTietKiemJS, MucTieuController, Database, ThongBaoService
```

### 3B. Flowchart — Vòng Đời Mục Tiêu Tiết Kiệm

```
Sinh Flowchart (Mermaid.js flowchart LR) cho vòng đời mục tiêu tiết kiệm:

Trạng thái:
[Tạo mục tiêu] → dang_tiet_kiem
dang_tiet_kiem → [Nạp tiền] → dang_tiet_kiem (nếu chưa đạt mục tiêu)
dang_tiet_kiem → hoan_thanh (khi so_tien_hien_tai >= so_tien_muc_tieu)
dang_tiet_kiem → [Xóa] → hoàn tiền → da_huy
hoan_thanh → [Xóa] → hoàn tiền → da_huy
hoan_thanh → [Rút toàn bộ] → da_huy (tùy chọn)

Ghi chú:
- Mọi đường dẫn đến da_huy đều phải hoàn tiền về ví (BR-06)
- Auto-Save chỉ hoạt động khi trạng thái = dang_tiet_kiem
```
