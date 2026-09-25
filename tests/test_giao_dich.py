"""
Kiểm thử tự động cho module Giao Dịch
Bao gồm:
- TC-03: Thêm giao dịch chi với so_tien = -50000 -> 400
- TC-04: Thêm giao dịch khiến tổng chi danh mục vượt han_muc -> trả kèm cảnh báo ngay
- TC-05: Sửa số tiền một giao dịch từ dưới sang trên hạn mức -> chạy lại kiểm tra ngân sách
- TC-10: Người dùng A gọi API xem/sửa giao dịch của người dùng B -> 403 (NFR-07)
- UC005: Tra cứu & phân trang
"""
from datetime import datetime
from fastapi import status
from app.models import NganSach, GiaoDich

def test_tc03_them_giao_dich_so_tien_am(client, cat_chi_a, auth_headers_a):
    """
    TC-03:
    Input: Thêm giao dịch chi với so_tien = -50000
    Kết quả mong đợi: Trả về lỗi 400, không lưu vào CSDL
    """
    payload = {
        "so_tien": -50000,
        "loai_gd": "chi",
        "ma_dm": cat_chi_a.ma_dm,
        "ghi_chu": "Giao dịch lỗi"
    }
    response = client.post("/api/giao-dich", json=payload, headers=auth_headers_a)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "lớn hơn 0" in response.json()["detail"].lower()

def test_tc04_them_giao_dich_canh_bao_vuot_ngan_sach(client, db_session, user_a, cat_chi_a, auth_headers_a):
    """
    TC-04:
    Input: Thêm giao dịch khiến tổng chi danh mục vượt han_muc đã đặt
    Kết quả mong đợi: Response trả kèm cảnh báo vượt ngân sách; bản ghi giao dịch vẫn được lưu (NFR-02)
    """
    thang_nam = datetime.now().strftime("%Y-%m")
    # Thiết lập hạn mức ngân sách: 500,000 đ
    ns = NganSach(
        ma_nd=user_a.ma_nd,
        ma_dm=cat_chi_a.ma_dm,
        thang_nam=thang_nam,
        han_muc=500000.0,
        so_tien_da_chi=0.0
    )
    db_session.add(ns)
    db_session.commit()

    # Thêm giao dịch chi 600,000 đ (vượt hạn mức 500k)
    payload = {
        "so_tien": 600000.0,
        "loai_gd": "chi",
        "ma_dm": cat_chi_a.ma_dm,
        "ghi_chu": "Tiệc liên hoan"
    }
    response = client.post("/api/giao-dich", json=payload, headers=auth_headers_a)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()

    # Kiểm tra giao dịch đã được lưu
    assert data["so_tien"] == 600000.0

    # Kiểm tra cảnh báo ngân sách trả về ngay trong response (NFR-02)
    canh_bao = data["canh_bao"]
    assert canh_bao["vuot_ngan_sach"] is True
    assert canh_bao["co_canh_bao"] is True
    assert canh_bao["so_tien_da_chi"] == 600000.0
    assert "vượt ngân sách" in canh_bao["thong_bao"].lower()

def test_tc05_sua_giao_dich_kich_hoat_lai_canh_bao(client, db_session, user_a, cat_chi_a, auth_headers_a):
    """
    TC-05:
    Input: Sửa số tiền một giao dịch từ dưới sang trên hạn mức
    Kết quả mong đợi: Hệ thống chạy lại kiểm tra ngân sách và trả cảnh báo tương ứng
    """
    thang_nam = datetime.now().strftime("%Y-%m")
    # Đặt hạn mức: 500,000 đ
    ns = NganSach(
        ma_nd=user_a.ma_nd,
        ma_dm=cat_chi_a.ma_dm,
        thang_nam=thang_nam,
        han_muc=500000.0,
        so_tien_da_chi=0.0
    )
    db_session.add(ns)
    db_session.commit()

    # Tạo giao dịch ban đầu 200,000 đ (chưa vượt)
    tx = GiaoDich(
        ma_nd=user_a.ma_nd,
        ma_dm=cat_chi_a.ma_dm,
        so_tien=200000.0,
        loai_gd="chi",
        ngay_gd=datetime.now(),
        ghi_chu="Ăn trưa"
    )
    db_session.add(tx)
    db_session.commit()
    db_session.refresh(tx)

    # Sửa số tiền lên 700,000 đ (vượt hạn mức 500k)
    update_payload = {"so_tien": 700000.0}
    res_put = client.put(f"/api/giao-dich/{tx.ma_gd}", json=update_payload, headers=auth_headers_a)
    assert res_put.status_code == status.HTTP_200_OK
    data = res_put.json()

    # Kiểm tra đã kích hoạt lại cảnh báo ngân sách
    assert data["canh_bao"]["vuot_ngan_sach"] is True
    assert data["canh_bao"]["so_tien_da_chi"] == 700000.0

def test_tc10_nfr07_cach_ly_du_lieu_nguoi_dung(client, db_session, user_b, auth_headers_a):
    """
    TC-10 & NFR-07:
    Input: Người dùng A gọi API sửa/xóa giao dịch thuộc về Người dùng B
    Kết quả mong đợi: Trả về lỗi 403, không trả hoặc thao tác dữ liệu của người khác
    """
    # Tạo giao dịch thuộc về người dùng B
    tx_b = GiaoDich(
        ma_nd=user_b.ma_nd,
        ma_dm=1,
        so_tien=150000.0,
        loai_gd="chi",
        ngay_gd=datetime.now(),
        ghi_chu="Giao dịch của B"
    )
    db_session.add(tx_b)
    db_session.commit()
    db_session.refresh(tx_b)

    # Người dùng A cố tình sửa giao dịch của B
    res_edit = client.put(f"/api/giao-dich/{tx_b.ma_gd}", json={"so_tien": 999999.0}, headers=auth_headers_a)
    assert res_edit.status_code == status.HTTP_403_FORBIDDEN

    # Người dùng A cố tình xóa giao dịch của B
    res_del = client.delete(f"/api/giao-dich/{tx_b.ma_gd}", headers=auth_headers_a)
    assert res_del.status_code == status.HTTP_403_FORBIDDEN

def test_uc005_tim_kiem_loc_giao_dich(client, db_session, user_a, cat_chi_a, auth_headers_a):
    """UC005: Tìm kiếm & phân trang giao dịch"""
    # Thêm vài giao dịch mẫu
    for i in range(5):
        t = GiaoDich(
            ma_nd=user_a.ma_nd,
            ma_dm=cat_chi_a.ma_dm,
            so_tien=50000.0 * (i + 1),
            loai_gd="chi",
            ghi_chu=f"Khoản chi số {i+1}",
            ngay_gd=datetime.now()
        )
        db_session.add(t)
    db_session.commit()

    # Tra cứu với bộ lọc từ khóa
    res = client.get("/api/giao-dich/tim-kiem?tu_khoa=Khoản chi&page=1&limit=2", headers=auth_headers_a)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["total_pages"] == 3
