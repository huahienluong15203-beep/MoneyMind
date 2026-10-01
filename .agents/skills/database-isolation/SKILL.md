---
name: database-isolation
description: >
  Tu dong tao moi schema, cach ly du lieu va tu dong rollback sau moi phien test.
  Dam bao moi test chay doc lap, khong lam ban CSDL that cua du an.
---

# SKILL-02: Database Isolation

## Mo ta
Moi test case chay tren SQLite :memory: rieng biet, duoc tao va xoa hoan toan
sau moi function test. Khong co shared state giua cac test.

Nguyen tac:
1. Truoc moi test -> Base.metadata.create_all() tao lai toan bo schema
2. Chay test -> thao tac voi DB in-memory
3. Sau moi test -> Base.metadata.drop_all() xoa sach, giai phong bo nho

---

## Cach hoat dong trong conftest.py

```python
# tests/conftest.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.core.database import Base, get_db
from app.main import app

# 1. Tao SQLite In-Memory Engine (doc lap voi tai_chinh.db that)
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine_test = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool          # Quan trong: dung chung 1 connection cho cac thread
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)

# 2. Fixture: tao/xoa schema truoc-sau moi test function
@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine_test)   # Tao tat ca bang
    db = TestingSessionLocal()
    try:
        yield db                                   # Tra DB cho test dung
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine_test)  # Xoa sach, rollback tu dong

# 3. Fixture: TestClient ghi de get_db() bang DB in-memory
@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db  # Override dependency
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()                    # Don dep sau test
```

---

## Tai sao dung StaticPool?

SQLite :memory: mac dinh mo moi connection se tao DB moi. StaticPool buoc
SQLAlchemy dung chung 1 connection, dam bao TestClient va db_session nhin
cung 1 DB.

```python
# DUNG (dung chung 1 connection)
engine_test = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool   # <- Bat buoc phai co
)

# SAI (moi thread co DB khac nhau -> test fail khong ro ly do)
engine_test = create_engine("sqlite:///:memory:")
```

---

## Cac Fixture co san trong conftest.py

```python
# Tao san user de test (khong can POST /api/auth/dang-ky)
@pytest.fixture
def user_a(db_session):
    user = NguoiDung(
        email="user_a@test.com",
        ho_ten="Nguoi Dung A",
        mat_khau_hash=get_password_hash("password123"),
        trang_thai="hoat_dong",
        so_lan_sai=0,
        ngay_tao=datetime.utcnow()
    )
    db_session.add(user); db_session.commit(); db_session.refresh(user)
    return user

# Tao san JWT token hop le cho user_a
@pytest.fixture
def auth_headers_a(user_a):
    token = create_access_token(data={"sub": user_a.email, "user_id": user_a.ma_nd})
    return {"Authorization": f"Bearer {token}"}

# Tao san danh muc chi (hu "An uong" voi han muc 1tr)
@pytest.fixture
def cat_chi_a(db_session, user_a):
    cat = DanhMuc(
        ma_nd=user_a.ma_nd, ten_dm="An uong",
        loai_dm="chi", icon="utensils",
        mau_sac="#f43f5e", han_muc=1000000.0
    )
    db_session.add(cat); db_session.commit(); db_session.refresh(cat)
    return cat
```

---

## Them fixture tuy chinh moi

Them vao `tests/conftest.py`:

```python
@pytest.fixture
def ngan_sach_a(db_session, user_a, cat_chi_a):
    """Tao san ngan sach thang nay cho user_a danh muc chi"""
    from app.models import NganSach
    from datetime import datetime
    ns = NganSach(
        ma_nd=user_a.ma_nd,
        ma_dm=cat_chi_a.ma_dm,
        thang_nam=datetime.now().strftime("%Y-%m"),
        han_muc=2000000.0,
        so_tien_da_chi=0.0
    )
    db_session.add(ns); db_session.commit(); db_session.refresh(ns)
    return ns
```

Sau do dung trong test:

```python
def test_canh_bao_vuot_ngan_sach(client, auth_headers_a, cat_chi_a, ngan_sach_a):
    # ngan_sach_a da ton tai trong DB test
    res = client.post("/api/giao-dich", json={"so_tien": 2500000, "loai_gd": "chi", ...})
    assert res.json()["canh_bao"]["vuot_ngan_sach"] is True
```

---

## Kiem tra: test co thuc su doc lap?

```powershell
# Chay cung 1 test 10 lan - phai luon PASSED, khong co shared state
pytest tests/test_giao_dich.py::test_tc04_them_giao_dich_canh_bao_vuot_ngan_sach -v --count=10
# (can pip install pytest-repeat)
```

---

## Luu y quan trong

- Khong bao gio dung `scope="session"` cho `db_session` fixture - se gay loi du lieu dan xen.
- Neu test fail va DB khong duoc drop -> chay lai se tu dong tao moi (create_all idempotent).
- File `tai_chinh.db` that KHONG BAO GIO bi anh huong boi bo test.
