# Prompt Tạo Skill: Mocking AI Engine (Gemini API Mock)

> **Mục tiêu:** Giả lập toàn diện các phản hồi của Google Gemini AI trong kiểm thử tự động, loại bỏ phụ thuộc API key thật, cắt giảm chi phí và giảm thời gian test xuống dưới 5 giây.

---

## 📌 Nội Dung Prompt Gốc Đã Sử Dụng

```text
Bạn là Chuyên gia Tích hợp AI (AI Integration Specialist & Test Architect).
Hãy xây dựng skill 'mocking-ai-engine' cho MoneyMind nhằm phục vụ việc test tính năng Trợ lý Tài chính AI (Google Gemini):

1. Yêu cầu nghiệp vụ:
   - Dịch vụ AI chính: `app/services/ai_service.py` (sử dụng Gemini Flash / Pro).
   - Test tự động phải chạy hoàn toàn offline / local mà không cần GEMINI_API_KEY thật.
   - Tốc độ toàn bộ bộ test AI phải < 5 giây (thay vì 30s-60s khi gọi mạng thật).

2. Các kịch bản giả lập (Test Scenarios):
   - Kịch bản 1: AI phản hồi định dạng JSON chuẩn (Báo cáo tài chính tháng, phân tích 6 hũ, lời khuyên).
   - Kịch bản 2: AI gặp lỗi Timeout (giả lập mất mạng hoặc Gemini phản hồi chậm > 15s).
   - Kịch bản 3: AI bị Rate Limit HTTP 429 (Too Many Requests - hạn mức gọi API bị hết).
   - Kịch bản 4: AI trả về Markdown/Text không đúng schema (kiểm tra hàm fallback & regex extract).

3. Kỹ thuật cài đặt:
   - Sử dụng `unittest.mock.patch` để mock `google.generativeai.GenerativeModel.generate_content`.
   - Giả lập `asyncio.to_thread` khi service gọi non-async SDK.
   - Cung cấp mẫu Mock Generator có thể tái sử dụng trong các test case mới.

Định dạng đầu ra: Chuẩn SKILL.md với YAML frontmatter hợp lệ cho Antigravity AI Agent.
```

---

## 🚀 Hướng Dẫn Tái Tạo Hoặc Nâng Cấp Skill Này

Khi muốn yêu cầu AI cập nhật hoặc tái tạo skill này, hãy gửi prompt sau:

```text
Hãy đọc file `app/services/ai_service.py` và `tests/test_ai.py` của MoneyMind.
Sau đó cập nhật file `.agents/skills/mocking-ai-engine/SKILL.md`:
- Đồng bộ payload mock với prompt template mới nhất của trợ lý Gemini.
- Bổ sung mock cho tính năng trò chuyện ngữ cảnh đa lượt (chat history multi-turn).
- Bổ sung mock kiểm tra tính năng bảo vệ quyền riêng tư `privacy_service.py` trước khi dữ liệu được gửi tới AI.
```
