"""
Kiểm thử tự động cho module Ngân Sách
Bao gồm:
- TC-06: Đặt ngân sách với han_muc = 0 -> 400
- UC006: Thiết lập & cập nhật ngân sách
- UC007: Trạng thái cảnh báo vượt ngân sách
"""
from datetime import datetime
from fastapi import status
from app.models import DanhMuc, GiaoDich, NganSach, ThongBao
from app.services.ngan_sach_service import NganSachService

def test_tc06_thiet_lap_ngan_sach_bang_khong(client, cat_chi_a, auth_headers_a):
    """
    TC-06:
    Input: Đặt ngân sách với han_muc = 0
    Kết quả mong đợi: Trả về lỗi 400 theo luồng A1
    """
    payload = {
        "ma_dm": cat_chi_a.ma_dm,
        "thang_nam": datetime.now().strftime("%Y-%m"),
        "han_muc": 0.0
    }
    response = client.post("/api/ngan-sach", json=payload, headers=auth_headers_a)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "lớn hơn 0" in response.json()["detail"].lower()

def test_uc006_thiet_lap_va_sua_ngan_sach(client, cat_chi_a, auth_headers_a):
    """UC006: Thiết lập hạn mức ngân sách và chỉnh sửa hạn mức"""
    thang_nam = datetime.now().strftime("%Y-%m")

    # 1. Thiết lập ngân sách hợp lệ
    create_payload = {
        "ma_dm": cat_chi_a.ma_dm,
        "thang_nam": thang_nam,
        "han_muc": 2000000.0
    }
    res_post = client.post("/api/ngan-sach", json=create_payload, headers=auth_headers_a)
    assert res_post.status_code == status.HTTP_201_CREATED
    data = res_post.json()
    assert data["han_muc"] == 2000000.0
    ma_ns = data["ma_ns"]

    # 2. Xem danh sách ngân sách
    res_get = client.get(f"/api/ngan-sach?thang_nam={thang_nam}", headers=auth_headers_a)
    assert res_get.status_code == status.HTTP_200_OK
    items = res_get.json()
    assert len(items) >= 1
    assert items[0]["ma_ns"] == ma_ns

    # 3. Chỉnh sửa hạn mức ngân sách
    update_payload = {"han_muc": 2500000.0}
    res_put = client.put(f"/api/ngan-sach/{ma_ns}", json=update_payload, headers=auth_headers_a)
    assert res_put.status_code == status.HTTP_200_OK
    assert res_put.json()["han_muc"] == 2500000.0

def test_thang_moi_khong_canh_bao_thang_cu_va_chua_cap_han_muc(client, user_a, auth_headers_a, db_session):
    """
    Kiểm thử nghiệp vụ khi bước sang tháng mới:
    1. Chi tiêu tháng cũ vượt hạn mức không làm phát sinh cảnh báo sai ở tháng mới.
    2. Hũ chi tiêu ở tháng mới mặc định là (chưa cấp hạn mức) và không tự động trừ tiền ví chính.
    """
    from app.models.danh_muc import DanhMuc
    from app.models.giao_dich import GiaoDich
    from app.models.ngan_sach import NganSach
    from app.models.thong_bao import ThongBao
    from app.services.ngan_sach_service import NganSachService
    from datetime import timedelta

    # 1. Tạo khoản thu ban đầu 10,000,000 đ vào ví chính
    tx_thu = GiaoDich(
        ma_nd=user_a.ma_nd,
        so_tien=10000000.0,
        loai_gd="thu",
        ghi_chu="Lương khởi tạo",
        ngay_gd=datetime.now()
    )
    db_session.add(tx_thu)

    # 2. Tạo hũ Ăn uống với ngân sách tháng cũ (tháng trước)
    dm = DanhMuc(
        ma_nd=user_a.ma_nd,
        ten_dm="Ăn uống tháng cũ",
        loai_dm="chi",
        han_muc=2000000.0
    )
    db_session.add(dm)
    db_session.commit()
    db_session.refresh(dm)

    now = datetime.now()
    # Tháng trước
    first_day_this_month = datetime(now.year, now.month, 1)
    last_month_date = first_day_this_month - timedelta(days=5)
    last_month_ym = last_month_date.strftime("%Y-%m")

    ns_old = NganSach(
        ma_nd=user_a.ma_nd,
        ma_dm=dm.ma_dm,
        thang_nam=last_month_ym,
        han_muc=2000000.0,
        so_tien_da_chi=2500000.0
    )
    db_session.add(ns_old)

    # Chi 2,500,000 đ trong tháng trước (vượt 2,000,000 đ)
    tx_old = GiaoDich(
        ma_nd=user_a.ma_nd,
        ma_dm=dm.ma_dm,
        so_tien=2500000.0,
        loai_gd="chi",
        ghi_chu="Ăn tiệc tháng trước",
        ngay_gd=last_month_date
    )
    db_session.add(tx_old)

    # Tháng này chi 40,000 đ
    tx_new = GiaoDich(
        ma_nd=user_a.ma_nd,
        ma_dm=dm.ma_dm,
        so_tien=400000.0,
        loai_gd="chi",
        ghi_chu="Ăn sáng tháng này",
        ngay_gd=now
    )
    db_session.add(tx_new)
    db_session.commit()

    # Xóa các thông báo cũ để kiểm tra
    db_session.query(ThongBao).filter(ThongBao.ma_nd == user_a.ma_nd).delete()
    db_session.commit()

    # 3. Kích hoạt kiểm tra cảnh báo đăng nhập
    NganSachService.check_and_generate_login_budget_notifications(db_session, user_a)

    # Xác nhận: KHÔNG có thông báo vượt hạn mức tháng mới
    notifs = db_session.query(ThongBao).filter(ThongBao.ma_nd == user_a.ma_nd).all()
    over_alerts = [n for n in notifs if "vượt" in (n.tieu_de or "").lower()]
    assert len(over_alerts) == 0

    # 4. Kiểm tra danh mục trả về qua API: chưa được cấp hạn mức tháng này
    res_dm = client.get("/api/danh-muc", headers=auth_headers_a)
    assert res_dm.status_code == status.HTTP_200_OK
    cats = res_dm.json()
    cat_match = next((c for c in cats if c["ma_dm"] == dm.ma_dm), None)
    assert cat_match is not None
    assert cat_match["han_muc"] == 0.0


