# Prompt Tạo Skill: Quản Lý Giao Dịch & Tra Cứu (Transaction Management)

> **Mục tiêu:** Tạo skill hoàn chỉnh về CRUD giao dịch thu/chi, xác thực số tiền, lọc tra cứu và phòng chống IDOR trong MoneyMind.

---

## 📌 Nội Dung Prompt Gốc Đã Sử Dụng

```text
Bạn là Lập trình viên Fullstack FastAPI + Vanilla JS.
Hãy tạo skill 'transaction-management' cho MoneyMind:

1. Thiết kế Endpoint & Service:
   - POST /api/giao-dich/ tạo mới giao dịch thu/chi.
   - GET /api/giao-dich/ tra cứu, phân trang, lọc theo danh mục, ngày tháng.
   - PUT & DELETE /api/giao-dich/{id} cập nhật và hoàn tác số dư (BR-06).

2. Quy tắc nghiệp vụ & Bảo mật:
   - BR-02: Số tiền bắt buộc > 0 (Pydantic Field(gt=0)).
   - IDOR Defense: Kiểm tra ma_nd sở hữu trước mọi thao tác cập nhật/xóa.

3. Frontend:
   - frontend/js/giao-dich.js: Form thêm giao dịch modal, auto format currency 100,000 đ.
   - frontend/js/tra-cuu.js: Lọc đa năng theo từ khóa, hũ, thời gian.

4. Hướng dẫn test tự động bằng pytest test_giao_dich.py.

Định dạng đầu ra: Chuẩn SKILL.md với YAML frontmatter cho Antigravity AI Agent.
```

---

## 🚀 Hướng Dẫn Tái Tạo Hoặc Cập Nhật Skill Này

Gửi prompt:
```text
Hãy đọc `app/controllers/giao_dich_controller.py`, `app/models/giao_dich.py` và `frontend/js/tra-cuu.js`.
Cập nhật file `.agents/skills/transaction-management/SKILL.md`:
- Bổ sung tính năng xuất file Excel/CSV lịch sử giao dịch.
- Bổ sung tính năng đính kèm ảnh hóa đơn giao dịch.
```
