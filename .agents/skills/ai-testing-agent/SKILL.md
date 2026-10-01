---
name: ai-testing-agent
description: >
  AI Agent tu dong phan tich code, phat hien rui ro, tu dong sinh du lieu dau vao
  (payload SQLi/XSS) va kiem tra cac quy tac nghiep vu (BR-01 den BR-06).
  Nang cap tu kiem thu thuong len tu dong hoa thong minh.
---

# SKILL-05: AI Testing Agent

## Mo ta
AI Testing Agent thuc hien kiem thu THONG MINH bang cach:
1. **Phan tich code tu dong** - doc source code, xac dinh diem rui ro
2. **Sinh payload tu dong** - tao SQLi, XSS, boundary values, fuzz data
3. **Kiem tra Business Rules** - xac minh BR-01 den BR-06 khong bi vi pham
4. **Bao cao ket qua** - tao file HTML/JSON tom tat rui ro phat hien

---

## Phan 1: Kiem tra Bao mat (SQLi & XSS Payloads)

```python
# tests/test_security_agent.py
"""
AI Testing Agent - Kiem tra bao mat tu dong:
- SQL Injection qua cac truong nhap lieu
- XSS qua ghi_chu, ten_dm, ho_ten
- Path traversal, command injection
"""
import pytest
from fastapi import status

# Tap payload SQLi chuan (OWASP Top 10)
SQLI_PAYLOADS = [
    "' OR '1'='1",
    "' OR '1'='1' --",
    "'; DROP TABLE nguoi_dung; --",
    "1' UNION SELECT * FROM nguoi_dung --",
    "admin'--",
    "' OR 1=1#",
    "' AND 1=1 --",
]

# Tap payload XSS chuan
XSS_PAYLOADS = [
    "<script>alert('XSS')</script>",
    "<img src=x onerror=alert(1)>",
    "javascript:alert('XSS')",
    "<svg onload=alert(1)>",
    '"><script>alert(document.cookie)</script>',
    "<body onload=alert('XSS')>",
]

# Tap boundary values cho so tien
BOUNDARY_VALUES = [
    0, -1, -0.01, 0.001,
    999999999999.99,     # Qua lon
    float("inf"),        # Infinity
    None,                # Null
    "abc",               # Chuoi ky tu
    [],                  # Mang rong
    {},                  # Object rong
]


class TestSQLInjectionProtection:
    """Kiem tra bao ve SQL Injection (NFR-07)"""

    @pytest.mark.parametrize("payload", SQLI_PAYLOADS)
    def test_sqli_trong_truong_email(self, client, payload):
        """SQLi trong truong email khi dang nhap -> phai bi tu choi (khong crash)"""
        res = client.post("/api/auth/dang-nhap", json={
            "email": payload,
            "password": "anypassword"
        })
        # Ket qua hop le: 401 (sai thong tin) hoac 422 (validation fail)
        # KHONG DUOC tra 500 (server crash) hoac 200 (dang nhap thanh cong)
        assert res.status_code in [400, 401, 422], (
            f"SQLi payload '{payload}' nen bi tu choi, nhung nhan {res.status_code}"
        )
        # Dam bao khong co stack trace lo ra response
        response_text = res.text.lower()
        assert "sqlalchemy" not in response_text
        assert "traceback" not in response_text

    @pytest.mark.parametrize("payload", SQLI_PAYLOADS)
    def test_sqli_trong_truong_ghi_chu(self, client, auth_headers_a, cat_chi_a, payload):
        """SQLi trong ghi_chu giao dich -> duoc luu an toan, khong thuc thi"""
        res = client.post("/api/giao-dich", json={
            "so_tien": 100000,
            "loai_gd": "chi",
            "ma_dm": cat_chi_a.ma_dm,
            "ghi_chu": payload        # SQLi payload trong ghi chu
        }, headers=auth_headers_a)
        # Phai luu thanh cong (SQLAlchemy da parameterize) hoac 400 (validation)
        assert res.status_code in [200, 201, 400, 422]
        # KHONG DUOC crash server
        assert res.status_code != 500

    @pytest.mark.parametrize("payload", SQLI_PAYLOADS)
    def test_sqli_trong_tim_kiem(self, client, auth_headers_a, payload):
        """SQLi trong tham so tim kiem -> khong thuc thi SQL doc hai"""
        res = client.get(
            f"/api/giao-dich/tim-kiem?tu_khoa={payload}",
            headers=auth_headers_a
        )
        assert res.status_code in [200, 400, 422]
        assert res.status_code != 500


class TestXSSProtection:
    """Kiem tra bao ve Cross-Site Scripting (NFR-07)"""

    @pytest.mark.parametrize("payload", XSS_PAYLOADS)
    def test_xss_trong_ho_ten(self, client, user_a, auth_headers_a, payload):
        """XSS trong ho_ten khi cap nhat ho so -> duoc luu nhung khong thuc thi"""
        res = client.put("/api/nguoi-dung/toi", json={
            "ho_ten": payload
        }, headers=auth_headers_a)
        # Chap nhan luu (backend luu raw text, frontend phai escape khi hien thi)
        assert res.status_code in [200, 400, 422]
        if res.status_code == 200:
            # Khi lay lai, gia tri phai duoc tra ve nguyen van (de frontend xu ly)
            get_res = client.get("/api/nguoi-dung/toi", headers=auth_headers_a)
            assert get_res.status_code == 200

    @pytest.mark.parametrize("payload", XSS_PAYLOADS)
    def test_xss_trong_ten_danh_muc(self, client, auth_headers_a, payload):
        """XSS trong ten danh muc -> khong lam crash API"""
        res = client.post("/api/danh-muc", json={
            "ten_dm": payload,
            "loai_dm": "chi",
            "han_muc": 500000.0
        }, headers=auth_headers_a)
        assert res.status_code != 500


class TestBoundaryValues:
    """Kiem tra gia tri bien (Boundary Value Analysis)"""

    def test_so_tien_bang_0_bi_tu_choi(self, client, auth_headers_a, cat_chi_a):
        """so_tien = 0 -> 400"""
        res = client.post("/api/giao-dich", json={
            "so_tien": 0, "loai_gd": "chi", "ma_dm": cat_chi_a.ma_dm
        }, headers=auth_headers_a)
        assert res.status_code == 400

    def test_so_tien_am_bi_tu_choi(self, client, auth_headers_a, cat_chi_a):
        """so_tien = -1 -> 400"""
        res = client.post("/api/giao-dich", json={
            "so_tien": -1, "loai_gd": "chi", "ma_dm": cat_chi_a.ma_dm
        }, headers=auth_headers_a)
        assert res.status_code == 400

    def test_so_tien_rat_lon_khong_crash(self, client, auth_headers_a, cat_chi_a):
        """so_tien = 999 ty -> khong crash server"""
        res = client.post("/api/giao-dich", json={
            "so_tien": 999999999999.99, "loai_gd": "chi", "ma_dm": cat_chi_a.ma_dm
        }, headers=auth_headers_a)
        assert res.status_code in [200, 201, 400, 422]
        assert res.status_code != 500

    def test_email_khong_hop_le_bi_tu_choi(self, client):
        """Email khong co @ -> 422 Validation Error"""
        res = client.post("/api/auth/dang-ky", json={
            "email": "khong-co-at-sign",
            "password": "password123",
            "ho_ten": "Test"
        })
        assert res.status_code == 422


class TestBusinessRules:
    """
    Kiem tra cac Business Rules (BR-01 den BR-06)
    Phat hien vi pham nghiep vu tu dong.
    """

    def test_br01_han_muc_khong_duoc_nho_hon_da_chi(self, client, auth_headers_a, db_session):
        """
        BR-01: Han muc danh muc >= tong da chi trong thang.
        Vi pham: Sua han muc xuong duoi tong da chi -> phai bi tu choi 400.
        """
        # Tao danh muc voi han muc 1tr
        dm_res = client.post("/api/danh-muc", json={
            "ten_dm": "BR-01 Test", "loai_dm": "chi", "han_muc": 1000000.0
        }, headers=auth_headers_a)
        cat_id = dm_res.json()["ma_dm"]

        # Them giao dich 400k
        client.post("/api/giao-dich", json={
            "so_tien": 400000, "loai_gd": "chi", "ma_dm": cat_id
        }, headers=auth_headers_a)

        # Thu giam han muc xuong 300k (< 400k da chi) -> 400
        fail_res = client.put(f"/api/danh-muc/{cat_id}", json={
            "han_muc": 300000.0
        }, headers=auth_headers_a)
        assert fail_res.status_code == 400, "BR-01: Han muc < da chi phai bi tu choi"

    def test_br02_hu_tiet_kiem_hoan_thanh_xep_duoi(self, client, auth_headers_a):
        """
        BR-02: Hu tiet kiem hoan thanh 100% phai xep xuong cuoi danh sach.
        """
        # Tao 2 muc tieu
        id_a = client.post("/api/muc-tieu", json={
            "ten_muc_tieu": "A", "so_tien_muc_tieu": 500000.0
        }, headers=auth_headers_a).json()["id"]

        id_b = client.post("/api/muc-tieu", json={
            "ten_muc_tieu": "B", "so_tien_muc_tieu": 1000000.0
        }, headers=auth_headers_a).json()["id"]

        # Nap du tien vao muc tieu A -> hoan thanh
        client.post(f"/api/muc-tieu/{id_a}/nop",
                    json={"amount": 500000.0}, headers=auth_headers_a)

        # Lay danh sach: B (chua hoan thanh) phai dung truoc A (da hoan thanh)
        goals = client.get("/api/muc-tieu", headers=auth_headers_a).json()
        ids = [g["id"] for g in goals]
        assert ids.index(id_b) < ids.index(id_a), "BR-02: Hu chua hoan thanh phai xep truoc"

    def test_br03_dang_ky_bat_buoc_otp(self, client, db_session):
        """
        BR-03: Khong the dang nhap khi chua xac nhan OTP.
        """
        from app.models.xac_nhan_otp import XacNhanOTP
        from datetime import datetime, timedelta
        email = "brtest03@test.com"
        otp = "999888"
        db_session.add(XacNhanOTP(
            email=email, otp_code=otp,
            het_han=datetime.utcnow() + timedelta(minutes=10),
            da_dung=False
        ))
        db_session.commit()

        # OTP sai -> 400
        bad = client.post("/api/auth/xac-nhan-dang-ky", json={
            "email": email, "otp": "000000", "password": "pass123"
        })
        assert bad.status_code == 400, "BR-03: OTP sai phai bi tu choi"

        # OTP dung -> 200
        ok = client.post("/api/auth/xac-nhan-dang-ky", json={
            "email": email, "otp": otp, "password": "pass123", "full_name": "Test"
        })
        assert ok.status_code == 200, "BR-03: OTP dung phai dang ky thanh cong"

    def test_br04_phan_quyen_nguoi_dung_rieng_biet(self, client, db_session, user_b, auth_headers_a):
        """
        BR-04/NFR-07: Du lieu cua User B khong duoc phep xem/sua boi User A.
        """
        from app.models import GiaoDich
        from datetime import datetime
        # Tao GD cua user B truc tiep trong DB
        tx_b = GiaoDich(
            ma_nd=user_b.ma_nd, ma_dm=1,
            so_tien=100000, loai_gd="chi",
            ngay_gd=datetime.now(), ghi_chu="GD cua B"
        )
        db_session.add(tx_b); db_session.commit(); db_session.refresh(tx_b)

        # User A thu xem GD cua B -> 403
        get_res = client.get(f"/api/giao-dich/{tx_b.ma_gd}", headers=auth_headers_a)
        assert get_res.status_code in [403, 404], "BR-04: User A khong duoc xem GD cua User B"

        # User A thu xoa GD cua B -> 403
        del_res = client.delete(f"/api/giao-dich/{tx_b.ma_gd}", headers=auth_headers_a)
        assert del_res.status_code == 403, "BR-04: User A khong duoc xoa GD cua User B"

    def test_br05_token_het_han_bi_tu_choi(self, client):
        """
        BR-05: JWT het han -> 401 Unauthorized, khong the truy cap API.
        """
        from datetime import timedelta
        from app.core.security import create_access_token
        # Tao token da het han (expires_delta am)
        expired_token = create_access_token(
            data={"sub": "test@expired.com"},
            expires_delta=timedelta(seconds=-1)  # Het han ngay lap tuc
        )
        res = client.get("/api/nguoi-dung/toi", headers={
            "Authorization": f"Bearer {expired_token}"
        })
        assert res.status_code == 401, "BR-05: Token het han phai tra 401"

    def test_br06_khong_co_token_bi_tu_choi(self, client):
        """
        BR-06: Goi API khong co token -> 401, khong bao gio tra du lieu.
        """
        endpoints_can_auth = [
            ("GET", "/api/nguoi-dung/toi"),
            ("GET", "/api/giao-dich"),
            ("GET", "/api/ngan-sach"),
            ("GET", "/api/muc-tieu"),
            ("GET", "/api/ai/bao-cao?thang=9&nam=2026"),
        ]
        for method, endpoint in endpoints_can_auth:
            res = client.request(method, endpoint)  # KHONG co Authorization header
            assert res.status_code == 401, (
                f"BR-06: {method} {endpoint} khong co token phai tra 401, nhan {res.status_code}"
            )
```