def test_ket_chuyen_ngan_sach_tu_dong_va_tra_cuu_lich_su(client, db_session, user_a, auth_headers_a):
    """
    Kiểm thử tự động kết chuyển số dư hạn mức chưa dùng hết từ tháng trước sang tháng mới
    (ví dụ: Ăn uống 1 triệu, chi 800k -> còn 200k chuyển sang tháng sau)
    và kiểm tra API tra cứu lịch sử kết chuyển.
    """
    from app.models.ket_chuyen_ngan_sach import KetChuyenNganSach

    # 1. Tạo danh mục Ăn uống
    dm = DanhMuc(
        ma_nd=user_a.ma_nd,
        ten_dm="Ăn uống tháng 9",
        loai_dm="chi",
        han_muc=1000000.0
    )
    db_session.add(dm)
    db_session.commit()
    db_session.refresh(dm)

    # 2. Tạo bản ghi ngân sách tháng 9/2026: hạn mức 1,000,000 đ
    ns_t9 = NganSach(
        ma_nd=user_a.ma_nd,
        ma_dm=dm.ma_dm,
        thang_nam="2026-09",
        han_muc=1000000.0,
        so_tien_da_chi=0.0
    )
    db_session.add(ns_t9)

    # 3. Tạo giao dịch chi tiêu trong tháng 9/2026: 800,000 đ
    gd_t9 = GiaoDich(
        ma_nd=user_a.ma_nd,
        ma_dm=dm.ma_dm,
        loai_gd="chi",
        so_tien=800000.0,
        ngay_gd=datetime(2026, 9, 20, 12, 0, 0),
        ghi_chu="Ăn uống tháng 9"
    )
    db_session.add(gd_t9)
    db_session.commit()

    # 4. Kích hoạt tự động kết chuyển sang tháng 10/2026
    rolled = NganSachService.tu_dong_ket_chuyen_thang_moi(db_session, user_a.ma_nd, "2026-10")
    assert len(rolled) >= 1
    rolled_match = next((r for r in rolled if r["name"] == "Ăn uống tháng 9"), None)
    assert rolled_match is not None
    assert rolled_match["amount"] == 200000.0

    # 5. Kiểm tra bản ghi lưu trong bảng KetChuyenNganSach
    kc = db_session.query(KetChuyenNganSach).filter(
        KetChuyenNganSach.ma_nd == user_a.ma_nd,
        KetChuyenNganSach.ma_dm == dm.ma_dm,
        KetChuyenNganSach.thang_nguon == "2026-09",
        KetChuyenNganSach.thang_dich == "2026-10"
    ).first()
    assert kc is not None
    assert kc.han_muc_thang_truoc == 1000000.0
    assert kc.da_chi_thang_truoc == 800000.0
    assert kc.so_tien_chuyen == 200000.0

    # 6. Kiểm tra NganSach tháng 10/2026 đã nhận được 200,000 đ số dư chuyển sang
    ns_t10 = db_session.query(NganSach).filter(
        NganSach.ma_nd == user_a.ma_nd,
        NganSach.ma_dm == dm.ma_dm,
        NganSach.thang_nam == "2026-10"
    ).first()
    assert ns_t10 is not None
    assert ns_t10.so_du_chuyen_sang == 200000.0
    assert ns_t10.han_muc == 200000.0

    # 7. Kiểm tra API tra cứu lịch sử kết chuyển: GET /api/ngan-sach/ket-chuyen
    res = client.get("/api/ngan-sach/ket-chuyen", headers=auth_headers_a)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert len(data) >= 1
    item = next((k for k in data if k["ma_dm"] == dm.ma_dm), None)
    assert item is not None
    assert item["thang_nguon"] == "2026-09"
    assert item["thang_dich"] == "2026-10"
    assert item["so_tien_chuyen"] == 200000.0
    assert item["han_muc_thang_truoc"] == 1000000.0
    assert item["da_chi_thang_truoc"] == 800000.0

    # 8. Kiểm tra tính Idempotent (không bị kết chuyển đúp nếu gọi lại)
    rolled_second = NganSachService.tu_dong_ket_chuyen_thang_moi(db_session, user_a.ma_nd, "2026-10")
    duplicate_match = [r for r in rolled_second if r["name"] == "Ăn uống tháng 9"]
    assert len(duplicate_match) == 0
