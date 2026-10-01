---
name: mocking-ai-engine
description: >
  Tu dong gia lap cac phan hoi tu Gemini API (JSON hop le, timeout, loi 429)
  de bo test hoan tat tuc thi (< 5 giay), khong can API key that, khong ton chi phi.
---

# SKILL-03: Mocking AI Engine

## Mo ta
**Khong bao gio** goi Gemini API that trong test. Ly do:
- Ton API key (tien)
- Cham (5-30 giay moi call)
- Ket qua khong ot dinh (AI co the tra loi khac nhau)
- Khong kiem tra duoc loi timeout / rate-limit / 503

Giai phap: Dung `unittest.mock.patch` de "gia vo" Gemini tra ve bat ky ket qua muon.

---

## Ham can mock

```python
# app/services/ai_service.py - Day la diem duy nhat goi Gemini
class AIService:
    @staticmethod
    def _call_gemini_with_timeout(prompt: str, timeout: float = 25.0) -> str:
        # Goi Gemini REST API that - day la thu can mock
        ...
```

---

## Pattern 1: Mock tra ve ket qua hop le (JSON string)

```python
from unittest.mock import patch
from app.services.ai_service import AIService

def test_bao_cao_ai_tao_moi(client, auth_headers_a):
    """Test tao bao cao AI moi khi chua co cache"""
    # Gia lap Gemini tra ve JSON bao cao hop le
    mock_response = (
        'Tom tat: Chi tieu thang 9 tang 15%. '
        'Goi y: ["Giam chi an uong", "Tiet kiem them 500k", "Kiem soat chi mua sam"]'
    )
    with patch.object(AIService, "_call_gemini_with_timeout", return_value=mock_response):
        res = client.get("/api/ai/bao-cao?thang=9&nam=2026", headers=auth_headers_a)
        assert res.status_code == 200
        data = res.json()
        assert data["cached"] is False
        assert len(data["noi_dung_tom_tat"]) > 0
```

---

## Pattern 2: Mock timeout -> 503

```python
from fastapi import HTTPException, status

def test_tc08_ai_timeout_503(client, auth_headers_a):
    """TC-08: Khi Gemini phan hoi > 30s -> he thong tra 503"""
    with patch.object(
        AIService,
        "_call_gemini_with_timeout",
        side_effect=HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI Engine phan hoi qua thoi gian cho phep (> 5 giay). Vui long thu lai sau."
        )
    ):
        res = client.get("/api/ai/bao-cao?thang=9&nam=2026", headers=auth_headers_a)
        assert res.status_code == 503
        assert "qua thoi gian" in res.json()["detail"].lower()
```

---

## Pattern 3: Mock loi 429 (Rate Limit Gemini)

```python
import urllib.error

def test_ai_rate_limit_429_fallback(client, auth_headers_a):
    """Khi Gemini tra 429 -> he thong phai fallback hoac bao loi ro rang"""
    http_err = urllib.error.HTTPError(
        url="https://generativelanguage.googleapis.com/...",
        code=429,
        msg="Too Many Requests",
        hdrs={},
        fp=None
    )
    with patch.object(AIService, "_call_gemini_with_timeout", side_effect=http_err):
        res = client.get("/api/ai/bao-cao?thang=9&nam=2026", headers=auth_headers_a)
        # He thong phai xu ly graceful (503 hoac message bao loi)
        assert res.status_code in [503, 429]
```

---

## Pattern 4: Mock kiem tra cache (khong goi Gemini lan 2)

```python
from app.models import BaoCaoAI
from datetime import datetime

def test_tc07_bao_cao_ai_tu_cache_khong_goi_gemini(client, db_session, user_a, auth_headers_a):
    """TC-07: Da co cache trong DB -> Gemini KHONG duoc goi"""
    # Them cache vao DB test truoc
    db_session.add(BaoCaoAI(
        ma_nd=user_a.ma_nd,
        thang_nam="2026-09",
        noi_dung_tom_tat="Bao cao da luu cache.",
        goi_y_dieu_chinh='["Goi y 1", "Goi y 2", "Goi y 3"]',
        ngay_tao=datetime.utcnow()
    ))
    db_session.commit()

    with patch.object(AIService, "_call_gemini_with_timeout") as mock_fn:
        res = client.get("/api/ai/bao-cao?thang=9&nam=2026", headers=auth_headers_a)
        assert res.status_code == 200
        assert res.json()["cached"] is True
        mock_fn.assert_not_called()  # QUAN TRONG: Gemini khong duoc goi
```

---

## Pattern 5: Mock hoi-dap AI ngoai pham vi (TC-09)

```python
def test_tc09_hoi_ngoai_pham_vi_ai_tu_choi(client, auth_headers_a):
    """TC-09: Hoi ve co phieu -> AI tu choi theo system prompt"""
    # Mock Gemini tra ve cau tu choi (nhu system prompt huong dan)
    mock_refuse = (
        "Xin loi, toi chi ho tro tu van quan ly chi tieu va tiet kiem ca nhan. "
        "Toi khong co tham quyen tu van dau tu co phieu."
    )
    with patch.object(AIService, "_call_gemini_with_timeout", return_value=mock_refuse):
        res = client.post("/api/ai/hoi-dap",
                          json={"cau_hoi": "Nen mua co phieu nao?"},
                          headers=auth_headers_a)
        assert res.status_code == 200
        tra_loi = res.json()["tra_loi"]
        assert any(kw in tra_loi.lower() for kw in ["xin loi", "khong co tham quyen", "quan ly chi tieu"])
```

---

## Thoi gian chay bo test

| Khong mock | Mock Gemini |
|-----------|-------------|
| ~30-90 giay/test (goi API that) | < 0.1 giay/test |
| Ton API key | Khong ton API key |
| Ket qua khong on dinh | Ket qua luon nhat quan |

---

## Dung mocker (pytest-mock) thay vi patch truc tiep

```python
# Cai: pip install pytest-mock
def test_ai_voi_mocker(client, mocker, auth_headers_a):
    """Cach ngan hon dung mocker fixture"""
    mocker.patch.object(
        AIService, "_call_gemini_with_timeout",
        return_value="Bao cao AI mock"
    )
    res = client.get("/api/ai/bao-cao?thang=9&nam=2026", headers=auth_headers_a)
    assert res.status_code == 200
```
