---
name: frontend-test-suite
description: >
  Chay tu dong kiem thu giao dien MoneyMind: Dashboard, bieu do thong ke, Chatbot AI.
  Su dung Playwright (E2E) cho Vanilla JS SPA, khong can React/Vitest.
---

# SKILL-04: Frontend Test Suite

## Mo ta
Frontend MoneyMind la Vanilla JS SPA (khong dung React). Cong cu test phu hop:
- **Playwright** - E2E test toan bo luong nguoi dung trong trinh duyet that
- **pytest-playwright** - tich hop Playwright vao pytest (cung runner voi backend test)

Playwright tu dong mo trinh duyet (Chromium/Firefox/WebKit), thao tac nhu nguoi
dung that (click, nhap form, kiem tra hien thi...).

---

## Cai dat

```powershell
# Cai thu vien
pip install playwright pytest-playwright

# Cai trinh duyet Chromium (1 lan duy nhat, ~100MB)
playwright install chromium

# Them vao requirements.txt
playwright>=1.40.0
pytest-playwright>=0.4.0
```

---

## Cau truc thu muc tests/frontend/

```
tests/
  frontend/
    conftest.py                <- Fixtures: page, base_url, logged_in_page
    test_auth_ui.py            <- Test giao dien dang nhap, dang ky, OTP
    test_dashboard_ui.py       <- Test Dashboard: so du, thong ke nhanh
    test_bieu_do_ui.py         <- Test bieu do thong ke (bar chart, pie)
    test_chatbot_ui.py         <- Test hop thoai AI chatbot
    test_giao_dich_form_ui.py  <- Test form them giao dich
```

---

## Fixtures dung chung (tests/frontend/conftest.py)

```python
# tests/frontend/conftest.py
import pytest
from playwright.sync_api import Page

BASE_URL = "http://127.0.0.1:8000"   # Server phai dang chay

@pytest.fixture(scope="session")
def base_url():
    return BASE_URL

@pytest.fixture
def logged_in_page(page: Page, base_url: str):
    """Trang da dang nhap san, co the dung ngay cho test UI"""
    page.goto(f"{base_url}/")
    # Nhap thong tin dang nhap test
    page.fill("#email-input", "user_a@test.com")
    page.fill("#password-input", "password123")
    page.click("#login-btn")
    # Cho den khi Dashboard hien ra
    page.wait_for_selector("#dashboard-section", timeout=5000)
    return page
```

---

## Test 1: Giao dien Dang Nhap

```python
# tests/frontend/test_auth_ui.py
from playwright.sync_api import Page, expect

def test_hien_thi_form_dang_nhap(page: Page, base_url: str):
    """Form dang nhap phai hien thi du cac truong bat buoc"""
    page.goto(f"{base_url}/")
    expect(page.locator("#email-input")).to_be_visible()
    expect(page.locator("#password-input")).to_be_visible()
    expect(page.locator("#login-btn")).to_be_enabled()

def test_dang_nhap_sai_hien_thong_bao_loi(page: Page, base_url: str):
    """Dang nhap sai email/MK -> hien thong bao loi ro rang"""
    page.goto(f"{base_url}/")
    page.fill("#email-input", "sai@email.com")
    page.fill("#password-input", "satpassword")
    page.click("#login-btn")
    # Ket qua: hien thong bao loi trong vong 3 giay
    expect(page.locator(".error-message, .toast-error")).to_be_visible(timeout=3000)
    error_text = page.locator(".error-message, .toast-error").inner_text()
    assert len(error_text) > 0

def test_dang_nhap_thanh_cong_chuyen_dashboard(page: Page, base_url: str):
    """Dang nhap dung -> chuyen sang Dashboard"""
    page.goto(f"{base_url}/")
    page.fill("#email-input", "user_a@test.com")
    page.fill("#password-input", "password123")
    page.click("#login-btn")
    expect(page.locator("#dashboard-section")).to_be_visible(timeout=5000)
```

---

## Test 2: Dashboard & So Du

