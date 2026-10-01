---
name: financial-analytics
description: Chức năng Thống kê Tổng quan Thu - Chi - Số dư, Phân tích Cơ cấu 6 Hũ và Trực quan hóa Biểu đồ Báo cáo tài chính bằng Chart.js trong MoneyMind.
---

# Kỹ Năng: Thống Kê & Trực Quan Hóa Biểu Đồ (Financial Analytics)

Chức năng cung cấp bức tranh toàn cảnh về sức khỏe tài chính của người dùng thông qua các chỉ số tổng hợp và biểu đồ trực quan sinh động.

---

## 1. Kiến Trúc & Công Cụ

- **Backend Controller**: [thong_ke_controller.py](file:///c:/Users/Admin/OneDrive/Desktop/DỰ ÁN LỚN/app/controllers/thong_ke_controller.py)
  - `GET /api/thong-ke/tong-quan`: Tổng thu, tổng chi, số dư ròng trong tháng.
  - `GET /api/thong-ke/theo-danh-muc`: Tỷ trọng chi tiêu theo từng danh mục / hũ.
  - `GET /api/thong-ke/xu-huong`: Dữ liệu biến động thu/chi 6 tháng liên tiếp phục vụ vẽ biểu đồ đường/cột.
- **Thư viện Vẽ Biểu Đồ**: Chart.js v4.x (tích hợp trực tiếp qua CDN trong `frontend/index.html`).
- **Frontend Logic**: [thong-ke.js](file:///c:/Users/Admin/OneDrive/Desktop/DỰ ÁN LỚN/frontend/js/thong-ke.js) (34KB - module JS lớn và đầy đủ nhất phía client).

---

## 2. Các Loại Biểu Đồ Trực Quan Hóa

1. **Biểu đồ Tròn Phân Bổ 6 Hũ (Doughnut Chart)**:
   - Hiển thị tỷ trọng phần trăm thực tế người dùng đã tiêu so với tỷ lệ chuẩn của 6 hũ.
   - Nhận diện ngay hũ nào đang bị lạm chi (ví dụ: NEC vượt quá 55%).
2. **Biểu đồ Cột Xu Hướng 6 Tháng (Bar Chart)**:
   - So sánh cột Thu nhập (Xanh lục) đối đầu Chi tiêu (Đỏ) qua từng tháng.
   - Giúp người dùng theo dõi tỷ lệ tiết kiệm ròng theo thời gian.
3. **Bảng Thống Kê Chi Tiết**:
   - Danh sách xếp hạng danh mục tiêu tốn nhiều tiền nhất (Top Spending Categories).

---

## 3. Truy Vấn Tổng Hợp SQL Thủ Công

```bash
# Thống kê tổng thu và tổng chi của tài khoản
python -c "import sqlite3; con = sqlite3.connect('tai_chinh.db'); cur = con.cursor(); print(cur.execute('SELECT loai, SUM(so_tien), COUNT(*) FROM giao_dich GROUP BY loai').fetchall()); con.close()"
```

---

## 4. Kiểm Thử Tự Động

```powershell
.env\Scripts\pytest tests/test_new_requirements.py -k "thong_ke" -v
```
