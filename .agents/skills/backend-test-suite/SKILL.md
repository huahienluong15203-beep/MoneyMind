---
name: backend-test-suite
description: >
  Chay tu dong toan bo bo test case backend MoneyMind bang pytest + httpx.
  Bao gom: cau truc bo test, cach doc ket qua, cach them test case moi, CI/CD.
---

# SKILL-01: Backend Test Suite

## Mo ta
Bo test backend chay HOAN TOAN TU DONG, khong can khoi dong server that,
khong anh huong du lieu that. Cong cu:
- **pytest** - framework test chinh
- **fastapi.testclient + httpx** - gui HTTP request gia lap den API
- **SQLite :memory:** - database test tach biet (xem SKILL-02: database-isolation)
- **unittest.mock.patch** - mock Gemini AI (xem SKILL-03: mocking-ai-engine)

---

## Cau truc thu muc tests/

```
tests/
  conftest.py               <- Fixtures dung chung cho moi test
  test_nguoi_dung.py        <- TC-01, TC-02, UC001, UC002
  test_giao_dich.py         <- TC-03, TC-04, TC-05, TC-10, UC005
  test_ngan_sach.py         <- CRUD ngan sach + canh bao hu
  test_ai.py                <- TC-07, TC-08, TC-09, UC011
  test_new_requirements.py  <- BR-01, BR-02, BR-03
```

---

## Lenh chay (tu thu muc goc du an)

```powershell
# Kich hoat moi truong ao
.\venv\Scripts\activate

# Chay TOAN BO bo test
pytest tests/ -v

# Chay 1 file cu the
pytest tests/test_giao_dich.py -v

# Chay 1 test case cu the
pytest tests/test_giao_dich.py::test_tc04_them_giao_dich_canh_bao_vuot_ngan_sach -v

# Loc theo keyword
pytest tests/ -k "tc04 or tc07" -v

# Bao cao coverage HTML (mo htmlcov/index.html)
pytest tests/ --cov=app --cov-report=html

# Dung ngay khi co test fail dau tien
pytest tests/ -x -v
```

---

## Cach doc ket qua terminal

```
PASSED  <- test thanh cong (xanh la)
FAILED  <- test that bai (do) - xem AssertionError phia duoi
ERROR   <- loi khi chay fixture/setup
SKIPPED <- bo qua (dung @pytest.mark.skip)

Vi du:
  tests/test_nguoi_dung.py::test_dang_ky_thanh_cong PASSED
  tests/test_ai.py::test_tc08_ai_engine_timeout_503 FAILED
    AssertionError: assert 200 == 503
```

---

## Cau truc 1 test case chuan (AAA Pattern)

```python
def test_ten_function_mo_ta_ket_qua(client, auth_headers_a, cat_chi_a):
    """TC-XX / UC-XX: Input => Output mong doi"""
    # ARRANGE: Chuan bi du lieu
    payload = {
        "so_tien": 100000,
        "loai_gd": "chi",
        "ma_dm": cat_chi_a.ma_dm,
    }
    # ACT: Goi API
    response = client.post("/api/giao-dich", json=payload, headers=auth_headers_a)
    # ASSERT: Kiem tra ket qua
    assert response.status_code == 201
    data = response.json()
    assert data["so_tien"] == 100000
```

---

## Bang Test Cases hien co

| TC/UC | File                     | Mo ta                                     |
|-------|--------------------------|-------------------------------------------|
| TC-01 | test_nguoi_dung.py       | Dang ky email trung -> 400                |
| TC-02 | test_nguoi_dung.py       | Sai MK 5 lan -> khoa TK 15 phut          |
| TC-03 | test_giao_dich.py        | So tien am -> 400                         |
| TC-04 | test_giao_dich.py        | Vuot han muc ngan sach -> canh bao + 201  |
| TC-05 | test_giao_dich.py        | Sua GD kich hoat lai kiem tra ngan sach   |
| TC-07 | test_ai.py               | Bao cao AI tu cache -> khong goi Gemini   |
| TC-08 | test_ai.py               | AI timeout -> 503, khong crash server     |
| TC-09 | test_ai.py               | Hoi ngoai pham vi -> AI tu choi           |
| TC-10 | test_giao_dich.py        | User A xoa GD cua User B -> 403           |
| BR-01 | test_new_requirements.py | Han muc < da chi -> 400                   |
| BR-02 | test_new_requirements.py | Sap xep hu TK hoan thanh xuong duoi       |
| BR-03 | test_new_requirements.py | Dang ky OTP bat buoc hop le               |
| UC001 | test_nguoi_dung.py       | Dang ky thanh cong -> 201                 |
| UC002 | test_nguoi_dung.py       | Dang nhap -> JWT access + refresh token   |
| UC005 | test_giao_dich.py        | Tim kiem & phan trang giao dich           |
| UC011 | test_ai.py               | Goi y han muc ngan sach thang toi         |

---

## CI/CD - GitHub Actions (.github/workflows/test.yml)

```yaml
name: Backend Auto Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    env:
      GEMINI_API_KEY: test-mock-key-ci
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with: { python-version: "3.10" }
      - run: pip install -r requirements.txt pytest-cov
      - run: pytest tests/ -v --cov=app --cov-report=xml
```

---

## Cai them thu vien test tuy chon

```powershell
pip install pytest-cov     # Coverage HTML/XML
pip install pytest-xdist   # Song song: pytest -n auto
pip install pytest-html    # Bao cao dep: pytest --html=report.html
pip install pytest-mock    # mocker.patch(...) ngan hon
```