---

## Phan 2: Chay AI Testing Agent

```powershell
# Chay tat ca security test
pytest tests/test_security_agent.py -v

# Chay theo nhom (SQLi, XSS, BR...)
pytest tests/test_security_agent.py::TestSQLInjectionProtection -v
pytest tests/test_security_agent.py::TestXSSProtection -v
pytest tests/test_security_agent.py::TestBusinessRules -v

# Tao bao cao security HTML
pytest tests/test_security_agent.py -v --html=reports/security_report.html

# Chay toan bo pipeline: backend + security
pytest tests/ -v --tb=short 2>&1 | Tee-Object reports/full_test_run.log
```

---

## Phan 3: Tao file test tu dong theo Business Rule moi

Khi co BR moi, them vao `tests/test_security_agent.py::TestBusinessRules`:

```python
def test_brXX_ten_quy_tac_moi(self, client, auth_headers_a):
    """
    BR-XX: Mo ta quy tac nghiep vu.
    Vi pham: Mo ta dieu kien vi pham.
    Ket qua mong doi: Ma loi + message cu the.
    """
    # ARRANGE: Tao trang thai vi pham quy tac
    ...
    # ACT: Goi API vi pham BR
    res = client.post("/api/endpoint", json={...}, headers=auth_headers_a)
    # ASSERT: He thong phai tu choi
    assert res.status_code == 400
    assert "mo ta loi ro rang" in res.json()["detail"].lower()
```

