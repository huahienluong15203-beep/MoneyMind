# Prompt Tạo Skill: Quản Lý Ngân Sách & Cảnh Báo (Budget Monitoring)

> **Mục tiêu:** Tạo skill xây dựng hệ thống hạn mức ngân sách tháng cho 6 hũ và thuật toán phát sinh cảnh báo tự động khi chạm ngưỡng 80% và 100%.

---

## 📌 Nội Dung Prompt Gốc Đã Sử Dụng

```text
Bạn là Kỹ sư Backend & Thiết kế Giải thuật Cảnh báo Tài chính.
Hãy tạo skill 'budget-monitoring' cho MoneyMind:

1. Cơ chế tính toán ngân sách:
   - Thiết lập ngân sách theo tháng/năm cho từng danh mục hũ.
   - Service app/services/ngan_sach_service.py tính tổng chi tiêu thực tế trong tháng.

2. Quy tắc nghiệp vụ BR-03 (Alert Thresholds):
   - >= 80%: Tạo thông báo nhắc nhở hũ sắp cạn.
   - >= 100%: Tạo thông báo cảnh báo nghiêm trọng đã vượt ngân sách.
   - Trả thông tin cảnh báo ngay trong response của POST /api/giao-dich/.

3. Frontend:
   - frontend/js/ngan-sach.js: Hiển thị thanh tiến trình 3 trạng thái màu (Xanh, Vàng, Đỏ).
   - frontend/js/thong-bao.js: Danh sách thông báo dạng dropdown có nút đánh dấu đã đọc.

4. Hướng dẫn test tự động bằng pytest test_ngan_sach.py.

Định dạng đầu ra: Chuẩn SKILL.md với YAML frontmatter cho Antigravity AI Agent.
```

---

## 🚀 Hướng Dẫn Tái Tạo Hoặc Cập Nhật Skill Này

Gửi prompt:
```text
Hãy đọc `app/services/ngan_sach_service.py` và `app/controllers/ngan_sach_controller.py`.
Cập nhật file `.agents/skills/budget-monitoring/SKILL.md`:
- Bổ sung cơ chế gợi ý ngân sách tự động dựa trên mức thu nhập trung bình 3 tháng gần nhất.
```
