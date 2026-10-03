---
name: test-management
description: >
  Quan ly toan bo Test Case MoneyMind: bang test case day du (TC, UC, BR, Security),
  dau ra mong doi, cach them test case moi, chay va doc ket qua.
  Skill trung tam de xem, them, chay va bao cao ket qua kiem thu.
---

# SKILL-00: Test Management — Quan ly Toan bo Test Case

## Muc dich
Skill nay la **diem tham chieu trung tam** cho toan bo bo kiem thu MoneyMind.
Bao gom bang test case day du, dau ra mong doi, va huong dan them / chay test.

---

## Cau truc thu muc tests/

```
tests/
  conftest.py                     <- Fixtures dung chung (db, client, user_a/b, auth, danh muc)
  test_nguoi_dung.py              <- Xac thuc, dang ky, dang nhap, quen MK
  test_giao_dich.py               <- CRUD giao dich, canh bao ngan sach, cach ly du lieu
  test_ngan_sach.py               <- Han muc, ket chuyen, dong bo vi chinh
  test_ai.py                      <- AI bao cao, hoi dap, goi y ngan sach
  test_new_requirements.py        <- Cac yeu cau nghiep vu moi (BR)
  test_security_agent.py          <- Bao mat: SQLi, XSS, Boundary Values, BR-01~BR-06
  test_ai_natural_transactions.py <- AI nhan dien giao dich tu ngon ngu tu nhien
  test_ai_confirmation.py         <- AI hoi xac nhan truoc khi ghi giao dich
  test_ai_logs.py                 <- Ghi log hoi thoai AI
```

---

## Bang Test Case Day du

### 1. Module Nguoi Dung & Xac Thuc — test_nguoi_dung.py

| ID | Ten Test | Input | Dau ra mong doi |
|----|----------|-------|-----------------|
| TC-01 | test_tc01_dang_ky_email_da_ton_tai | Email da ton tai trong DB | 400, message "email da duoc su dung" |
| TC-02 | test_tc02_dang_nhap_sai_mat_khau_khoa_tai_khoan | Sai MK 5 lan lien tiep | Lan 5 -> 403, message "tam khoa" |
| UC001 | test_dang_ky_thanh_cong | Email moi + password hop le | 201, body co email, thong_bao |
| UC002 | test_dang_nhap_thanh_cong | Email + password dung | 200, body co access_token, refresh_token |
| UC002b | test_uc002_xem_va_cap_nhat_thong_tin | JWT hop le, PUT thong tin moi | GET 200 + PUT 200, tra dung ho_ten |
| — | test_quen_mat_khau_email_khong_ton_tai | Email chua dang ky | 404, message "chua duoc dang ky" |
| — | test_quen_mat_khau_va_dat_lai_thanh_cong | OTP dung -> dat MK moi | 200, dang nhap MK moi OK, MK cu that bai |
| — | test_dang_nhap_don_thiet_bi_kickout_thiet_bi_cu | 2 thiet bi cung TK | TB1 bi kick: 401, header X-Logout-Reason: concurrent_login |

---

### 2. Module Giao Dich — test_giao_dich.py

| ID | Ten Test | Input | Dau ra mong doi |
|----|----------|-------|-----------------|
| TC-03 | test_tc03_them_giao_dich_so_tien_am | so_tien = -50000 | 400, message "lon hon 0" |
| TC-04 | test_tc04_them_giao_dich_canh_bao_vuot_ngan_sach | Chi 600k vuot han muc 500k | 201, canh_bao.vuot_ngan_sach=true |
| TC-05 | test_tc05_sua_giao_dich_kich_hoat_lai_canh_bao | Sua 200k len 700k, han muc 500k | 200, canh_bao.vuot_ngan_sach=true |
| TC-10 | test_tc10_nfr07_cach_ly_du_lieu_nguoi_dung | User A sua/xoa GD cua User B | 403 ca hai thao tac |
| UC005 | test_uc005_tim_kiem_loc_giao_dich | tu_khoa, page=1, limit=2 | 200, total=5, items.len=2, total_pages=3 |

---

### 3. Module Ngan Sach — test_ngan_sach.py

| ID | Ten Test | Input | Dau ra mong doi |
|----|----------|-------|-----------------|
| TC-06 | test_tc06_thiet_lap_ngan_sach_bang_khong | han_muc = 0 | 400, message "lon hon 0" |
| UC006 | test_uc006_thiet_lap_va_sua_ngan_sach | Tao 2M, sua 2.5M | 201 + 200, han_muc=2500000 |
| — | test_thang_moi_khong_canh_bao_thang_cu | Chi vuot thang cu, thang moi chi it | Khong co canh bao "vuot" thang moi |
| — | test_ket_chuyen_ngan_sach_tu_dong | HM 1M, chi 800k T9 -> T10 | Ket chuyen 200k, idempotent |
| — | test_sua_han_muc_tru_va_hoan_tien_vi_chinh | Tang/giam han muc hu | So du vi chinh dong bo; sai -> 400 |

