"""
Kiểm thử tự động cho 3 yêu cầu cập nhật mới:
1. Không cho phép giảm hạn mức danh mục chi nhỏ hơn số tiền đã chi tiêu
2. Hũ tiết kiệm khi hoàn thành đưa xuống dưới, khi sửa nâng mục tiêu thì nổi lên trên
3. Đăng ký tài khoản bắt buộc xác nhận OTP qua Gmail
"""
from fastapi import status
from app.models.xac_nhan_otp import XacNhanOTP
from datetime import datetime, timedelta

def test_han_muc_khong_duoc_nho_hon_so_tien_da_chi(client, user_a, auth_headers_a, db_session):
    # 1. Tạo danh mục chi với hạn mức ban đầu 1,000,000 đ
    dm_res = client.post("/api/danh-muc", json={
        "ten_dm": "Ăn vặt",
        "loai_dm": "chi",
        "han_muc": 1000000.0
    }, headers=auth_headers_a)
    assert dm_res.status_code == status.HTTP_201_CREATED
    cat_id = dm_res.json()["ma_dm"]

    # 2. Tạo giao dịch chi 400,000 đ trong danh mục này
    tx_res = client.post("/api/giao-dich", json={
        "ma_dm": cat_id,
        "so_tien": 400000.0,
        "loai_gd": "chi",
        "ghi_chu": "Trà sữa"
    }, headers=auth_headers_a)
    assert tx_res.status_code == status.HTTP_201_CREATED

    # 3. Thử sửa hạn mức xuống 300,000 đ (nhỏ hơn 400,000 đ đã chi) -> Bắt buộc bị từ chối 400
    edit_fail = client.put(f"/api/danh-muc/{cat_id}", json={
        "han_muc": 300000.0
    }, headers=auth_headers_a)
    assert edit_fail.status_code == status.HTTP_400_BAD_REQUEST
    assert "không được nhỏ hơn số tiền đã chi" in edit_fail.json()["detail"].lower()

    # 4. Sửa hạn mức lên 500,000 đ (lớn hơn 400,000 đ đã chi) -> Thành công
    edit_ok = client.put(f"/api/danh-muc/{cat_id}", json={
        "han_muc": 500000.0
    }, headers=auth_headers_a)
    assert edit_ok.status_code == status.HTTP_200_OK
    assert float(edit_ok.json()["han_muc"]) == 500000.0

def test_sap_xep_hu_tiet_kiem_hoan_thanh(client, user_a, auth_headers_a):
    # 1. Tạo mục tiêu tiết kiệm A: 1,000,000 đ
    res_a = client.post("/api/muc-tieu", json={
        "ten_muc_tieu": "Mua sách",
        "so_tien_muc_tieu": 1000000.0
    }, headers=auth_headers_a)
    assert res_a.status_code == status.HTTP_201_CREATED
    id_a = res_a.json()["id"]

    # 2. Tạo mục tiêu tiết kiệm B: 2,000,000 đ
    res_b = client.post("/api/muc-tieu", json={
        "ten_muc_tieu": "Du lịch hè",
        "so_tien_muc_tieu": 2000000.0
    }, headers=auth_headers_a)
    assert res_b.status_code == status.HTTP_201_CREATED
    id_b = res_b.json()["id"]

    # Nạp thu nhập vào ví chính trước
    client.post("/api/danh-muc", json={
        "ten_dm": "Lương tháng",
        "loai_dm": "thu",
        "han_muc": 5000000.0
    }, headers=auth_headers_a)

    # Nạp 1,000,000 đ vào mục tiêu A để hoàn thành 100%
    nop_res = client.post(f"/api/muc-tieu/{id_a}/nop", json={
        "amount": 1000000.0
    }, headers=auth_headers_a)
    assert nop_res.status_code == status.HTTP_200_OK

    # Lấy danh sách hũ tiết kiệm: hũ B (chưa hoàn thành) phải đứng trước hũ A (đã hoàn thành)
    list_res = client.get("/api/muc-tieu", headers=auth_headers_a)
    assert list_res.status_code == status.HTTP_200_OK
    goals = list_res.json()
    assert goals[0]["id"] == id_b  # Chưa hoàn thành nổi lên trên
    assert goals[1]["id"] == id_a  # Đã hoàn thành chìm xuống dưới

    # Khi sửa hũ A nâng mục tiêu lên 1,500,000 đ -> hũ A trở lại chưa hoàn thành
    update_res = client.put(f"/api/muc-tieu/{id_a}", json={
        "so_tien_muc_tieu": 1500000.0
    }, headers=auth_headers_a)
    assert update_res.status_code == status.HTTP_200_OK

    # Lấy lại danh sách: cả 2 hũ đều chưa hoàn thành
    list_res2 = client.get("/api/muc-tieu", headers=auth_headers_a)
    goals2 = list_res2.json()
    assert float(goals2[0]["current_amount"]) < float(goals2[0]["target_amount"])
    assert float(goals2[1]["current_amount"]) < float(goals2[1]["target_amount"])

def test_xac_nhan_otp_dang_ky_thanh_cong(client, db_session):
    new_email = "testotpuser@gmail.com"
    otp_code = "654321"

    # Thêm record OTP hợp lệ vào CSDL
    otp_rec = XacNhanOTP(
        email=new_email,
        otp_code=otp_code,
        het_han=datetime.utcnow() + timedelta(minutes=10),
        da_dung=False
    )
    db_session.add(otp_rec)
    db_session.commit()

    # Xác thực sai OTP -> 400
    fail_res = client.post("/api/auth/xac-nhan-dang-ky", json={
        "email": new_email,
        "password": "mypassword123",
        "otp": "000000"
    })
    assert fail_res.status_code == status.HTTP_400_BAD_REQUEST

    # Xác thực đúng OTP -> 200, trả về access_token
    ok_res = client.post("/api/auth/xac-nhan-dang-ky", json={
        "email": new_email,
        "password": "mypassword123",
        "otp": otp_code,
        "full_name": "Nguyen Van Test"
    })
    assert ok_res.status_code == status.HTTP_200_OK
    data = ok_res.json()
    assert "access_token" in data
    assert data["user"]["email"] == new_email
