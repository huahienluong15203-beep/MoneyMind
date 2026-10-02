# 📊 PROMPT GUIDE — budget-monitoring

> **Skill:** Thiết Lập Ngân Sách & Cảnh Báo Ngưỡng Chi Tiêu  
> **File SKILL:** [SKILL.md](./SKILL.md)  
> **Cập nhật:** 03/10/2026

---

## 📌 PHẦN 1 — PROMPT SINH SKILL (Tạo SKILL.md)

```
Bạn là Kỹ sư Backend chuyên FastAPI + SQLAlchemy và Chuyên gia Tài chính Cá nhân.
Hãy tạo file SKILL.md cho skill 'budget-monitoring' trong MoneyMind.

Nội dung bắt buộc:

1. Cơ chế cảnh báo 2 ngưỡng (BR-03):
   - WARNING: chi tiêu thực tế >= 80% định mức → thông báo màu vàng ⚠️
   - CRITICAL: chi tiêu thực tế >= 100% định mức → thông báo màu đỏ 🚨
   - Tự động ghi vào bảng thong_bao sau MỖI giao dịch chi

2. Kiến trúc (bảng + link file):
   - Backend: app/controllers/ngan_sach_controller.py
   - Service logic: app/services/ngan_sach_service.py (43KB — module chính)
     + Hàm: kiem_tra_canh_bao(ma_nd, ma_dm, thang, nam) → alert_info
   - ORM: app/models/ngan_sach.py (ma_ns, ma_nd, ma_dm, thang, nam, so_tien_dinh_muc)
   - Frontend: frontend/js/ngan-sach.js (thanh tiến trình màu động)

3. Danh sách endpoint:
   - POST /api/ngan-sach/ — Tạo hạn mức cho danh mục theo tháng/năm
   - GET /api/ngan-sach/ — Trạng thái tháng hiện tại (% thực tế vs định mức)
   - GET /api/ngan-sach/ket-chuyen — Xem lịch sử kết chuyển
   - PUT /api/ngan-sach/{id} — Cập nhật định mức
   - DELETE /api/ngan-sach/{id} — Xóa hạn mức

4. SQL query tính % chi tiêu thực tế vs định mức

5. Schema Pydantic v2: NganSachCreate, NganSachResponse

6. Lệnh Pytest: .\\venv\\Scripts\\pytest tests/test_ngan_sach.py -v

Định dạng: YAML frontmatter + Markdown. Có bảng, code block, link file.
```

---

## 💻 PHẦN 2 — PROMPT TẠO CODE (Mở Rộng Tính Năng)

### 2A. Thêm Báo Cáo Chi Tiêu Email Hàng Tuần

```
Hãy đọc `.agents/skills/budget-monitoring/SKILL.md`.
Thêm tính năng gửi email báo cáo chi tiêu hàng tuần cho người dùng.

Yêu cầu:
- Chạy mỗi Chủ Nhật 20:00 (APScheduler CronTrigger)
- Lấy tất cả user có is_email_report = True
- Với mỗi user: tổng hợp chi tiêu 7 ngày qua theo từng hũ
- Template HTML email đẹp:
  + Header: logo MoneyMind + "Báo Cáo Tuần [ngày - ngày]"
  + Bảng 6 hũ: Tên hũ | Chi tiêu | Định mức | % | Trạng thái (✅🟡🔴)
  + Footer: link "Xem chi tiết" → app
- Dùng email_service.py hiện có (Gmail SMTP)
- Thêm cột is_email_report (bool, default=True) vào bảng nguoi_dung
- Endpoint bật/tắt: PUT /api/nguoi-dung/cai-dat-email {is_email_report: bool}
- Frontend: Toggle switch trong trang cài đặt

Không phá vỡ cơ chế cảnh báo realtime BR-03 hiện tại.
```

### 2B. Thêm Kết Chuyển Ngân Sách Tháng