---

### 4. Module AI — test_ai.py

| ID | Ten Test | Input | Dau ra mong doi |
|----|----------|-------|-----------------|
| TC-07 | test_tc07_bao_cao_ai_cache_db | Goi API khi da co cache DB | 200, cached=true, KHONG goi Gemini |
| TC-08 | test_tc08_ai_engine_timeout_503 | Mock timeout Gemini | 503, message "qua thoi gian cho phep" |
| TC-09 | test_tc09_hoi_dap_ngoai_pham_vi | Hoi ve co phieu dau tu | 200, tra loi tu choi ("xin loi"/"ngoai pham vi") |
| UC011 | test_uc011_goi_y_ngan_sach | GET /api/ai/goi-y-ngan-sach | 200, co danh_sach_goi_y, thang_nam_tiep_theo |
| — | test_ai_canh_bao_tu_ngu_khong_phu_hop | Cau hoi thu tuc | 200, co canh bao ngon tu |
| — | test_ai_tu_choi_ngoai_pham_vi_thoi_tiet | Hoi thoi tiet | 200, "ngoai pham vi" |
| — | test_ai_chao_hoi_ngan_gon | "xin chao" | 200, "xin chao ban" |
| — | test_ai_hoi_so_tien_va_ghi_nhan_da_luot | L1: an bun cha; L2: 35k | L1: hoi lai so tien; L2: ghi nhan 35,000 |

---

### 5. Yeu cau nghiep vu moi — test_new_requirements.py

| ID | Ten Test | Input | Dau ra mong doi |
|----|----------|-------|-----------------|
| BR-01 | test_han_muc_khong_duoc_nho_hon_so_tien_da_chi | Da chi 400k, giam xp 300k | 400, "khong duoc nho hon so tien da chi" |
| BR-02 | test_sap_xep_hu_tiet_kiem_hoan_thanh | Nop du hu A; hu B chua du | List: B truoc A; nang muc tieu A -> ca 2 chua xong |
| BR-03 | test_xac_nhan_otp_dang_ky_thanh_cong | OTP sai -> OTP dung | Sai: 400; Dung: 200 + access_token |
| — | test_tao_danh_muc_chi_bat_buoc_toi_thieu_1000 | Han muc < 1000 | 400, "toi thieu la 1.000 d" |

---

### 6. Bao mat & Business Rules — test_security_agent.py

#### SQLi Protection (6 payload, parametrize)

| Payload | Endpoint | Dau ra mong doi |
|---------|----------|-----------------|
| `' OR '1'='1` (x6) | POST /api/auth/dang-nhap (email) | 400/401/422, khong co "traceback" |
| SQLi payloads | POST /api/giao-dich (ghi_chu) | Khong crash 500 |
| SQLi payloads | GET /api/giao-dich/tim-kiem?tu_khoa= | Khong crash 500 |

#### XSS Protection (5 payload, parametrize)

| Payload | Endpoint | Dau ra mong doi |
|---------|----------|-----------------|
| `<script>alert(1)</script>` (x5) | PUT /api/nguoi-dung/toi (ho_ten) | 200/400/422, khong crash |
| XSS payloads | POST /api/danh-muc (ten_dm) | Khong crash 500 |

#### Boundary Values

| Test | Input | Dau ra mong doi |
|------|-------|-----------------|
| so_tien bang 0 | so_tien=0 | 400 |
| so_tien am | so_tien=-1 | 400 |
| so_tien rat lon | so_tien=999 ty | Khong crash 500 |
| Email khong hop le | Email khong co @ | 400/422 |
| Payload rong | Body {} | 400/422 |

#### Business Rules

| ID | Ten Test | Dau ra mong doi |
|----|----------|-----------------|
| BR-04 | test_br04_phan_quyen_nguoi_dung_rieng_biet | User A sua/xoa GD B -> 403 |
| BR-05 | test_br05_token_het_han_bi_tu_choi | JWT het han -> 401 moi endpoint |
| BR-06 | test_br06_khong_co_token_bi_tu_choi | Khong token -> 401 tren 6 endpoint |

---

## Lenh chay test (tu thu muc goc du an)

