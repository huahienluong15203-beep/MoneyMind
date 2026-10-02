# 🏺 PROMPT GUIDE — six-jars-category

> **Skill:** Quản Lý Danh Mục & Phương Pháp 6 Hũ Tài Chính  
> **File SKILL:** [SKILL.md](./SKILL.md)  
> **Cập nhật:** 03/10/2026

---

## 📌 PHẦN 1 — PROMPT SINH SKILL (Tạo SKILL.md)

```
Bạn là Chuyên gia Cố vấn Tài chính Cá nhân (CFP) và Kỹ sư Backend FastAPI.
Hãy tạo file SKILL.md cho skill 'six-jars-category' trong MoneyMind.

Nội dung bắt buộc:

1. Bảng công thức 6 Hũ Kinh Điển của T. Harv Eker:
   | Ký hiệu | Tên Hũ | Tỷ lệ | Mục đích |
   - NEC (Necessities): 55% — Ăn uống, thuê nhà, sinh hoạt thiết yếu
   - LTSS (Long-term savings): 10% — Quỹ khẩn cấp, mua nhà/xe
   - EDU (Education): 10% — Sách, khóa học, phát triển bản thân
   - PLAY (Play): 10% — Du lịch, giải trí, nhà hàng sang
   - FFA (Financial Freedom): 10% — Đầu tư chứng khoán, bất động sản
   - GIVE (Give): 5% — Từ thiện, quà biếu cha mẹ

2. Quy tắc nghiệp vụ BR-01: Tổng tỷ lệ 6 hũ phải = 100% (validation cứng)

3. Kiến trúc mã nguồn (bảng + link file):
   - Backend: app/controllers/danh_muc_controller.py
     + GET /api/danh-muc/ — Lấy danh sách danh mục & hũ
     + POST /api/danh-muc/ — Tạo danh mục gắn với 1 trong 6 hũ
     + PUT /api/danh-muc/{id} — Sửa tên, màu, icon
     + DELETE /api/danh-muc/{id} — Xóa (chỉ khi không có giao dịch)
   - ORM: app/models/danh_muc.py
     + Cột: ma_dm (PK), ma_nd (FK), ten_dm, loai (thu|chi), loai_hu (NEC|LTSS|EDU|PLAY|FFA|GIVE), bieu_tuong, mau_sac
   - Frontend: frontend/js/danh-muc.js
     + Render 6 thẻ hũ với màu nhận diện riêng và thanh tiến trình chi tiêu

4. Câu SQL kiểm tra danh mục thủ công

5. Lệnh Pytest: .\\venv\\Scripts\\pytest tests/test_new_requirements.py -k "test_br01" -v

Định dạng: YAML frontmatter + Markdown. Có bảng, code block, link file.
```

---

## 💻 PHẦN 2 — PROMPT TẠO CODE (Mở Rộng Tính Năng)

### 2A. Thêm Phân Bổ Thu Nhập Tự Động Theo 6 Hũ

```
Hãy đọc `.agents/skills/six-jars-category/SKILL.md` để nắm kiến trúc danh mục.
Thêm tính năng "Phân Bổ Thu Nhập Tự Động" vào MoneyMind.

Khi người dùng ghi nhận một khoản thu nhập:
- Endpoint mới: POST /api/danh-muc/phan-bo-tu-dong
  Body: {so_tien_thu_nhap: float, ghi_chu: str}
- Tự động tính số tiền cho từng hũ theo tỷ lệ của người dùng
- Tạo 6 bản ghi giao dịch thu riêng cho từng hũ (bulk insert)
- Response: danh sách {loai_hu, so_tien, phan_tram}%
- Frontend danh-muc.js: Nút "Phân bổ ngay" khi thêm giao dịch loại=thu
- Popup xác nhận: "NEC: +2,750,000đ | LTSS: +500,000đ | ..."

Đảm bảo giữ nguyên BR-01 (tổng = 100%).
Dùng SQLAlchemy bulk insert cho hiệu suất tốt.
```

### 2B. Thêm Tùy Chỉnh Tỷ Lệ Hũ Theo Giai Đoạn

