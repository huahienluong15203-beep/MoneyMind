# 🎭 PROMPT GUIDE — mocking-ai-engine

> **Skill:** Mock Google Gemini API — Test AI Offline Không Tốn Chi Phí  
> **File SKILL:** [SKILL.md](./SKILL.md)  
> **Cập nhật:** 03/10/2026

---

## 📌 PHẦN 1 — PROMPT SINH SKILL (Tạo SKILL.md)

```
Bạn là Senior Test Engineer chuyên Mock & Stub trong Python.
Hãy tạo file SKILL.md cho skill 'mocking-ai-engine' trong MoneyMind.

Nội dung bắt buộc:

1. Vấn đề khi test AI thật:
   - Tốn tiền API (mỗi request tốn token → chi phí)
   - Chậm (Gemini response 2-10 giây → test suite 5 phút+)
   - Không ổn định (429 rate limit, timeout, API down)
   - Kết quả không deterministic (AI trả lời khác nhau mỗi lần)

2. Giải pháp: unittest.mock.patch
   - Target: "app.services.ai_service.genai.GenerativeModel"
   - Hoặc: "google.generativeai.GenerativeModel.generate_content"

3. 4 loại mock response cần tạo (code block):
   a. Mock thành công — ADD_TRANSACTION:
      MagicMock(text='{"action": "ADD_TRANSACTION", "so_tien": 20000, "danh_muc": "An uong"}')
   b. Mock thành công — báo cáo tháng:
      MagicMock(text="## Báo Cáo Tháng 10\n\nĐiểm sức khỏe: 85/100\n...")
   c. Mock Timeout:
      side_effect = TimeoutError("Request timed out after 15s")
   d. Mock Rate Limit 429:
      side_effect = Exception("429 Resource exhausted: Quota exceeded")

4. Fixture mock_gemini trong conftest.py (code block hoàn chỉnh):
   @pytest.fixture
   def mock_gemini_add_transaction():
       with patch("app.services.ai_service.genai.GenerativeModel") as mock:
           mock.return_value.generate_content.return_value = MagicMock(text=...)
           yield mock

5. Đảm bảo test chạy < 5 giây toàn bộ suite (không call API thật)
6. Cách verify mock được gọi đúng: mock.assert_called_once_with(...)

Định dạng: YAML frontmatter + Markdown, có code block, link file.
```

---

## 💻 PHẦN 2 — PROMPT TẠO CODE

### 2A. Viết Test Đầy Đủ Cho AI Autonomous Agent (Có Mock)

```
Hãy đọc `.agents/skills/mocking-ai-engine/SKILL.md`.
Viết test cases đầy đủ cho AI Autonomous Agent trong tests/test_ai.py.

Test cases cần có (tất cả dùng mock Gemini, KHÔNG gọi API thật):

1. test_ai_them_giao_dich_bang_text:
   - Mock Gemini trả về: ADD_TRANSACTION {so_tien: 20000, danh_muc: "An uong"}
   - POST /api/ai/chat {"message": "Toi di an banh mi 20k"}
   - Assert: HTTP 200, giao dịch được tạo trong DB, so_du_vi giảm 20000

2. test_ai_xoa_giao_dich_gan_nhat:
   - Tạo 1 giao dịch trước → Mock Gemini → DELETE_TRANSACTION
   - POST /api/ai/chat {"message": "Xoa giao dich vua them"}
   - Assert: HTTP 200, giao dịch bị xóa, so_du_vi hoàn lại

3. test_ai_tao_muc_tieu_tiet_kiem:
   - Mock Gemini → CREATE_SAVINGS_GOAL {ten: "Mua laptop", so_tien: 20000000}
   - Assert: mục tiêu được tạo trong DB

4. test_ai_timeout_fallback:
   - Mock model chính raise TimeoutError → Mock model fallback thành công
   - Assert: HTTP 200 (không trả 500), dùng fallback model

5. test_ai_rate_limit_429:
   - Mock tất cả models raise Exception("429")
   - Assert: HTTP 200 với message "AI tam thoi khong kha dung"

Fixtures: authenticated_client, mock_gemini (từ conftest.py)
```