```powershell
# Kich hoat moi truong ao
.\venv\Scripts\activate

# Chay TOAN BO bo test
pytest tests/ -v

# Chay tung file
pytest tests/test_nguoi_dung.py -v
pytest tests/test_giao_dich.py -v
pytest tests/test_ngan_sach.py -v
pytest tests/test_ai.py -v
pytest tests/test_new_requirements.py -v
pytest tests/test_security_agent.py -v

# Chay 1 test case cu the
pytest tests/test_giao_dich.py::test_tc04_them_giao_dich_canh_bao_vuot_ngan_sach -v

# Loc theo ID
pytest tests/ -k "tc04 or tc07 or br01" -v

# Dung ngay khi co loi dau tien
pytest tests/ -x -v

# Coverage HTML (mo htmlcov/index.html)
pytest tests/ --cov=app --cov-report=html

# HTML report dep
pytest tests/ --html=report.html --self-contained-html

# Chay song song (nhanh hon)
pytest tests/ -n auto -v
```

---

## Cach doc ket qua terminal

```
PASSED  <- test thanh cong (xanh la)
FAILED  <- test that bai (do) - xem AssertionError phia duoi
ERROR   <- loi khi chay fixture/setup
SKIPPED <- bo qua (dung @pytest.mark.skip)

Vi du:
  tests/test_nguoi_dung.py::test_dang_ky_thanh_cong          PASSED
  tests/test_ai.py::test_tc08_ai_engine_timeout_503          FAILED
    AssertionError: assert 200 == 503

Tom tat cuoi:
  ========= 45 passed, 2 failed, 1 skipped in 8.34s =========
```

---

## Cach them Test Case moi

### Buoc 1: Chon file phu hop

| Module | File |
|--------|------|
| Nguoi dung / Auth | test_nguoi_dung.py |
| Giao dich | test_giao_dich.py |
| Ngan sach / Hu | test_ngan_sach.py |
| AI chatbot / bao cao | test_ai.py |
| Yeu cau moi / BR | test_new_requirements.py |
| Bao mat / SQLi / XSS | test_security_agent.py |

### Buoc 2: Viet test theo chuan AAA

```python
def test_tc_XX_mo_ta_ket_qua_mong_doi(client, auth_headers_a, cat_chi_a):
    """
    TC-XX / UC-XX:
    Input: Mo ta input cu the
    Ket qua mong doi: Mo ta dau ra
    """
    # -- ARRANGE: Chuan bi du lieu --
    payload = {
        "so_tien": 100000,
        "loai_gd": "chi",
        "ma_dm": cat_chi_a.ma_dm,
    }
    # -- ACT: Goi API --
    response = client.post("/api/giao-dich", json=payload, headers=auth_headers_a)
    # -- ASSERT: Kiem tra ket qua --
    assert response.status_code == 201
    data = response.json()
    assert data["so_tien"] == 100000
```

### Buoc 3: Fixtures co san tu conftest.py

| Fixture | Mo ta |
|---------|-------|
| client | FastAPI TestClient (khong can server that) |
| db_session | SQLite in-memory, tu xoa sau moi test |
| user_a | Nguoi dung A da tao san |
| user_b | Nguoi dung B da tao san (kiem tra cach ly) |
| auth_headers_a | JWT Bearer token cua User A |
| auth_headers_b | JWT Bearer token cua User B |
| cat_chi_a | Danh muc Chi "An uong" thuoc User A |
| cat_thu_a | Danh muc Thu "Luong" thuoc User A |

### Buoc 4: Mock AI khi can

```python
from unittest.mock import patch
from app.services.ai_service import AIService

def test_ai_khong_goi_gemini(client, auth_headers_a):
    with patch.object(AIService, "_call_gemini_with_timeout") as mock_g:
        mock_g.return_value = "Phan hoi mock"
        res = client.get("/api/ai/bao-cao?thang=9&nam=2026", headers=auth_headers_a)
        assert res.status_code == 200
        mock_g.assert_called_once()
```

---

## Cai thu vien test tuy chon

```powershell
pip install pytest-cov      # Coverage HTML/XML
pip install pytest-xdist    # Chay song song: pytest -n auto
pip install pytest-html     # Bao cao dep: pytest --html=report.html
pip install pytest-mock     # mocker.patch(...)
pip install pytest-timeout  # Gioi han thoi gian: @pytest.mark.timeout(5)
```

---

## Lien quan den cac Skill khac

| Skill | Lien quan |
|-------|-----------|
| backend-test-suite | Cach chay pytest, cau truc chung |
| database-isolation | Co che SQLite in-memory, cach ly du lieu |
| mocking-ai-engine | Mock Gemini API trong test AI |
| ai-testing-agent | Agent tu dong sinh payload SQLi/XSS |
| frontend-test-suite | Kiem thu giao dien bang Playwright |
