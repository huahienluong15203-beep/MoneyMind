import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import get_password_hash, create_access_token
from app.models import NguoiDung, DanhMuc, GiaoDich, NganSach, MucTieuTietKiem, BaoCaoAI
from app.main import app

# Sử dụng SQLite In-Memory Database cho test suite
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine_test = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)

@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine_test)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine_test)

@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def user_a(db_session):
    user = NguoiDung(
        email="user_a@test.com",
        ho_ten="Người Dùng A",
        mat_khau_hash=get_password_hash("password123"),
        trang_thai="hoat_dong",
        so_lan_sai=0,
        ngay_tao=datetime.utcnow()
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def user_b(db_session):
    user = NguoiDung(
        email="user_b@test.com",
        ho_ten="Người Dùng B",
        mat_khau_hash=get_password_hash("password456"),
        trang_thai="hoat_dong",
        so_lan_sai=0,
        ngay_tao=datetime.utcnow()
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def auth_headers_a(user_a):
    token = create_access_token(data={"sub": user_a.email, "user_id": user_a.ma_nd})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def auth_headers_b(user_b):
    token = create_access_token(data={"sub": user_b.email, "user_id": user_b.ma_nd})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def cat_chi_a(db_session, user_a):
    cat = DanhMuc(
        ma_nd=user_a.ma_nd,
        ten_dm="Ăn uống",
        loai_dm="chi",
        icon="utensils",
        mau_sac="#f43f5e",
        han_muc=1000000.0
    )
    db_session.add(cat)
    db_session.commit()
    db_session.refresh(cat)
    return cat

@pytest.fixture
def cat_thu_a(db_session, user_a):
    cat = DanhMuc(
        ma_nd=user_a.ma_nd,
        ten_dm="Lương",
        loai_dm="thu",
        icon="wallet",
        mau_sac="#10b981",
        han_muc=0.0
    )
    db_session.add(cat)
    db_session.commit()
    db_session.refresh(cat)
    return cat
