# 💳 PROMPT GUIDE — transaction-management

> **Skill:** Quản Lý Giao Dịch Thu/Chi & Số Dư Ví  
> **File SKILL:** [SKILL.md](./SKILL.md)  
> **Cập nhật:** 03/10/2026

---

## 📌 PHẦN 1 — PROMPT SINH SKILL (Tạo SKILL.md)

```
Bạn là Kỹ sư Backend chuyên FastAPI & SQLAlchemy.
Hãy tạo file SKILL.md cho skill 'transaction-management' trong MoneyMind.

Nội dung bắt buộc:

1. Luồng nghiệp vụ:
   - Thêm giao dịch CHI: trừ số dư ví → kích hoạt kiểm tra ngân sách → tạo cảnh báo nếu cần
   - Thêm giao dịch THU: cộng số dư ví
   - Sửa giao dịch: hoàn tác delta số tiền cũ → áp delta số tiền mới vào ví
   - Xóa giao dịch: hoàn toàn bộ số tiền về ví

2. Danh sách endpoint đầy đủ:
   - POST /api/giao-dich/ — Thêm giao dịch mới
   - GET /api/giao-dich/ — Lấy danh sách (filter: thang, nam, loai, ma_dm, tu_ngay, den_ngay)
   - GET /api/giao-dich/{id} — Chi tiết 1 giao dịch
   - PUT /api/giao-dich/{id} — Sửa giao dịch
   - DELETE /api/giao-dich/{id} — Xóa giao dịch

3. Schema Pydantic v2:
   - GiaoDichCreate: ma_dm, so_tien, loai (thu|chi), ngay, ghi_chu
   - GiaoDichUpdate: so_tien?, loai?, ngay?, ghi_chu?
   - GiaoDichResponse: thêm ma_gd, ten_dm, loai_hu, ma_nd

4. ORM Model app/models/giao_dich.py — tất cả cột + relationships

5. Quy tắc BR-02: so_tien phải > 0, từ chối HTTP 422 nếu vi phạm

6. Câu SQL tra cứu giao dịch thủ công

7. Lệnh Pytest: .\\venv\\Scripts\\pytest tests/test_giao_dich.py -v

Link đến các file source code thực tế trong dự án.
Định dạng: YAML frontmatter + Markdown, có bảng và code block.
```

---

## 💻 PHẦN 2 — PROMPT TẠO CODE (Mở Rộng Tính Năng)

### 2A. Thêm Giao Dịch Định Kỳ (Recurring Transactions)

```
Hãy đọc `.agents/skills/transaction-management/SKILL.md`.
Thêm tính năng "Giao Dịch Định Kỳ" vào MoneyMind.

Yêu cầu:
- Model mới: app/models/giao_dich_dinh_ky.py
  Cột: ma_gd_dk (PK), ma_nd (FK), ma_dm (FK), so_tien, loai, ghi_chu,
        chu_ky (daily|weekly|monthly), ngay_bat_dau (date), ngay_ket_thuc (date nullable),
        lan_chay_cuoi (datetime), is_active (bool)
- Endpoints:
  + POST /api/giao-dich/dinh-ky/ — Tạo lịch định kỳ
  + GET /api/giao-dich/dinh-ky/ — Danh sách lịch
  + PUT /api/giao-dich/dinh-ky/{id}/toggle — Bật/tắt
  + DELETE /api/giao-dich/dinh-ky/{id} — Xóa lịch
- Background job (FastAPI lifespan + APScheduler): chạy mỗi 1h
  + Tìm các giao dịch định kỳ đến hạn → tự động tạo giao dịch thật
  + Cập nhật lan_chay_cuoi
- Frontend giao-dich.js: Badge "🔄 Định kỳ" cho giao dịch được tạo tự động

Mỗi giao dịch tự động vẫn kích hoạt BR-03 (kiểm tra ngân sách).
Không ảnh hưởng CRUD giao dịch thường.
```

### 2B. Thêm Import Giao Dịch Từ File CSV

