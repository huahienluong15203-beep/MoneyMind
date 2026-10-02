# 🛡️ PROMPT GUIDE — ai-testing-agent

> **Skill:** AI Agent Kiểm Thử Bảo Mật & Business Rules Tự Động  
> **File SKILL:** [SKILL.md](./SKILL.md)  
> **Cập nhật:** 03/10/2026

---

## 📌 PHẦN 1 — PROMPT SINH SKILL (Tạo SKILL.md)

```
Bạn là Senior Security Engineer & AI QA Automation Expert.
Hãy tạo file SKILL.md cho skill 'ai-testing-agent' trong MoneyMind.

Nội dung bắt buộc:

1. Mô tả AI Testing Agent:
   - Tự động đọc source code API endpoints → phát hiện input chưa validate
   - Tự động sinh payload tấn công (SQLi, XSS, IDOR)
   - Tự động kiểm tra 6 Business Rules (BR-01 đến BR-06)
   - Sinh báo cáo lỗi chi tiết với mức độ rủi ro (HIGH/MEDIUM/LOW)

2. Danh sách payload tự động sinh:
   SQLi payloads:
   - "' OR '1'='1"
   - "1; DROP TABLE nguoi_dung;--"
   - "' UNION SELECT email, mat_khau FROM nguoi_dung--"
   XSS payloads:
   - "<script>alert(document.cookie)</script>"
   - "<img src=x onerror=alert(1)>"
   - "javascript:alert(1)"
   IDOR patterns:
   - Thay ma_nd trong JWT → truy cập dữ liệu người khác
   - Brute-force ma_gd, ma_dm, ma_mt

3. Kiểm tra 6 Business Rules (bảng: BR | Mô tả | Endpoint | Test):
   - BR-01: Tổng tỷ lệ 6 hũ = 100%
   - BR-02: Số tiền giao dịch > 0
   - BR-03: Cảnh báo ngưỡng 80% và 100%
   - BR-04: Khóa sau 5 lần sai OTP
   - BR-05: Ẩn danh hóa trước AI (không leak PII)
   - BR-06: Hoàn tiền khi xóa mục tiêu

4. File test hiện có: tests/test_security_agent.py (10KB)

5. Lệnh chạy: .\\venv\\Scripts\\pytest tests/test_security_agent.py -v --tb=long

Định dạng: YAML frontmatter + Markdown, có bảng, code block, link file.
```

---

## 💻 PHẦN 2 — PROMPT TẠO CODE

### 2A. Viết Test Đầy Đủ Cho BR-04 (Khóa Tài Khoản)

```
Hãy đọc `.agents/skills/ai-testing-agent/SKILL.md`.
Viết test case đầy đủ cho BR-04 trong tests/test_security_agent.py.

BR-04: Sau 5 lần nhập sai OTP → tài khoản bị khóa, không thể thử tiếp.

Test cases:
1. test_br04_sau_5_lan_sai_otp_tai_khoan_bi_khoa:
   - Đăng ký user mới → nhận OTP (mock email)
   - Gửi OTP sai 5 lần: POST /api/auth/xac-nhan-otp {"ma_otp": "000000"} × 5
   - Lần 1-4: Assert HTTP 400 "Mã OTP không đúng"
   - Lần 5: Assert HTTP 423 "Tài khoản bị khóa do nhập sai quá nhiều lần"
   - Thử đăng nhập: POST /api/auth/dang-nhap → Assert HTTP 403 "Tài khoản bị khóa"

2. test_br04_khoa_tam_thoi_co_the_gui_lai_otp:
   - Sau khi bị khóa → POST /api/auth/gui-lai-otp {email}
   - Assert HTTP 200 → OTP mới được gửi, so_lan_sai reset về 0

3. test_br04_4_lan_sai_van_chua_bi_khoa:
   - Sai 4 lần → Assert tài khoản VẪN có thể thử tiếp
   - Lần 5 đúng → Assert đăng nhập thành công

Dùng fixtures từ conftest.py.
```

### 2B. Viết Test Pentest Tự Động (SQLi & XSS)

```
Hãy đọc `.agents/skills/ai-testing-agent/SKILL.md`.
Thêm parametrized test pentest vào tests/test_security_agent.py.

Dùng @pytest.mark.parametrize để test hàng loạt payload:

SQLi Payloads:
sqli_payloads = [
    "' OR '1'='1",
    "'; DROP TABLE giao_dich;--",
    "1 UNION SELECT * FROM nguoi_dung",
    "' OR 1=1 LIMIT 1--",
    "admin'--",
]

@pytest.mark.parametrize("payload", sqli_payloads)
async def test_sqli_dang_nhap(authenticated_client, payload):
    response = await authenticated_client.post("/api/auth/dang-nhap", json={"email": payload, "mat_khau": "test"})
    assert response.status_code in [400, 401, 422]  # Không được 200 hay 500

XSS Payloads:
xss_payloads = [
    "<script>alert(1)</script>",
    "<img src=x onerror=alert(document.cookie)>",
    "javascript:alert(1)",
    "<svg onload=alert(1)>",
]

@pytest.mark.parametrize("payload", xss_payloads)
async def test_xss_ten_danh_muc(authenticated_client, payload):
    response = await authenticated_client.post("/api/danh-muc/", json={"ten_dm": payload, "loai": "chi", "loai_hu": "NEC"})
    # Nếu lưu thành công → kiểm tra đã được escaped
    if response.status_code == 201:
        saved_name = response.json()["ten_dm"]
        assert "<script>" not in saved_name
        assert "javascript:" not in saved_name

Chạy: pytest tests/test_security_agent.py -k "sqli or xss" -v
```

