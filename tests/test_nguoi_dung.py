"""
Kiểm thử tự động cho module Người Dùng & Xác Thực
Bao gồm:
- TC-01: Đăng ký với email đã tồn tại -> 400
- TC-02: Đăng nhập sai mật khẩu liên tiếp -> khóa tài khoản
- UC001 & UC002: Đăng ký thành công, đăng nhập thành công, xem và sửa thông tin cá nhân
"""
from fastapi import status

def test_tc01_dang_ky_email_da_ton_tai(client, user_a):
    """
    TC-01:
    Input: Đăng ký với email đã tồn tại
    Kết quả mong đợi: Trả về lỗi 400, thông báo email đã được sử dụng
    """
    payload = {
        "email": user_a.email,
        "password": "newpassword123",
        "ho_ten": "Trùng Lặp"
    }
    response = client.post("/api/auth/dang-ky", json=payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "email đã được sử dụng" in response.json()["detail"].lower()

def test_tc02_dang_nhap_sai_mat_khau_khoa_tai_khoan(client, user_a):
    """
    TC-02:
    Input: Đăng nhập sai mật khẩu 6 lần liên tiếp
    Kết quả mong đợi: Từ lần thứ 5-6, tài khoản bị tạm khoá đăng nhập (A2, 403)
    """
    payload = {
        "email": user_a.email,
        "password": "wrongpassword"
    }
    # Nhập sai các lần đầu
    for i in range(4):
        resp = client.post("/api/auth/dang-nhap", json=payload)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    # Lần thứ 5 đạt ngưỡng khóa
    resp5 = client.post("/api/auth/dang-nhap", json=payload)
    assert resp5.status_code == status.HTTP_403_FORBIDDEN
    assert "tạm khóa" in resp5.json()["detail"].lower()

    # Lần thứ 6 tiếp tục bị từ chối truy cập do đang bị khóa
    resp6 = client.post("/api/auth/dang-nhap", json=payload)
    assert resp6.status_code == status.HTTP_403_FORBIDDEN
    assert "tạm khóa" in resp6.json()["detail"].lower()

def test_dang_ky_thanh_cong(client):
    """Kiểm thử đăng ký tài khoản mới thành công"""
    payload = {
        "email": "newuser@example.com",
        "password": "secretpassword",
        "ho_ten": "Người Dùng Mới"
    }
    response = client.post("/api/auth/dang-ky", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert "thong_bao" in data

def test_dang_nhap_thanh_cong(client, user_a):
    """Kiểm thử đăng nhập thành công trả về access token và refresh token"""
    payload = {
        "email": user_a.email,
        "password": "password123"
    }
    response = client.post("/api/auth/dang-nhap", json=payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

def test_uc002_xem_va_cap_nhat_thong_tin(client, user_a, auth_headers_a):
    """UC002: Xem và cập nhật thông tin cá nhân"""
    # 1. Xem thông tin
    res_get = client.get("/api/nguoi-dung/toi", headers=auth_headers_a)
    assert res_get.status_code == status.HTTP_200_OK
    assert res_get.json()["email"] == user_a.email

    # 2. Cập nhật thông tin
    update_data = {
        "ho_ten": "Họ Tên Đã Đổi",
        "occupation": "Kỹ sư phần mềm",
        "goals": "Mua nhà 2027"
    }
    res_put = client.put("/api/nguoi-dung/toi", json=update_data, headers=auth_headers_a)
    assert res_put.status_code == status.HTTP_200_OK
    data = res_put.json()
    assert data["ho_ten"] == "Họ Tên Đã Đổi"
    assert data["occupation"] == "Kỹ sư phần mềm"
