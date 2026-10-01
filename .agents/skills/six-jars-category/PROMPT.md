# Prompt Tạo Skill: Quản Lý Danh Mục & 6 Hũ Tài Chính (Six Jars)

> **Mục tiêu:** Tạo skill chi tiết về phương pháp quản lý tài chính 6 chiếc hũ (Jars Method) và CRUD danh mục chi tiêu trong MoneyMind.

---

## 📌 Nội Dung Prompt Gốc Đã Sử Dụng

```text
Bạn là Chuyên gia Cố vấn Tài chính Cá nhân (CFP) và Kỹ sư Phần mềm.
Hãy tạo skill 'six-jars-category' cho MoneyMind:

1. Lý thuyết và phương pháp 6 chiếc hũ của T. Harv Eker:
   - NEC (55%), LTSS (10%), EDU (10%), PLAY (10%), FFA (10%), GIVE (5%).
   - Quy tắc vàng BR-01: Tổng phân bổ luôn bằng 100%.

2. Thiết kế CSDL và Backend:
   - Bảng danh_muc: ma_dm, ma_nd, ten_dm, loai, loai_hu, mau_sac, bieu_tuong.
   - Controller app/controllers/danh_muc_controller.py hỗ trợ CRUD hũ và khởi tạo bộ danh mục mặc định khi người dùng mới đăng ký.

3. Frontend:
   - frontend/js/danh-muc.js render thẻ 6 hũ trực quan với màu sắc tương ứng.
   - Modal thêm/sửa danh mục có chọn icon và bảng mã màu.

4. Hướng dẫn kiểm thử quy tắc phân bổ tỷ lệ phần trăm và bảo vệ IDOR khi sửa danh mục.

Định dạng đầu ra: Chuẩn SKILL.md với YAML frontmatter cho Antigravity AI Agent.
```

---

## 🚀 Hướng Dẫn Tái Tạo Hoặc Cập Nhật Skill Này

Gửi prompt:
```text
Hãy đọc `app/models/danh_muc.py`, `app/controllers/danh_muc_controller.py` và `frontend/js/danh-muc.js`.
Cập nhật file `.agents/skills/six-jars-category/SKILL.md`:
- Thêm cơ chế tùy chỉnh tỷ lệ hũ theo từng giai đoạn (ví dụ: sinh viên tăng EDU, gia đình tăng NEC).
```