### 2B. Thêm Fixtures Mock Vào conftest.py

```
Hãy đọc `.agents/skills/mocking-ai-engine/SKILL.md`.
Thêm các fixtures mock Gemini vào tests/conftest.py.

Fixtures cần thêm:

@pytest.fixture
def mock_gemini_success_transaction():
    """Mock Gemini trả về intent ADD_TRANSACTION thành công"""
    with patch("app.services.ai_service.genai.GenerativeModel") as mock:
        mock.return_value.generate_content.return_value = MagicMock(
            text='{"action": "ADD_TRANSACTION", "so_tien": 50000, "loai": "chi", "danh_muc_goi_y": "An uong", "ghi_chu": "Banh mi"}'
        )
        yield mock

@pytest.fixture
def mock_gemini_timeout():
    """Mock Gemini timeout → test cascade fallback"""
    with patch("app.services.ai_service.genai.GenerativeModel") as mock:
        mock.return_value.generate_content.side_effect = TimeoutError("Timeout 15s")
        yield mock

@pytest.fixture
def mock_gemini_rate_limit():
    """Mock tất cả models đều 429 → test error handling"""
    with patch("app.services.ai_service.genai.GenerativeModel") as mock:
        mock.return_value.generate_content.side_effect = Exception("429 Resource exhausted")
        yield mock

@pytest.fixture
def mock_gemini_bao_cao():
    """Mock Gemini trả về báo cáo tháng markdown"""
    with patch("app.services.ai_service.genai.GenerativeModel") as mock:
        mock.return_value.generate_content.return_value = MagicMock(
            text="## Bao Cao Thang 10/2026\n\nDiem: 78/100\n\nNhan xet: Chi tieu NEC..."
        )
        yield mock

Đặt tất cả mock fixtures trong conftest.py để dùng chung toàn bộ test files.
```

---

## 🗺️ PHẦN 3 — PROMPT SINH SƠ ĐỒ

### 3A. Flowchart — So Sánh Test Thật vs Test Mock

```
Sinh Flowchart (Mermaid.js flowchart LR) so sánh 2 chiến lược test AI:

Nhánh trái — Test Thật (KHÔNG nên):
- Test gọi thật Gemini API
- Tốn tiền: ~$0.001/test × 100 tests = $0.1/lần chạy
- Chậm: 3-10s/test × 100 tests = 10+ phút
- Có thể fail ngẫu nhiên (429, timeout, network)
- Kết quả không deterministic

Nhánh phải — Test Mock (KHUYẾN NGHỊ):
- unittest.mock.patch thay thế Gemini
- Miễn phí: không gọi API thật
- Nhanh: <0.1s/test × 100 tests = <10 giây
- Luôn deterministic
- Test offline hoàn toàn (không cần internet)

Kết quả: Mock nhanh hơn 100x, miễn phí, ổn định
```

### 3B. Sequence Diagram — Mock Patch Hoạt Động Như Thế Nào

```
Sinh Sequence Diagram cho cơ chế unittest.mock.patch:

1. pytest bắt đầu test: test_ai_them_giao_dich
2. pytest setup fixture mock_gemini_success:
   a. patch("app.services.ai_service.genai.GenerativeModel") context manager
   b. THAY THẾ GenerativeModel thật bằng MagicMock
   c. Cấu hình: mock.return_value.generate_content.return_value = fake_response
3. Test body:
   a. POST /api/ai/chat {"message": "an banh mi 20k"}
   b. AIController → AIService.process()
   c. AIService gọi GenerativeModel() → NHẬN MagicMock (không phải class thật)
   d. mock.generate_content(prompt) → NHẬN fake_response (JSON định sẵn)
   e. AIService parse JSON → action = ADD_TRANSACTION
   f. AIService INSERT giao_dich vào DB
   g. HTTP 200 response
4. Test assert: status == 200, giao_dich trong DB, so_du_vi giảm
5. pytest teardown fixture:
   a. patch context manager thoát
   b. GenerativeModel thật được khôi phục

Participant: Pytest, MockFixture, AIService, MockGenerativeModel, FakeResponse, Database
```
