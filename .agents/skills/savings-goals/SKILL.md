---
name: savings-goals
description: Chức năng Quản lý Mục tiêu Tiết kiệm, Nộp tiền Tích lũy, Theo dõi Tiến độ và Dự báo Thời gian Hoàn thành trong MoneyMind.
---

# Kỹ Năng: Quản Lý Mục Tiêu Tiết Kiệm (Savings Goals)

Chức năng hỗ trợ người dùng hiện thực hóa các ước mơ tài chính lớn (mua sắm tài sản, quỹ khẩn cấp, du học, khởi nghiệp) thông qua việc đặt mục tiêu và tích lũy có kỷ luật.

---

## 1. Kiến Trúc & Công Cụ

- **Backend Controller**: [muc_tieu_controller.py](file:///c:/Users/Admin/OneDrive/Desktop/DỰ ÁN LỚN/app/controllers/muc_tieu_controller.py)
  - `GET /api/muc-tieu/`: Lấy danh sách mục tiêu tiết kiệm kèm tiến độ % và số ngày còn lại.
  - `POST /api/muc-tieu/`: Tạo mục tiêu mới (tên mục tiêu, số tiền kỳ vọng, hạn chót).
  - `POST /api/muc-tieu/{id}/nop-tien`: Ghi nhận khoản tiền nộp thêm vào mục tiêu.
  - `DELETE /api/muc-tieu/{id}`: Hủy bỏ mục tiêu.
- **ORM Model**: [muc_tieu_tiet_kiem.py](file:///c:/Users/Admin/OneDrive/Desktop/DỰ ÁN LỚN/app/models/muc_tieu_tiet_kiem.py)
  - Cột: `ma_mt`, `ma_nd`, `ten_muc_tieu`, `so_tien_muc_tieu`, `so_tien_hien_tai`, `ngay_bat_dau`, `ngay_ket_thuc`, `trang_thai` (`dang_thuc_hien`, `hoan_thanh`).
- **Frontend UI/Logic**: [tiet-kiem.js](file:///c:/Users/Admin/OneDrive/Desktop/DỰ ÁN LỚN/frontend/js/tiet-kiem.js)
  - Hiển thị danh thiếp mục tiêu dạng thẻ quà tặng, vòng tròn tiến độ động (Circular SVG progress), nút "Nộp tiền nhanh".

---

## 2. Quy Trình Tính Toán Tiến Độ

1. **Tỷ lệ hoàn thành (%)**:
   $$	ext{Tiến độ} = \min\left(100, rac{	ext{so\_tien\_hien\_tai}}{	ext{so\_tien\_muc\_tieu}} 	imes 100ight)$$
2. **Tự động chuyển trạng thái**:
   - Khi $	ext{so\_tien\_hien\_tai} \ge 	ext{so\_tien\_muc\_tieu}$, hệ thống tự động cập nhật `trang_thai = 'hoan_thanh'`.
3. **Validate nộp tiền**:
   - Số tiền nộp thêm phải $> 0$.

---

## 3. Truy Xuất SQL Thủ Công

```bash
# Xem danh sách mục tiêu tiết kiệm
python -c "import sqlite3; con = sqlite3.connect('tai_chinh.db'); cur = con.cursor(); print(cur.execute('SELECT ma_mt, ten_muc_tieu, so_tien_hien_tai, so_tien_muc_tieu, trang_thai FROM muc_tieu_tiet_kiem').fetchall()); con.close()"
```

---

## 4. Kiểm Thử Tự Động

```powershell
.env\Scripts\pytest tests/test_new_requirements.py -k "muc_tieu" -v
```
