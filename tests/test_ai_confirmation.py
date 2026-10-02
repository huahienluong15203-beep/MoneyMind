import pytest
from datetime import datetime
from app.core.database import SessionLocal
from app.models.nguoi_dung import NguoiDung
from app.models.giao_dich import GiaoDich
from app.models.muc_tieu_tiet_kiem import MucTieuTietKiem
from app.models.danh_muc import DanhMuc
from app.services.ai_service import AIService

@pytest.fixture
def db_session():
    db = SessionLocal()
    yield db
    db.close()

@pytest.fixture
def test_user(db_session):
    user = db_session.query(NguoiDung).filter(NguoiDung.email == "test@example.com").first()
    if not user:
        user = db_session.query(NguoiDung).first()
    return user

def test_xac_nhan_xoa_giao_dich(db_session, test_user):
    """Kiểm tra quy trình 2 bước: AI phải hỏi xác nhận trước khi xóa giao dịch."""
    # 1. Tạo giao dịch mẫu
    tx = GiaoDich(
        so_tien=85000.0,
        loai_gd="chi",
        ghi_chu="Ăn bún chả xác nhận",
        ngay_gd=datetime.now(),
        ma_nd=test_user.ma_nd
    )
    db_session.add(tx)
    db_session.commit()
    db_session.refresh(tx)
    tx_id = tx.ma_gd

    # Bước 1: Yêu cầu xóa
    res1 = AIService.xu_ly_giao_dich_tu_nhien(db_session, test_user.ma_nd, "xóa giao dịch vừa rồi đi")
    assert "XÁC NHẬN XÓA GIAO DỊCH" in res1
    assert f"#{tx_id}" in res1

    # Kiểm tra giao dịch CHƯA bị xóa
    tx_check = db_session.query(GiaoDich).filter(GiaoDich.ma_gd == tx_id).first()
    assert tx_check is not None

    # Bước 2a: Người dùng hủy thao tác
    hist = [
        {"role": "user", "content": "xóa giao dịch vừa rồi đi"},
        {"role": "assistant", "content": res1}
    ]
    res_cancel = AIService.xu_ly_giao_dich_tu_nhien(db_session, test_user.ma_nd, "thôi đừng xóa nữa", lich_su_chat=hist)
    assert "hủy thao tác xóa" in res_cancel
    assert db_session.query(GiaoDich).filter(GiaoDich.ma_gd == tx_id).first() is not None

    # Bước 2b: Người dùng xác nhận xóa
    res_confirm = AIService.xu_ly_giao_dich_tu_nhien(db_session, test_user.ma_nd, "đồng ý", lich_su_chat=hist)
    assert "Đã xóa giao dịch thành công" in res_confirm
    assert db_session.query(GiaoDich).filter(GiaoDich.ma_gd == tx_id).first() is None

def test_xac_nhan_xoa_hu_tiet_kiem(db_session, test_user):
    """Kiểm tra quy trình 2 bước: AI phải hỏi xác nhận trước khi xóa hũ tiết kiệm."""
    goal = MucTieuTietKiem(
        ten_muc_tieu="Hũ Thử Nghiệm Xác Nhận 2026",
        so_tien_muc_tieu=2000000.0,
        so_tien_hien_tai=200000.0,
        ma_nd=test_user.ma_nd,
        trang_thai="dang_thuc_hien"
    )
    db_session.add(goal)
    db_session.commit()
    db_session.refresh(goal)
    goal_id = goal.ma_mt

    # Bước 1: Yêu cầu xóa
    res1 = AIService.xu_ly_giao_dich_tu_nhien(db_session, test_user.ma_nd, "xóa hũ Thử Nghiệm Xác Nhận 2026")
    assert "XÁC NHẬN XÓA HŨ TIẾT KIỆM" in res1
    assert f"#{goal_id}" in res1
    assert db_session.query(MucTieuTietKiem).filter(MucTieuTietKiem.ma_mt == goal_id).first() is not None

    # Bước 2: Xác nhận xóa
    hist = [
        {"role": "user", "content": "xóa hũ Thử Nghiệm Xác Nhận 2026"},
        {"role": "assistant", "content": res1}
    ]
    res_confirm = AIService.xu_ly_giao_dich_tu_nhien(db_session, test_user.ma_nd, "xác nhận xóa", lich_su_chat=hist)
    assert "Đã xóa hũ tiết kiệm" in res_confirm
    assert db_session.query(MucTieuTietKiem).filter(MucTieuTietKiem.ma_mt == goal_id).first() is None