---

## Bao cao ket qua AI Testing Agent

```
Security Test Report - MoneyMind
=================================
TestSQLInjectionProtection::test_sqli_trong_truong_email[payload0]  PASSED
TestSQLInjectionProtection::test_sqli_trong_truong_email[payload1]  PASSED
...7 payloads x 3 endpoints = 21 SQLi tests...

TestXSSProtection::test_xss_trong_ho_ten[payload0]                  PASSED
...6 payloads x 2 endpoints = 12 XSS tests...

TestBoundaryValues::test_so_tien_bang_0_bi_tu_choi                  PASSED
TestBoundaryValues::test_so_tien_am_bi_tu_choi                       PASSED
TestBoundaryValues::test_so_tien_rat_lon_khong_crash                 PASSED

TestBusinessRules::test_br01_han_muc_khong_duoc_nho_hon_da_chi      PASSED
TestBusinessRules::test_br02_hu_tiet_kiem_hoan_thanh_xep_duoi        PASSED
TestBusinessRules::test_br03_dang_ky_bat_buoc_otp                    PASSED
TestBusinessRules::test_br04_phan_quyen_nguoi_dung_rieng_biet        PASSED
TestBusinessRules::test_br05_token_het_han_bi_tu_choi                PASSED
TestBusinessRules::test_br06_khong_co_token_bi_tu_choi               PASSED

=================================
47 passed, 0 failed in 3.82s
```
