---
name: six-jars-category
description: Chức năng Quản lý Danh mục chi tiêu và Phương pháp Quản lý Tài chính 6 Chiếc Hũ (Jars Method) của T. Harv Eker trong MoneyMind.
---

# Kỹ Năng: Quản Lý Danh Mục & Phương Pháp 6 Hũ Tài Chính (Six Jars)

Chức năng cung cấp nền tảng phân bổ dòng tiền thông minh theo công thức quản lý tài chính cá nhân nổi tiếng thế giới của T. Harv Eker.

---

## 1. Công Thức 6 Chiếc Hũ Kinh Điển

| Ký hiệu | Tên Hũ | Tỷ lệ chuẩn | Mục đích sử dụng |
| :---: | :--- | :---: | :--- |
| **NEC** | **Nhu cầu thiết yếu** (Necessities) | **55%** | Ăn uống, thuê nhà, hóa đơn điện nước, xăng xe, y tế cơ bản. |
| **LTSS**| **Tiết kiệm dài hạn** (Long-term savings) | **10%** | Mua nhà, mua xe, quỹ khẩn cấp 6 tháng, chi phí y tế lớn. |
| **EDU** | **Giáo dục & Bản thân** (Education) | **10%** | Mua sách, khóa học, hội thảo, rèn luyện kỹ năng mới. |
| **PLAY**| **Hưởng thụ & Giải trí** (Play) | **10%** | Du lịch, nhà hàng sang trọng, mua sắm sở thích cá nhân. |
| **FFA** | **Tự do tài chính** (Financial Freedom)| **10%** | Đầu tư chứng khoán, bất động sản, gửi tiết kiệm sinh lời. |
| **GIVE**| **Cho đi & Thiện nguyện** (Give) | **5%** | Giúp đỡ người khó khăn, quà biếu cha mẹ, từ thiện. |

> **Quy tắc nghiệp vụ BR-01:** Tổng tỷ lệ phần trăm phân bổ của 6 hũ luôn luôn phải chính xác bằng **100%**.

---

## 2. Kiến Trúc Mã Nguồn

- **Backend Controller**: [danh_muc_controller.py](file:///c:/Users/Admin/OneDrive/Desktop/DỰ ÁN LỚN/app/controllers/danh_muc_controller.py)
  - `GET /api/danh-muc/`: Lấy danh sách danh mục và hũ của người dùng hiện tại.
  - `POST /api/danh-muc/`: Tạo danh mục mới gắn với 1 trong 6 hũ.
  - `PUT /api/danh-muc/{id}`: Sửa tên, màu sắc, biểu tượng danh mục.
  - `DELETE /api/danh-muc/{id}`: Xóa danh mục (chỉ khi chưa có giao dịch ràng buộc).
- **ORM Model**: [danh_muc.py](file:///c:/Users/Admin/OneDrive/Desktop/DỰ ÁN LỚN/app/models/danh_muc.py)
  - Cột: `ma_dm`, `ma_nd`, `ten_dm`, `loai` (thu/chi), `loai_hu` (NEC/LTSS/EDU/PLAY/FFA/GIVE), `bieu_tuong`, `mau_sac`.
- **Frontend UI/Logic**: [danh-muc.js](file:///c:/Users/Admin/OneDrive/Desktop/DỰ ÁN LỚN/frontend/js/danh-muc.js)
  - Hiển thị danh thiếp 6 hũ với thanh tiến trình trực quan, màu sắc nhận diện riêng biệt.

---

## 3. Truy Xuất & Thao Tác SQL Thủ Công

```bash
# Xem các danh mục mẫu của tài khoản đầu tiên
python -c "import sqlite3; con = sqlite3.connect('tai_chinh.db'); cur = con.cursor(); print(cur.execute('SELECT ma_dm, ten_dm, loai_hu, mau_sac FROM danh_muc LIMIT 10').fetchall()); con.close()"
```

---

## 4. Kiểm Thử Tự Động

```powershell
.env\Scripts\pytest tests/test_new_requirements.py -k "test_br01" -v
```
