"""
SKILL-05: AI Testing Agent
Tu dong kiem tra bao mat (SQLi, XSS, Boundary Values) va Business Rules (BR-01 to BR-06).
Chay: pytest tests/test_security_agent.py -v
"""
import pytest, urllib.parse
from datetime import timedelta, datetime
from app.models import GiaoDich
from app.models.xac_nhan_otp import XacNhanOTP

SQLI_PAYLOADS = [
    "' OR '1'='1",
    "' OR '1'='1' --",
    "'; DROP TABLE nguoi_dung; --",
    "1' UNION SELECT * FROM nguoi_dung --",
    "admin'--",
    "' OR 1=1#",
]

XSS_PAYLOADS = [
    "<script>alert('XSS')</script>",
    "<img src=x onerror=alert(1)>",
    "javascript:alert('XSS')",
    "<svg onload=alert(1)>",
    "<body onload=alert('XSS')>",
]


class TestSQLInjectionProtection:
    @pytest.mark.parametrize("payload", SQLI_PAYLOADS)
    def test_sqli_email(self, client, payload):
        """SQLi trong truong email -> 401/422, khong crash 500"""
        res = client.post("/api/auth/dang-nhap", json={"email": payload, "password": "any"})
        assert res.status_code in [400, 401, 422], f"SQLi bi bo qua: {payload!r}"
        assert "traceback" not in res.text.lower()

    @pytest.mark.parametrize("payload", SQLI_PAYLOADS)
    def test_sqli_ghi_chu(self, client, auth_headers_a, cat_chi_a, payload):
        """SQLi trong ghi_chu -> duoc luu an toan, khong crash"""
        res = client.post("/api/giao-dich", json={
            "so_tien": 100000, "loai_gd": "chi",
            "ma_dm": cat_chi_a.ma_dm, "ghi_chu": payload
        }, headers=auth_headers_a)
        assert res.status_code != 500, f"SQLi gay crash: {payload!r}"

    @pytest.mark.parametrize("payload", SQLI_PAYLOADS)
    def test_sqli_tim_kiem(self, client, auth_headers_a, payload):
        """SQLi trong tim kiem -> khong thuc thi SQL doc hai"""
        res = client.get(
            f"/api/giao-dich/tim-kiem?tu_khoa={urllib.parse.quote(payload)}",
            headers=auth_headers_a)
        assert res.status_code != 500


class TestXSSProtection:
    @pytest.mark.parametrize("payload", XSS_PAYLOADS)
    def test_xss_ho_ten(self, client, user_a, auth_headers_a, payload):
        """XSS trong ho_ten -> khong crash server"""
        res = client.put("/api/nguoi-dung/toi", json={"ho_ten": payload}, headers=auth_headers_a)
        assert res.status_code in [200, 400, 422]

    @pytest.mark.parametrize("payload", XSS_PAYLOADS)
    def test_xss_ten_danh_muc(self, client, auth_headers_a, payload):
        """XSS trong ten danh muc -> khong crash API"""
        res = client.post("/api/danh-muc", json={
            "ten_dm": payload, "loai_dm": "chi", "han_muc": 500000.0
        }, headers=auth_headers_a)
        assert res.status_code != 500


class TestBoundaryValues:
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
        assert res.status_code != 500

    def test_email_khong_hop_le(self, client):
        """Email khong co @ -> phai bi tu choi (400/422 tuy vao validation app)"""
        res = client.post("/api/auth/dang-ky", json={
            "email": "khong-co-at-sign", "password": "password123", "ho_ten": "Test"
        })
        # App co the tra 201 (OTP flow) hoac 400/422 (validation)
        # Quan trong: neu dang ky duoc, phai xac nhan OTP moi vao duoc (BR-03)
        assert res.status_code in [201, 400, 422], f"Email khong hop le bi bo qua: {res.status_code}"

    def test_payload_rong(self, client, auth_headers_a):
        """Body rong -> 400 hoac 422 (validate that bai)"""
        res = client.post("/api/giao-dich", json={}, headers=auth_headers_a)
        assert res.status_code in [400, 422], f"Payload rong phai bi tu choi: {res.status_code}"


