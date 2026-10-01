# Prompt Tạo Skill: Quản Lý Mục Tiêu Tiết Kiệm (Savings Goals)

> **Mục tiêu:** Tạo skill xây dựng tính năng lập mục tiêu tiết kiệm, nộp tiền từng đợt, tính toán tiến độ hoàn thành và cập nhật trạng thái tự động.

---

## 📌 Nội Dung Prompt Gốc Đã Sử Dụng

```text
Bạn là Lập trình viên Fullstack FastAPI và Chuyên gia Gamification Tài chính.
Hãy tạo skill 'savings-goals' cho MoneyMind:

1. Thiết kế API:
   - CRUD mục tiêu tiết kiệm: tên, số tiền kỳ vọng, hạn chót (deadline).
   - Endpoint nộp tiền: POST /api/muc-tieu/{id}/nop-tien tăng số dư tích lũy.
   - Tự động đánh dấu hoàn thành khi đạt 100%.

2. Model & Schema:
   - app/models/muc_tieu_tiet_kiem.py.
   - Validate số tiền nộp > 0, deadline phải trong tương lai.

3. Frontend:
   - frontend/js/tiet-kiem.js render giao diện trực quan, biểu tượng heo đất, thanh tiến trình % có hiệu ứng chuyển động.

4. Hướng dẫn test tự động và truy vấn SQL kiểm tra số dư tích lũy.

Định dạng đầu ra: Chuẩn SKILL.md với YAML frontmatter cho Antigravity AI Agent.
```

---

## 🚀 Hướng Dẫn Tái Tạo Hoặc Cập Nhật Skill Này

Gửi prompt:
```text
Hãy đọc `app/controllers/muc_tieu_controller.py` và `frontend/js/tiet-kiem.js`.
Cập nhật file `.agents/skills/savings-goals/SKILL.md`:
- Thêm tính năng gợi ý số tiền cần nộp mỗi ngày/mỗi tuần để kịp hạn chót.
```
