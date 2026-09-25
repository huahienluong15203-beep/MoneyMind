"""
Kiểm thử tự động cho module Ngân Sách
Bao gồm:
- TC-06: Đặt ngân sách với han_muc = 0 -> 400
- UC006: Thiết lập & cập nhật ngân sách
- UC007: Trạng thái cảnh báo vượt ngân sách
"""
from datetime import datetime
from fastapi import status

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