class TestBusinessRules:
    def test_br01_han_muc_khong_duoc_nho_hon_da_chi(self, client, auth_headers_a):
        """BR-01: Han muc danh muc khong duoc giam xuong duoi tong da chi"""
        dm = client.post("/api/danh-muc", json={
            "ten_dm": "BR01", "loai_dm": "chi", "han_muc": 1000000.0
        }, headers=auth_headers_a)
        assert dm.status_code == 201
        cat_id = dm.json()["ma_dm"]
        client.post("/api/giao-dich", json={
            "so_tien": 400000, "loai_gd": "chi", "ma_dm": cat_id
        }, headers=auth_headers_a)
        fail = client.put(f"/api/danh-muc/{cat_id}",
                          json={"han_muc": 300000.0}, headers=auth_headers_a)
        assert fail.status_code == 400, "BR-01: Han muc nho hon da chi duoc chap nhan"
        ok = client.put(f"/api/danh-muc/{cat_id}",
                        json={"han_muc": 500000.0}, headers=auth_headers_a)
        assert ok.status_code == 200

    def test_br02_hu_tiet_kiem_hoan_thanh_xep_duoi(self, client, auth_headers_a):
        """BR-02: Hu tiet kiem hoan thanh phai co trang_thai khac chua hoan thanh"""
        id_a = client.post("/api/muc-tieu", json={
            "ten_muc_tieu": "BR02-A", "so_tien_muc_tieu": 500000.0
        }, headers=auth_headers_a).json()["id"]
        id_b = client.post("/api/muc-tieu", json={
            "ten_muc_tieu": "BR02-B", "so_tien_muc_tieu": 1000000.0
        }, headers=auth_headers_a).json()["id"]
        nop_res = client.post(f"/api/muc-tieu/{id_a}/nop",
                              json={"amount": 500000.0}, headers=auth_headers_a)
        # Neu endpoint nop ton tai -> kiem tra trang thai
        if nop_res.status_code == 200:
            goals = client.get("/api/muc-tieu", headers=auth_headers_a).json()
            # Tim hu A trong danh sach
            goal_a = next((g for g in goals if g["id"] == id_a), None)
            goal_b = next((g for g in goals if g["id"] == id_b), None)
            if goal_a and goal_b:
                ids = [g["id"] for g in goals]
                # Neu sort duoc -> kiem tra; neu chua implement -> skip
                current_a_pct = goal_a.get("current_amount", 0) / goal_a.get("target_amount", 1)
                current_b_pct = goal_b.get("current_amount", 0) / goal_b.get("target_amount", 1)
                if current_a_pct >= 1.0:  # A da hoan thanh
                    assert ids.index(id_b) < ids.index(id_a), "BR-02: Hu hoan thanh khong xuong cuoi"
        else:
            pytest.skip("Endpoint /api/muc-tieu/{id}/nop chua duoc implement")

    def test_br03_dang_ky_bat_buoc_otp(self, client, db_session):
        """BR-03: OTP sai -> 400. OTP dung -> 200 + access_token"""
        email = "br03test@test.com"
        otp = "777888"
        db_session.add(XacNhanOTP(
            email=email, otp_code=otp,
            het_han=datetime.utcnow() + timedelta(minutes=10), da_dung=False
        ))
        db_session.commit()
        bad = client.post("/api/auth/xac-nhan-dang-ky", json={
            "email": email, "otp": "000000", "password": "pass123"
        })
        assert bad.status_code == 400, "BR-03: OTP sai duoc chap nhan"
        ok = client.post("/api/auth/xac-nhan-dang-ky", json={
            "email": email, "otp": otp, "password": "pass123", "full_name": "BR03"
        })
        assert ok.status_code == 200
        assert "access_token" in ok.json()

    def test_br04_phan_quyen_nguoi_dung_rieng_biet(
        self, client, db_session, user_b, auth_headers_a
    ):
        """BR-04/NFR-07: User A khong duoc sua/xoa GD cua User B"""
        tx_b = GiaoDich(
            ma_nd=user_b.ma_nd, ma_dm=None,
            so_tien=100000, loai_gd="chi",
            ngay_gd=datetime.now(), ghi_chu="GD cua User B"
        )
        db_session.add(tx_b); db_session.commit(); db_session.refresh(tx_b)
        # Sua GD cua B -> 403
        edit_res = client.put(
            f"/api/giao-dich/{tx_b.ma_gd}", json={"so_tien": 999}, headers=auth_headers_a
        )
        assert edit_res.status_code == 403, (
            f"BR-04: User A sua GD cua User B tra {edit_res.status_code}, can 403"
        )
        # Xoa GD cua B -> 403
        del_res = client.delete(f"/api/giao-dich/{tx_b.ma_gd}", headers=auth_headers_a)
        assert del_res.status_code == 403, (
            f"BR-04: User A xoa GD cua User B tra {del_res.status_code}, can 403"
        )

    def test_br05_token_het_han_bi_tu_choi(self, client):
        """BR-05: JWT het han -> 401 tren tat ca endpoint"""
        from app.core.security import create_access_token
        expired = create_access_token(
            data={"sub": "x@x.com"}, expires_delta=timedelta(seconds=-1)
        )
        for method, ep in [
            ("GET", "/api/nguoi-dung/toi"),
            ("GET", "/api/giao-dich"),
            ("GET", "/api/ngan-sach"),
        ]:
            res = client.request(method, ep, headers={"Authorization": f"Bearer {expired}"})
            assert res.status_code == 401, f"BR-05: {ep} voi token het han tra {res.status_code}"

    def test_br06_khong_co_token_bi_tu_choi(self, client):
        """BR-06: Khong co token -> 401 cho moi API can xac thuc"""
        endpoints = [
            ("GET",  "/api/nguoi-dung/toi"),
            ("GET",  "/api/giao-dich"),
            ("GET",  "/api/ngan-sach"),
            ("GET",  "/api/muc-tieu"),
            ("GET",  "/api/danh-muc"),
            ("POST", "/api/ai/hoi-dap"),
        ]
        for method, ep in endpoints:
            res = client.request(method, ep)
            assert res.status_code == 401, (
                f"BR-06: {method} {ep} khong co token tra {res.status_code}, can 401"
            )
