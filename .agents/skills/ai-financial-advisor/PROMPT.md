# Prompt Tạo Skill: Trợ Lý Tài Chính AI Gemini (AI Advisor)

> **Mục tiêu:** Tạo skill xây dựng Trợ lý Tài chính AI ứng dụng Google Gemini API, cơ chế ẩn danh hóa dữ liệu cá nhân (BR-05) và bộ nhớ đệm báo cáo tài chính hàng tháng.

---

## 📌 Nội Dung Prompt Gốc Đã Sử Dụng

```text
Bạn là Chuyên gia Kỹ thuật AI & Bảo vệ Quyền riêng tư Dữ liệu (AI Safety & Privacy Engineer).
Hãy tạo skill 'ai-financial-advisor' cho MoneyMind:

1. Tích hợp Google Gemini SDK:
   - Dịch vụ app/services/ai_service.py gọi Gemini Flash.
   - Cơ chế Prompt Engineering định hình AI thành Chuyên gia Tài chính 6 Hũ.
   - Bắt lỗi Timeout (>15s), HTTP 429 Rate Limit và fallback an toàn.

2. Bảo vệ quyền riêng tư (BR-05):
   - app/services/privacy_service.py thay thế họ tên, email, số điện thoại bằng mã định danh vô danh trước khi gửi cho Google AI.

3. Cache báo cáo:
   - Bảng bao_cao_ai lưu nội dung markdown phân tích tháng của từng user.

4. Frontend:
   - frontend/js/ai.js quản lý drawer chat AI, hiển thị typing effect và render markdown.

5. Hướng dẫn mock Gemini API để test tự động không cần API key thật.

Định dạng đầu ra: Chuẩn SKILL.md với YAML frontmatter cho Antigravity AI Agent.
```

---

## 🚀 Hướng Dẫn Tái Tạo Hoặc Cập Nhật Skill Này

Gửi prompt:
```text
Hãy đọc `app/services/ai_service.py` và `app/services/privacy_service.py`.
Cập nhật file `.agents/skills/ai-financial-advisor/SKILL.md`:
- Cập nhật prompt template để hỗ trợ mô hình Gemini 1.5 Pro / Flash mới nhất.
- Bổ sung tính năng nhận diện giao dịch từ ảnh chụp hóa đơn (Gemini Vision OCR).
```
