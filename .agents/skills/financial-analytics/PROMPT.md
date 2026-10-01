# Prompt Tạo Skill: Thống Kê & Trực Quan Hóa Biểu Đồ (Financial Analytics)

> **Mục tiêu:** Tạo skill xây dựng bộ API thống kê tài chính tổng hợp và tích hợp thư viện Chart.js để vẽ biểu đồ cơ cấu 6 hũ và xu hướng thu chi.

---

## 📌 Nội Dung Prompt Gốc Đã Sử Dụng

```text
Bạn là Kỹ sư Data Visualization & Backend FastAPI.
Hãy tạo skill 'financial-analytics' cho MoneyMind:

1. Thiết kế API thống kê:
   - GET /api/thong-ke/tong-quan tính tổng thu, tổng chi, số dư.
   - GET /api/thong-ke/theo-danh-muc nhóm GROUP BY ma_dm, tính tỷ lệ %.
   - GET /api/thong-ke/xu-huong nhóm theo tháng (strftime('%Y-%m', ngay)).

2. Tích hợp Chart.js trên Frontend:
   - Biểu đồ tròn Doughnut: Cơ cấu chi tiêu 6 hũ với bảng màu tiêu chuẩn.
   - Biểu đồ cột Bar Chart: Xu hướng thu nhập vs chi tiêu 6 tháng.
   - Quản lý vòng đời biểu đồ: Hủy instance chart cũ trước khi vẽ chart mới để tránh lag bộ nhớ.

3. Frontend: frontend/js/thong-ke.js xử lý format tiền tệ và responsive trên thiết bị di động.

4. Hướng dẫn kiểm tra tính toàn vẹn của dữ liệu tổng hợp bằng câu lệnh SQL thủ công.

Định dạng đầu ra: Chuẩn SKILL.md với YAML frontmatter cho Antigravity AI Agent.
```

---

## 🚀 Hướng Dẫn Tái Tạo Hoặc Cập Nhật Skill Này

Gửi prompt:
```text
Hãy đọc `app/controllers/thong_ke_controller.py` và `frontend/js/thong-ke.js`.
Cập nhật file `.agents/skills/financial-analytics/SKILL.md`:
- Bổ sung tính năng so sánh chi tiêu giữa tháng này so với cùng kỳ tháng trước (MoM Growth Rate).
```