```
Hãy đọc `.agents/skills/transaction-management/SKILL.md`.
Thêm tính năng Import giao dịch hàng loạt từ CSV.

Yêu cầu:
- Endpoint: POST /api/giao-dich/import-csv
  + Accept: multipart/form-data với file CSV
  + Column CSV: ngay (DD/MM/YYYY), so_tien, loai (thu|chi), ten_danh_muc, ghi_chu
- Xử lý:
  + Parse CSV với csv.DictReader (Python stdlib)
  + Tự động map ten_danh_muc → ma_dm (case-insensitive, fuzzy match)
  + Nếu không tìm được danh mục → gắn vào "Chưa phân loại" mặc định
  + Validate BR-02 (so_tien > 0) cho từng dòng
  + Bulk insert với SQLAlchemy
  + Trả về: {thanh_cong: N, that_bai: M, chi_tiet_loi: [...]}
- Frontend: Nút "Import CSV" + drag-and-drop + preview 5 dòng đầu trước khi submit
```

### 2C. Thêm Tìm Kiếm & Lọc Nâng Cao

```
Hãy đọc `.agents/skills/transaction-management/SKILL.md`.
Nâng cấp endpoint GET /api/giao-dich/ với tìm kiếm nâng cao:

Query params mới:
- q: tìm trong ghi_chu (LIKE %q%)
- tu_ngay, den_ngay: lọc theo khoảng thời gian (format: YYYY-MM-DD)
- so_tien_tu, so_tien_den: lọc theo khoảng số tiền
- loai_hu: lọc theo hũ (NEC|LTSS|EDU|PLAY|FFA|GIVE)
- page, page_size: phân trang (mặc định page=1, page_size=20)
- sort_by: ngay|so_tien (mặc định: ngay DESC)

Response: {items: [...], total: N, page: P, total_pages: T}
Frontend tra-cuu.js: Form filter với DatePicker, RangSlider số tiền, dropdown hũ
```

---

## 🗺️ PHẦN 3 — PROMPT SINH SƠ ĐỒ

### 3A. Sequence Diagram — Thêm Giao Dịch Chi

```
Sinh Sequence Diagram (Mermaid.js) cho luồng "Thêm Giao Dịch Chi → Cập Nhật Ví → Cảnh Báo":

1. User điền form: 500,000đ — Ăn uống (NEC) — hôm nay
2. Frontend (giao-dich.js) POST /api/giao-dich/ {ma_dm, so_tien:500000, loai:chi, ngay}
3. AuthMiddleware xác thực JWT → lấy ma_nd
4. GiaoDichController validate: so_tien > 0 (BR-02)
5. GiaoDichController: SELECT so_du_vi FROM nguoi_dung WHERE ma_nd = ?
6. Kiểm tra: so_du_vi >= so_tien? Nếu không → HTTP 400 "Không đủ số dư"
7. BEGIN TRANSACTION
8. INSERT INTO giao_dich (ma_nd, ma_dm, so_tien=500000, loai=chi, ngay)
9. UPDATE nguoi_dung SET so_du_vi = so_du_vi - 500000
10. COMMIT
11. GiaoDichController gọi NganSachService.kiem_tra_canh_bao(ma_nd, ma_dm, thang, nam)
12. NganSachService SELECT SUM(chi tháng này) / dinh_muc → = 84%
13. Vượt ngưỡng 80% (BR-03) → INSERT INTO thong_bao (WARNING)
14. HTTP 201 {giao_dich, so_du_vi_moi, alert_info}
15. Frontend cập nhật số dư + hiển thị popup cảnh báo 84%

Participant: User, GiaoDichJS, GiaoDichController, AuthMiddleware, NganSachService, Database
```

### 3B. Flowchart — Logic Sửa Giao Dịch (Hoàn Tác Delta)

```
Sinh Flowchart (Mermaid.js flowchart TD) cho logic "Sửa Giao Dịch — Hoàn Tác Delta":

Nút:
- Bắt đầu: Nhận PUT /api/giao-dich/{id} {so_tien_moi, loai_moi}
- Lấy giao dịch gốc: so_tien_cu, loai_cu
- Tính delta:
  + Nếu loai_cu = chi: hoàn lại so_tien_cu vào ví (cộng)
  + Nếu loai_cu = thu: trừ lại so_tien_cu khỏi ví
- Áp delta mới:
  + Nếu loai_moi = chi: trừ so_tien_moi khỏi ví
  + Nếu loai_moi = thu: cộng so_tien_moi vào ví
- Kiểm tra so_du_vi >= 0? Nếu không → ROLLBACK + HTTP 400
- UPDATE giao_dich + UPDATE so_du_vi → COMMIT
- Kích hoạt kiểm tra ngân sách (BR-03) nếu loai_moi = chi
- HTTP 200 {giao_dich đã cập nhật, so_du_vi_moi}
```