```python
# tests/frontend/test_dashboard_ui.py
from playwright.sync_api import Page, expect

def test_dashboard_hien_thi_so_du(logged_in_page: Page):
    """Dashboard phai hien thi so du hien tai cua user"""
    page = logged_in_page
    so_du_el = page.locator("#so-du-hien-tai, .balance-amount")
    expect(so_du_el).to_be_visible()
    # So du phai la so (co the chua chu 'd' hoac 'VND')
    text = so_du_el.inner_text()
    assert any(c.isdigit() for c in text)

def test_dashboard_hien_thi_thu_chi_thang(logged_in_page: Page):
    """Dashboard hien thi tong thu va tong chi thang nay"""
    page = logged_in_page
    expect(page.locator("#tong-thu")).to_be_visible()
    expect(page.locator("#tong-chi")).to_be_visible()

def test_bieu_do_thu_chi_render(logged_in_page: Page):
    """Bieu do thu/chi phai render (canvas/svg ton tai)"""
    page = logged_in_page
    page.click("text=Thong ke")  # Chuyen sang trang thong ke
    # Cho canvas hoac svg xuat hien
    bieu_do = page.locator("canvas, svg").first
    expect(bieu_do).to_be_visible(timeout=5000)
```

---

## Test 3: Form Them Giao Dich

```python
# tests/frontend/test_giao_dich_form_ui.py
from playwright.sync_api import Page, expect

def test_form_them_giao_dich_day_du_truong(logged_in_page: Page):
    """Form them GD phai co truong so tien, danh muc, loai, ngay"""
    page = logged_in_page
    page.click("#btn-them-giao-dich, text=Them giao dich")
    expect(page.locator("input[name=so_tien], #input-so-tien")).to_be_visible(timeout=3000)
    expect(page.locator("select[name=ma_dm], #select-danh-muc")).to_be_visible()

def test_nhap_so_tien_am_hien_loi_validation(logged_in_page: Page):
    """Nhap so tien am -> hien thong bao loi ngay tren form (client-side)"""
    page = logged_in_page
    page.click("#btn-them-giao-dich, text=Them giao dich")
    page.fill("input[name=so_tien], #input-so-tien", "-50000")
    page.keyboard.press("Tab")  # Blur de kich hoat validation
    # Phai co thong bao loi hoac truong chuyen mau do
    loi = page.locator(".field-error, .invalid-feedback, input:invalid")
    expect(loi.first).to_be_visible(timeout=2000)
```

---

## Test 4: Chatbot AI

```python
# tests/frontend/test_chatbot_ui.py
from playwright.sync_api import Page, expect
from unittest.mock import patch
from app.services.ai_service import AIService

def test_hop_thoai_chatbot_hien_thi(logged_in_page: Page):
    """Nut mo chatbot phai hien thi va click duoc"""
    page = logged_in_page
    chatbot_btn = page.locator("#btn-ai-chat, .chatbot-toggle, text=Tro ly AI")
    expect(chatbot_btn).to_be_visible()
    chatbot_btn.click()
    expect(page.locator(".chatbot-window, #chatbot-panel")).to_be_visible(timeout=3000)

def test_gui_cau_hoi_hien_tra_loi(logged_in_page: Page):
    """Nhap cau hoi -> bot phai hien tra loi trong < 30s"""
    page = logged_in_page
    page.click("#btn-ai-chat, .chatbot-toggle")
    page.fill("#chat-input, .chat-input-field", "Chi tieu thang nay the nao?")
    page.click("#chat-send-btn, button[type=submit]")
    # Cho tra loi xuat hien (max 30s)
    bot_reply = page.locator(".bot-message, .ai-response").last
    expect(bot_reply).to_be_visible(timeout=30000)
    assert len(bot_reply.inner_text()) > 5
```

---

## Lenh chay Frontend Tests

```powershell
# Chay tat ca frontend test (server phai dang chay o port 8000)
pytest tests/frontend/ -v

# Chay co hien trinh duyet (de xem thu cong)
pytest tests/frontend/ -v --headed

# Chay cham lai (de debug)
pytest tests/frontend/ -v --headed --slowmo=1000

# Chay tren Firefox
pytest tests/frontend/ --browser=firefox -v

# Chup screenshot khi fail
pytest tests/frontend/ --screenshot=on-failure
```

---

## Luu y quan trong

1. **Server phai chay truoc** khi chay frontend test:
   ```powershell
   # Terminal 1: Khoi dong server
   .\venv\Scripts\python.exe main.py
   # Terminal 2: Chay test
   pytest tests/frontend/ -v
   ```

2. **Dung ID duy nhat** cho tung element HTML de Playwright de tim thay:
   ```html
   <!-- Tot: co ID ro rang -->
   <button id="btn-them-giao-dich">Them giao dich</button>
   <!-- Tranh: khong co ID -->
   <button class="btn btn-primary">Them giao dich</button>
   ```

3. **Dung data-testid** cho element khong co ID tu nhien:
   ```html
   <canvas data-testid="bieu-do-thu-chi"></canvas>
   ```
   ```python
   page.locator("[data-testid='bieu-do-thu-chi']")
   ```
