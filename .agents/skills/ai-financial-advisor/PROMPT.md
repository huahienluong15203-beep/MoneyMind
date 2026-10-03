# 🤖 PROMPT GUIDE — ai-financial-advisor

> **Skill:** Trợ Lý Tài Chính AI Gemini & AI Autonomous Agent  
> **File SKILL:** [SKILL.md](./SKILL.md)  
> **Cập nhật:** 03/10/2026

---

## 📌 PHẦN 1 — PROMPT SINH SKILL (Tạo SKILL.md)

```
Bạn là Chuyên gia AI Engineering & Privacy Engineer.
Hãy tạo file SKILL.md cho skill 'ai-financial-advisor' trong MoneyMind.
Đây là skill phức tạp nhất dự án.

Nội dung bắt buộc:

1. Kiến trúc AI (bảng + link file):
   - ai_service.py (135KB): module lớn nhất, tích hợp Gemini SDK
     + Sử dụng google-generativeai với mô hình gemini-3.8-flash
     + Cascade Fallback: gemini-3.8-flash → gemini-3.7-flash → gemini-flash-latest
     + Bắt lỗi: Timeout (>15s), HTTP 429 rate limit, network error
   - privacy_service.py: ẩn danh hóa dữ liệu trước khi gửi Gemini (BR-05)
     + Thay email → "USER_EMAIL_HIDDEN"
     + Thay họ tên → "USER_NAME_HIDDEN"
   - bao_cao_ai.py ORM: cache báo cáo tháng (không gọi lại API)
   - Frontend: ai.js — Drawer chat trượt từ phải, typing effect, Markdown render

2. 4 tính năng AI chính:
   a. Báo Cáo Tài Chính Tháng: chấm điểm 0-100, nhận xét cơ cấu chi tiêu, 3 hành động cụ thể
   b. Tư Vấn Phân Bổ Ngân Sách: đề xuất mức phân bổ dựa trên thu nhập thực tế
   c. Chat Hỏi Đáp Thông Minh: trả lời về chi tiêu, tiết kiệm, đầu tư
   d. AI Autonomous Agent: điều khiển app qua ngôn ngữ tự nhiên (20+ lệnh)

3. Danh sách 20+ lệnh Autonomous Agent:
   Giao dịch: thêm/sửa/xóa/tra cứu
   Hũ tiết kiệm: tạo/nộp tiền/rút tiền/nâng mục tiêu/xóa hũ
   Danh mục & Ngân sách: tạo/đổi tên/chỉnh hạn mức/xóa
   Phân tích: đánh giá sức khỏe/chấm điểm/tư vấn

4. Auto-refresh UI sau Autonomous Action:
   loadSummary(), loadTransactions(), loadSavingsGoals(), loadCategories(), loadNotifications()

5. Endpoint:
   - POST /api/ai/chat {message, session_history?} — Chat tổng quát
   - GET /api/ai/bao-cao-thang?thang=10&nam=2026 — Báo cáo tháng (có cache)

6. Lệnh Pytest: .\\venv\\Scripts\\pytest tests/test_ai.py -v

Định dạng: YAML frontmatter + Markdown, có bảng và code block, link file.
```

---

## 💻 PHẦN 2 — PROMPT TẠO CODE (Mở Rộng Tính Năng)

### 2A. Thêm Lệnh AI "Phân Tích Xu Hướng Chi Tiêu"

```
Hãy đọc `.agents/skills/ai-financial-advisor/SKILL.md`.
Thêm lệnh AI mới: "Phân tích xu hướng chi tiêu" vào ai_service.py.

Kích hoạt khi user gõ: "phân tích xu hướng", "xu hướng chi tiêu của tôi",
"tôi tiêu gì nhiều nhất", "so sánh tháng này với tháng trước"

Xử lý:
1. AI truy vấn DB: giao dịch 3 tháng gần nhất, GROUP BY loai_hu, thang
2. Tính % tăng/giảm mỗi hũ so với tháng trước
3. Ẩn danh qua privacy_service.py (BR-05) trước khi gửi Gemini
4. Prompt Gemini: "Dưới đây là xu hướng chi tiêu 3 tháng: {data}. Hãy phân tích..."
5. Gemini trả về insight: hũ nào tăng/giảm đáng kể + lý do có thể + gợi ý
6. Response: chat message với bảng so sánh markdown + icon 📈📉

Thêm handler trong hàm route_intent() của ai_service.py.
Không phá vỡ các lệnh Autonomous Agent hiện tại.
```

### 2B. Thêm Nhận Diện Giao Dịch Từ Ảnh Hóa Đơn (Gemini Vision)

```
Hãy đọc `.agents/skills/ai-financial-advisor/SKILL.md`.
Thêm tính năng nhận diện giao dịch từ ảnh chụp hóa đơn (Gemini Vision API).

Yêu cầu:
- Endpoint: POST /api/ai/nhan-dien-hoa-don (multipart/form-data, file: image)
- Validate: chỉ chấp nhận JPG/PNG/WEBP, max 5MB
- Encode ảnh sang base64 → gửi Gemini với prompt:
  "Đọc hóa đơn này và trích xuất: tên cửa hàng, tổng tiền, ngày mua, các mặt hàng"
- Response JSON: {ten_cua_hang, tong_tien, ngay, mon_hang, danh_muc_goi_y, ghi_chu_goi_y}
- Frontend ai.js:
  + Nút camera 📷 trong chat box
  + Preview ảnh trước khi gửi
  + Sau khi nhận diện: pre-fill form thêm giao dịch với data từ AI
  + User xác nhận → tạo giao dịch thật
- Ẩn danh hóa: KHÔNG gửi ảnh cho Gemini nếu ảnh chứa CMND/thẻ tín dụng (kiểm tra text)
```

