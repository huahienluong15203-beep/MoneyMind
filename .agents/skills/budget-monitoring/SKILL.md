---
name: budget-monitoring
description: Chức năng Thiết lập Hạn mức Ngân sách hàng tháng cho 6 Hũ, Tính toán Tỷ lệ Chi tiêu và Tự động Phát Cảnh báo Ngưỡng 80% - 100% trong MoneyMind.
---

# Kỹ Năng: Quản Lý Ngân Sách & Cảnh Báo Chi Tiêu (Budget Monitoring)

Chức năng giúp người dùng kiểm soát kỷ luật tài chính bằng cách đặt trần chi tiêu cho từng hũ trong tháng và nhận cảnh báo tức thì khi chi tiêu vượt ngưỡng.

---

## 1. Kiến Trúc & Công Cụ

- **Backend Controller**: [ngan_sach_controller.py](file:///c:/Users/Admin/OneDrive/Desktop/DỰ ÁN LỚN/app/controllers/ngan_sach_controller.py)
  - `GET /api/ngan-sach/`: Lấy bảng phân bổ ngân sách tháng hiện tại kèm tiến độ chi tiêu.
  - `POST /api/ngan-sach/`: Thiết lập hạn mức ngân sách tháng cho hũ danh mục.
- **Nghiệp Vụ Trung Tâm**: [ngan_sach_service.py](file:///c:/Users/Admin/OneDrive/Desktop/DỰ ÁN LỚN/app/services/ngan_sach_service.py)
  - Hàm `kiem_tra_canh_bao_ngan_sach(user_id, danh_muc_id, db)`: Tính tổng chi tiêu lũy kế tháng hiện tại của danh mục so với định mức ngân sách.
- **ORM Models**:
  - [ngan_sach.py](file:///c:/Users/Admin/OneDrive/Desktop/DỰ ÁN LỚN/app/models/ngan_sach.py): Bảng `ngan_sach` (thang, nam, so_tien_dinh_muc).
  - [thong_bao.py](file:///c:/Users/Admin/OneDrive/Desktop/DỰ ÁN LỚN/app/models/thong_bao.py): Bảng `thong_bao` lưu thông báo cảnh báo cho người dùng.
- **Frontend UI**:
  - [ngan-sach.js](file:///c:/Users/Admin/OneDrive/Desktop/DỰ ÁN LỚN/frontend/js/ngan-sach.js): Thanh đo tỷ lệ chi tiêu (Progress bar) đổi màu Xanh (<80%) -> Vàng (80-99%) -> Đỏ (>=100%).
  - [thong-bao.js](file:///c:/Users/Admin/OneDrive/Desktop/DỰ ÁN LỚN/frontend/js/thong-bao.js): Chuông thông báo hiển thị số cảnh báo chưa đọc.

---

## 2. Quy Tắc Cảnh Báo Ngân Sách (BR-03)

Hệ thống tự động kích hoạt kiểm tra sau mỗi lần người dùng ghi nhận thêm một giao dịch chi tiêu:
- **Ngưỡng Cảnh Giác (80% - 99%)**: Phát thông báo mức độ `WARNING` cảnh báo người dùng đã chi tiêu tiệm cận hạn mức hũ.
- **Ngưỡng Vượt Hạn Mức (>= 100%)**: Phát thông báo mức độ `DANGER` cảnh báo người dùng đã chính thức bội chi hũ trong tháng.

---

## 3. Truy Xuất Dữ Liệu SQL Thủ Công

```bash
# Xem các ngân sách tháng hiện tại
python -c "import sqlite3; con = sqlite3.connect('tai_chinh.db'); cur = con.cursor(); print(cur.execute('SELECT ma_ns, ma_dm, thang, nam, so_tien_dinh_muc FROM ngan_sach').fetchall()); con.close()"
```

---

## 4. Kiểm Thử Tự Động

```powershell
.env\Scripts\pytest tests/test_ngan_sach.py -v
```