```
Hãy đọc `.agents/skills/budget-monitoring/SKILL.md`.
Thêm tính năng "Kết Chuyển Ngân Sách" cuối tháng.

Logic:
- Cuối mỗi tháng, phần định mức chưa chi còn dư → tùy chọn kết chuyển:
  + "Chuyển sang tháng tới": Tăng định mức tháng sau thêm phần dư
  + "Tiết kiệm dư": Chuyển phần dư vào mục tiêu tiết kiệm chỉ định
  + "Để vậy": Định mức tháng sau giữ nguyên
- Cron job: 1 ngày/lần, kiểm tra các ngân sách hết tháng
- Model: app/models/ket_chuyen_ngan_sach.py
- Endpoint: POST /api/ngan-sach/ket-chuyen {ma_ns, phuong_thuc, ma_mt?}
- Notification: Ghi vào thong_bao khi kết chuyển tự động
```

### 2C. Thêm Dự Báo Chi Tiêu Cuối Tháng

```
Hãy đọc `.agents/skills/budget-monitoring/SKILL.md`.
Thêm tính năng "Dự Báo Chi Tiêu Cuối Tháng".

Logic:
- Lấy chi tiêu trung bình ngày = tổng_chi_thang / so_ngay_da_qua
- Dự báo tổng cuối tháng = chi_trung_binh_ngay * tong_so_ngay_thang
- Tính % dự báo so với định mức
- Endpoint: GET /api/ngan-sach/du-bao-thang
- Response: [{ma_dm, ten_dm, loai_hu, chi_hien_tai, dinh_muc, du_bao_cuoi_thang, % du_bao, muc_rui_ro: safe|warning|critical}]
- Frontend ngan-sach.js: Dòng dự báo (dash border) trên thanh tiến trình
```

---

## 🗺️ PHẦN 3 — PROMPT SINH SƠ ĐỒ

### 3A. Sequence Diagram — Kiểm Tra Cảnh Báo Ngân Sách (BR-03)

```
Sinh Sequence Diagram cho luồng "Kiểm Tra & Phát Cảnh Báo Ngân Sách" sau khi thêm giao dịch:

1. GiaoDichController gọi NganSachService.kiem_tra_canh_bao(ma_nd, ma_dm, thang, nam)
2. NganSachService: SELECT so_tien_dinh_muc FROM ngan_sach WHERE ma_nd=? AND ma_dm=? AND thang=? AND nam=?
3. Nếu không có ngân sách → return None (không cảnh báo)
4. SELECT SUM(so_tien) FROM giao_dich WHERE loai='chi' AND ma_dm=? AND MONTH(ngay)=thang
5. Tính phan_tram = (tong_chi / so_tien_dinh_muc) * 100
6. Nếu phan_tram < 80: return {alert: null}
7. Nếu 80 <= phan_tram < 100:
   - INSERT INTO thong_bao (loai=WARNING, "Chi tiêu đạt {phan_tram}% định mức")
   - return {alert: WARNING, phan_tram}
8. Nếu phan_tram >= 100:
   - INSERT INTO thong_bao (loai=CRITICAL, "Đã vượt định mức!")
   - return {alert: CRITICAL, phan_tram}
9. GiaoDichController gửi alert_info về Frontend

Participant: GiaoDichController, NganSachService, Database, ThongBaoService
```

### 3B. Flowchart — Logic Tính % Ngân Sách

```
Sinh Flowchart (Mermaid.js flowchart TD) cho logic tính phần trăm ngân sách:

- Start: Nhận (ma_nd, ma_dm, thang, nam)
- Query ngân sách → Có không?
  + Không → return {status: "no_budget"}
  + Có → dinh_muc = so_tien_dinh_muc
- Query tổng chi tháng → tong_chi
- Tính phan_tram = tong_chi / dinh_muc * 100
- phan_tram < 80? → return {status: "safe", color: green}
- phan_tram < 100? → return {status: "warning", color: yellow} + tạo thông báo
- phan_tram >= 100? → return {status: "critical", color: red} + tạo thông báo
- End
```
