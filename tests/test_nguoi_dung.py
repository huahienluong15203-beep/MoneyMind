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

def test_quen_mat_khau_email_khong_ton_tai(client):
    """Kiểm thử yêu cầu quên mật khẩu với email chưa đăng ký -> 404"""
    resp = client.post("/api/auth/quen-mat-khau", json={"email": "notfound12345@gmail.com"})
    assert resp.status_code == status.HTTP_404_NOT_FOUND
    assert "chưa được đăng ký" in resp.json()["detail"].lower()

def test_quen_mat_khau_va_dat_lai_thanh_cong(client, user_a):
    """Kiểm thử toàn bộ luồng quên mật khẩu và đặt lại mật khẩu mới"""
    # 1. Yêu cầu mã OTP đặt lại mật khẩu
    resp_forgot = client.post("/api/auth/quen-mat-khau", json={"email": user_a.email})
    assert resp_forgot.status_code == status.HTTP_200_OK
    data_forgot = resp_forgot.json()
    otp_code = data_forgot.get("dev_otp")
    assert otp_code is not None

    # 2. Xác nhận OTP và đặt mật khẩu mới
    new_pass = "brand_new_secret_pass_888"
    resp_reset = client.post("/api/auth/dat-lai-mat-khau", json={
        "email": user_a.email,
        "otp": otp_code,
        "new_password": new_pass
    })
    assert resp_reset.status_code == status.HTTP_200_OK

    # 3. Đăng nhập bằng mật khẩu mới thành công
    resp_login_new = client.post("/api/auth/dang-nhap", json={
        "email": user_a.email,
        "password": new_pass
    })
    assert resp_login_new.status_code == status.HTTP_200_OK
    assert "access_token" in resp_login_new.json()

    # 4. Đăng nhập bằng mật khẩu cũ phải thất bại
    resp_login_old = client.post("/api/auth/dang-nhap", json={
        "email": user_a.email,
        "password": "password123"
    })
    assert resp_login_old.status_code == status.HTTP_401_UNAUTHORIZED

def test_dang_nhap_don_thiet_bi_kickout_thiet_bi_cu(client, user_a):
    """
    Kiểm thử cơ chế đăng nhập đơn thiết bị (Single Active Session):
    - Khi thiết bị 1 đăng nhập -> hợp lệ
    - Khi thiết bị 2 đăng nhập vào cùng tài khoản -> thiết bị 2 hợp lệ
    - Thiết bị 1 ngay lập tức bị từ chối (401 Unauthorized), header X-Logout-Reason: concurrent_login
    """
    # 1. Thiết bị 1 đăng nhập
    resp1 = client.post("/api/auth/dang-nhap", json={
        "email": user_a.email,
        "password": "password123"
    })
    assert resp1.status_code == status.HTTP_200_OK
    token_dev1 = resp1.json()["access_token"]

    # Thiết bị 1 kiểm tra session -> Hợp lệ
    res_chk1 = client.get("/api/auth/check-session", headers={"Authorization": f"Bearer {token_dev1}"})
    assert res_chk1.status_code == status.HTTP_200_OK
    assert res_chk1.json()["status"] == "valid"

    # 2. Thiết bị 2 đăng nhập vào cùng tài khoản
    resp2 = client.post("/api/auth/dang-nhap", json={
        "email": user_a.email,
        "password": "password123"
    })
    assert resp2.status_code == status.HTTP_200_OK
    token_dev2 = resp2.json()["access_token"]

    # Thiết bị 2 kiểm tra session -> Hợp lệ
    res_chk2 = client.get("/api/auth/check-session", headers={"Authorization": f"Bearer {token_dev2}"})
    assert res_chk2.status_code == status.HTTP_200_OK
    assert res_chk2.json()["status"] == "valid"

    # 3. Thiết bị 1 gọi lại API (/check-session hoặc bất kỳ endpoint nào) -> BỊ OUT NGAY LẬP TỨC (401)
    res_kick = client.get("/api/auth/check-session", headers={"Authorization": f"Bearer {token_dev1}"})
    assert res_kick.status_code == status.HTTP_401_UNAUTHORIZED
    assert res_kick.headers.get("X-Logout-Reason") == "concurrent_login"
    assert "thiết bị khác" in res_kick.json()["detail"].lower()

    # 4. Kiểm tra endpoint legacy /check-session cũng hoạt động đồng nhất
    res_kick_legacy = client.get("/check-session", headers={"Authorization": f"Bearer {token_dev1}"})
    assert res_kick_legacy.status_code == status.HTTP_401_UNAUTHORIZED
    assert res_kick_legacy.headers.get("X-Logout-Reason") == "concurrent_login"


