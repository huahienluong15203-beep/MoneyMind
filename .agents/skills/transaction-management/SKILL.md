---
name: transaction-management
description: Chức năng Quản lý Giao dịch Thu/Chi, Tính toán Số dư ví, Lọc và Tra cứu Lịch sử giao dịch thông minh trong MoneyMind.
---

# Kỹ Năng: Quản Lý Giao Dịch & Tra Cứu (Transaction Management)

Chức năng là trái tim ghi nhận dòng tiền vào - ra hàng ngày của người dùng, liên kết trực tiếp với 6 hũ và thống kê tổng hợp.

---

## 1. Kiến Trúc & Công Cụ

- **Backend Controller**: [giao_dich_controller.py](file:///c:/Users/Admin/OneDrive/Desktop/DỰ ÁN LỚN/app/controllers/giao_dich_controller.py)
  - `POST /api/giao-dich/`: Tạo giao dịch mới (tự động kích hoạt kiểm tra cảnh báo ngân sách).
  - `GET /api/giao-dich/`: Lấy danh sách giao dịch có phân trang, lọc theo thời gian và danh mục.
  - `PUT /api/giao-dich/{id}`: Cập nhật thông tin giao dịch.
  - `DELETE /api/giao-dich/{id}`: Xóa giao dịch và hoàn tất cập nhật lại số dư.
- **ORM Model**: [giao_dich.py](file:///c:/Users/Admin/OneDrive/Desktop/DỰ ÁN LỚN/app/models/giao_dich.py)
  - Thuộc tính: `ma_gd`, `ma_nd`, `ma_dm`, `so_tien`, `loai` (`thu` hoặc `chi`), `ngay`, `ghi_chu`.
- **Frontend Modules**:
  - [giao-dich.js](file:///c:/Users/Admin/OneDrive/Desktop/DỰ ÁN LỚN/frontend/js/giao-dich.js): Form nhập liệu nhanh, chọn ngày tháng, định dạng tiền tệ VNĐ.
  - [tra-cuu.js](file:///c:/Users/Admin/OneDrive/Desktop/DỰ ÁN LỚN/frontend/js/tra-cuu.js): Bộ lọc đa tiêu chí (từ ngày - đến ngày, khoảng tiền, từ khóa ghi chú, loại hũ).

---

## 2. Quy Tắc Nghiệp Vụ Bắt Buộc

1. **Quy tắc BR-02 (Validation)**:
   - Số tiền giao dịch phải luôn luôn **lớn hơn 0** (`so_tien > 0`). Tuyệt đối từ chối giao dịch số tiền âm hoặc bằng 0.
2. **Quy tắc BR-06 (Hoàn tác số dư)**:
   - Khi một giao dịch chi tiêu bị xóa hoặc chỉnh sửa, hệ thống phải hoàn trả chính xác số tiền vào hạn mức ngân sách và số dư khả dụng.
3. **Chống lỗi IDOR (Bảo mật)**:
   - Mỗi truy vấn SQL luôn bắt buộc điều kiện `WHERE ma_nd = current_user.ma_nd`. Người dùng A không thể xem, sửa hoặc xóa giao dịch của người dùng B.

---

## 3. Truy Xuất & Debug SQL Thủ Công

```bash
# Xem 5 giao dịch chi tiêu mới nhất
python -c "import sqlite3; con = sqlite3.connect('tai_chinh.db'); cur = con.cursor(); print(cur.execute('SELECT ma_gd, so_tien, loai, ngay, ghi_chu FROM giao_dich ORDER BY ngay DESC LIMIT 5').fetchall()); con.close()"
```

---

## 4. Kiểm Thử Tự Động

```powershell
.env\Scripts\pytest tests/test_giao_dich.py -v
```