```
Hãy đọc `.agents/skills/six-jars-category/SKILL.md`.
Thêm tính năng "Giai Đoạn Tài Chính" để tùy chỉnh tỷ lệ hũ:

- Model mới: giai_doan_tai_chinh (ma_nd FK, ten_giai_doan, nec_pct, ltss_pct, edu_pct, play_pct, ffa_pct, give_pct)
- Validation: tổng 6 tỷ lệ phải = 100 (BR-01 giữ nguyên)
- Preset có sẵn: Sinh viên (NEC 65%, EDU 20%, ...) | Gia đình (NEC 60%, LTSS 15%, ...)
- Endpoint: POST /api/danh-muc/giai-doan {ten, nec_pct, ltss_pct, edu_pct, play_pct, ffa_pct, give_pct}
- Frontend: Modal chọn giai đoạn với slider % cho từng hũ, preview realtime tổng

Constraint: Không thể lưu nếu tổng != 100%.
```

### 2C. Thêm Màu Sắc & Icon Tùy Chỉnh Cho Hũ

```
Hãy đọc `.agents/skills/six-jars-category/SKILL.md`.
Nâng cấp UI quản lý danh mục với bộ chọn màu và icon:

- Backend PUT /api/danh-muc/{id}: cho phép cập nhật mau_sac (hex color) và bieu_tuong (emoji/icon code)
- Validate mau_sac: phải là hex hợp lệ (#RRGGBB)
- Frontend danh-muc.js:
  + Color picker (native HTML5 <input type="color">)
  + Emoji picker với 50+ icon tài chính phổ biến
  + Preview card thay đổi realtime
- Đảm bảo màu sắc nhất quán giữa: thẻ hũ, biểu đồ Chart.js và thanh tiến trình
```

---

## 🗺️ PHẦN 3 — PROMPT SINH SƠ ĐỒ

### 3A. Flowchart — Luồng Phân Bổ 6 Hũ

```
Sinh Flowchart (Mermaid.js flowchart LR) mô tả luồng phân bổ thu nhập vào 6 hũ trong MoneyMind.

Các nút:
- Thu nhập đầu vào (số tiền X)
- Kiểm tra tỷ lệ 6 hũ: tổng = 100%? (BR-01)
- Nếu không → báo lỗi "Tổng tỷ lệ phải = 100%"
- Nếu có → tính tiền từng hũ:
  + NEC = X * 55% → giao dịch thu NEC
  + LTSS = X * 10% → giao dịch thu LTSS
  + EDU = X * 10% → giao dịch thu EDU
  + PLAY = X * 10% → giao dịch thu PLAY
  + FFA = X * 10% → giao dịch thu FFA
  + GIVE = X * 5% → giao dịch thu GIVE
- Cập nhật số dư ví chính
- Hiển thị popup tóm tắt phân bổ
```

### 3B. Pie Chart — Tỷ Lệ Phân Bổ 6 Hũ

```
Sinh Pie Chart (Mermaid.js pie) thể hiện tỷ lệ phân bổ mặc định của 6 hũ MoneyMind:

title Phân Bổ Thu Nhập Chuẩn — Phương Pháp 6 Hũ T. Harv Eker
"NEC — Thiết Yếu" : 55
"LTSS — Tiết Kiệm" : 10
"EDU — Giáo Dục" : 10
"PLAY — Hưởng Thụ" : 10
"FFA — Tự Do TC" : 10
"GIVE — Cho Đi" : 5
```

### 3C. Sequence Diagram — Tạo Danh Mục & Gắn Vào Hũ

```
Sinh Sequence Diagram cho luồng "Tạo Danh Mục Chi Tiêu & Gắn Vào Hũ":

1. User chọn hũ (NEC) → điền tên "Ăn uống" → chọn màu #FF6B35 → chọn icon 🍜
2. Frontend POST /api/danh-muc/ {ten_dm, loai=chi, loai_hu=NEC, mau_sac, bieu_tuong}
3. AuthMiddleware xác thực JWT → lấy ma_nd
4. DanhMucController kiểm tra: ma_nd có tồn tại? loai_hu hợp lệ?
5. INSERT INTO danh_muc
6. HTTP 201 {danh_muc đã tạo}
7. Frontend cập nhật thẻ hũ NEC: thêm danh mục mới vào danh sách
8. Thanh tiến trình NEC refresh

Participant: User, FrontendDanhMucJS, DanhMucController, AuthMiddleware, Database
```