### 2C. Thêm Tính Năng Nhắc Nhở Thông Minh (Smart Reminders)

```
Hãy đọc `.agents/skills/ai-financial-advisor/SKILL.md`.
Thêm tính năng AI tự động nhắc nhở thông minh.

Logic:
- Mỗi sáng 8:00, AI phân tích dữ liệu từng user và tạo nhắc nhở cá nhân hóa:
  + "Hôm nay là ngày 25, bạn chưa đạt mục tiêu tiết kiệm tháng này (còn thiếu 500k)"
  + "Chi tiêu NEC tháng này đã 87%, hãy cẩn thận trong 5 ngày còn lại"
  + "Bạn có giao dịch định kỳ 'Thuê nhà' vào ngày 1 tháng tới (3 ngày nữa)"
- Lưu vào bảng thong_bao với loai = 'ai_reminder'
- Cron job: 8:00 sáng hàng ngày
- Gemini tổng hợp tối đa 3 nhắc nhở quan trọng nhất (không spam)
- Frontend: Toast notification khi mở app

Dùng privacy_service.py, không gửi dữ liệu cá nhân thật cho Gemini.
```

---

## 🗺️ PHẦN 3 — PROMPT SINH SƠ ĐỒ

### 3A. Sequence Diagram — Luồng AI Autonomous Agent Đầy Đủ

```
Sinh Sequence Diagram chi tiết cho "AI Autonomous Financial Agent" trong MoneyMind.
Kịch bản: User gõ "Tạo hũ tiết kiệm mua laptop 20 triệu hạn 31/12/2026"

1. User → Chat UI (ai.js): nhập text
2. Chat UI → AIController: POST /api/ai/chat {message, session_history}
3. AIController → PrivacyService: anonymize({ho_ten, email})
4. AIController → AIService: process_autonomous(message, anonymized_context)
5. AIService → Gemini API: Prompt intent detection
   (Fallback: gemini-3.8-flash → gemini-3.7-flash → gemini-flash-latest)
6. Gemini → AIService: {intent: "CREATE_SAVINGS_GOAL", ten: "Mua laptop", so_tien: 20000000, han_chot: "2026-12-31"}
7. AIService → Database: INSERT INTO muc_tieu_tiet_kiem
8. Database → AIService: ma_mt = 42, OK
9. AIService: tính thang_du_kien = (20,000,000 / avg_save) tháng
10. AIService → AIController: {action_done: true, reply: "✅ Đã tạo hũ Mua laptop 20tr, cần tiết kiệm ~X tháng để đạt mục tiêu", refresh: ["savings"]}
11. AIController → Chat UI: HTTP 200 {reply, refresh_modules}
12. Chat UI → User: hiển thị reply có emoji + formatting
13. Chat UI: gọi loadSavingsGoals() → cập nhật danh sách hũ realtime

Participant: User, ChatUI_AIjs, AIController, PrivacyService, AIService, GeminiAPI, Database
```

### 3B. Flowchart — Cascade Fallback Model Gemini

```
Sinh Flowchart (Mermaid.js flowchart TD) cho cơ chế Cascade Fallback Model Gemini:

Start: Nhận request AI
→ Thử gemini-3.8-flash
  → Thành công? → return response
  → Timeout (>15s)? → Log warning → Thử gemini-3.7-flash
  → 429 Rate Limit? → Wait 2s → Thử gemini-3.7-flash
  → Lỗi khác? → Log error → Thử gemini-3.7-flash

→ Thử gemini-3.7-flash
  → Thành công? → return response
  → Timeout hoặc 429? → Thử gemini-flash-latest

→ Thử gemini-flash-latest
  → Thành công? → return response
  → Tất cả thất bại? → return {error: "AI tạm thời không khả dụng, vui lòng thử lại sau"}

Ghi chú: Mỗi lần fallback đều log model đã dùng để monitoring.
```

### 3C. Component Diagram — Kiến Trúc Module AI

```
Sinh Component Diagram (Mermaid.js flowchart LR) cho kiến trúc module AI MoneyMind:

Components:
- Frontend [ai.js]: Chat Drawer UI, Typing Effect, Markdown Renderer
- AIController [ai_controller.py]: Route /api/ai/chat, /api/ai/bao-cao-thang
- PrivacyService [privacy_service.py]: Anonymize PII data (BR-05)
- AIService [ai_service.py 135KB]:
  + IntentRouter: phân loại intent từ text
  + AutonomousAgent: thực thi action (CRUD DB)
  + ChatHandler: trả lời câu hỏi thông thường
  + ReportGenerator: tạo báo cáo tháng chấm điểm
- GeminiClient: gọi Google Generative AI API (Cascade Fallback)
- Cache [bao_cao_ai table]: Lưu báo cáo 30 ngày để tránh gọi lại API

Luồng: Frontend → AIController → PrivacyService → AIService → GeminiClient
                                                   ↓
                                              Database (CRUD Actions)
```