### 2C. Thêm Test IDOR (Insecure Direct Object Reference)

```
Hãy đọc `.agents/skills/ai-testing-agent/SKILL.md`.
Viết test cases IDOR cho tất cả các endpoint quan trọng.

Test cases:
1. test_idor_giao_dich_nguoi_khac:
   - Tạo User A + User B
   - User A tạo giao dịch ma_gd=100
   - User B cố GET /api/giao-dich/100 → Assert HTTP 403 hoặc 404
   - User B cố DELETE /api/giao-dich/100 → Assert HTTP 403 hoặc 404
   - User B cố PUT /api/giao-dich/100 → Assert HTTP 403 hoặc 404

2. test_idor_danh_muc_nguoi_khac:
   - User A tạo danh mục ma_dm=50
   - User B cố PUT /api/danh-muc/50 → Assert HTTP 403/404
   - User B cố DELETE /api/danh-muc/50 → Assert HTTP 403/404

3. test_idor_muc_tieu_nguoi_khac:
   - User A tạo mục tiêu ma_mt=20
   - User B cố POST /api/muc-tieu/20/nop-tien → Assert HTTP 403/404
   - User B cố DELETE /api/muc-tieu/20 → Assert HTTP 403/404

4. test_idor_ngan_sach_nguoi_khac:
   - User A tạo ngân sách ma_ns=10
   - User B cố PUT /api/ngan-sach/10 → Assert HTTP 403/404

Mỗi test có docstring: "IDOR Risk: Nếu fail, attacker có thể [mô tả tác hại]"
```

---

## 🗺️ PHẦN 3 — PROMPT SINH SƠ ĐỒ

### 3A. Flowchart — AI Testing Agent Workflow

```
Sinh Flowchart (Mermaid.js flowchart TD) cho quy trình AI Testing Agent tự động:

Start: Nhận danh sách API endpoints
→ Phase 1 — Phân Tích:
   a. Đọc router definitions từ app/controllers/
   b. Xác định các input field nhận từ user
   c. Phân loại risk: string fields (SQLi/XSS), int fields (IDOR), auth fields (JWT)
→ Phase 2 — Sinh Payload:
   a. SQLi: 10 payload chuẩn OWASP
   b. XSS: 8 payload phổ biến
   c. IDOR: brute-force ID ±10 quanh ID hợp lệ
→ Phase 3 — Thực Thi Test:
   a. Gửi từng payload đến endpoint tương ứng
   b. Ghi lại: status code, response body, thời gian
→ Phase 4 — Phân Tích Kết Quả:
   a. 200 với payload SQLi? → HIGH RISK
   b. Text chứa HTML chưa escaped? → MEDIUM RISK (XSS)
   c. 200 với ID người khác? → HIGH RISK (IDOR)
   d. 500 Internal Error? → MEDIUM RISK (thông tin lộ)
→ Phase 5 — Báo Cáo:
   a. Tổng hợp: X HIGH, Y MEDIUM, Z LOW
   b. Chi tiết từng lỗi: endpoint + payload + response
   c. Khuyến nghị fix
```

### 3B. Sequence Diagram — Kiểm Tra BR-04 Tự Động

```
Sinh Sequence Diagram cho AI Agent tự động kiểm tra BR-04 (Khóa tài khoản sau 5 lần sai OTP):

1. AI Agent: tạo test user (POST /api/auth/dang-ky)
2. AI Agent: skip OTP (dùng fixture bypass OTP trong test env)
3. AI Agent: ghi nhận tài khoản ở trạng thái "chua_kich_hoat"
4. AI Agent: Lần 1 → POST /api/auth/xac-nhan-otp {"ma_otp": "000000"}
   → Assert HTTP 400, so_lan_sai = 1
5. AI Agent: Lần 2-4 → tương tự, so_lan_sai tăng dần
6. AI Agent: Lần 5 → POST /api/auth/xac-nhan-otp
   → Assert HTTP 423 Locked
   → Assert DB: trang_thai = "khoa"
7. AI Agent: Thử đăng nhập → POST /api/auth/dang-nhap
   → Assert HTTP 403 "Tai khoan bi khoa"
8. AI Agent: BR-04 PASSED ✅ → ghi vào báo cáo

Participant: AITestingAgent, FastAPIServer, AuthController, Database
```

### 3C. Bảng Rủi Ro Bảo Mật Toàn Hệ Thống

```
Sinh bảng Mermaid.js (không có loại bảng native, dùng flowchart để mô phỏng matrix) 
hoặc sinh bảng Markdown đánh giá rủi ro bảo mật MoneyMind:

| Vector Tấn Công | Endpoint Nguy Hiểm | Mức Rủi Ro | Trạng Thái |
|---|---|---|---|
| SQL Injection | POST /api/auth/dang-nhap | HIGH | Đã bảo vệ (SQLAlchemy ORM) |
| XSS Stored | POST /api/danh-muc/ (ten_dm) | MEDIUM | Đã escape (Pydantic validate) |
| IDOR | GET/PUT/DELETE /api/giao-dich/{id} | HIGH | Đã kiểm tra ma_nd |
| Brute-force OTP | POST /api/auth/xac-nhan-otp | HIGH | BR-04: khóa sau 5 lần |
| JWT Forgery | Tất cả endpoint xác thực | HIGH | python-jose HS256 |
| PII Leak to AI | POST /api/ai/chat | MEDIUM | BR-05: privacy_service.py |
| Mass Assignment | PUT /api/nguoi-dung/{id} | MEDIUM | Pydantic schema giới hạn field |

Sinh dưới dạng Markdown table chuẩn GitHub.
```
