# -*- coding: utf-8 -*-
from datetime import datetime
from app.models.nguoi_dung import NguoiDung
from app.models.lich_su_ai import LichSuAI
from app.services.ai_service import AIService

def test_ai_interaction_logging(db_session, user_a):
    """Kiểm thử tính năng ghi nhật ký tương tác AI theo ngày (UC012 Logging)"""
    ma_nd = user_a.ma_nd

    # Xóa log cũ của user nếu có
    db_session.query(LichSuAI).filter(LichSuAI.ma_nd == ma_nd).delete()
    db_session.commit()

    # 1. Tương tác 1: Thêm giao dịch
    q1 = "lúc trưa tôi vừa đi ăn xuất cơm gà hết 150k"
    res1 = AIService.hoi_dap_ai(db_session, ma_nd, q1)
    assert res1 is not None

    # 2. Tương tác 2: Đính chính
    q2 = "tôi nhầm (trưa nay tôi đi ăn lẩu hết 150k mới đúng)"
    res2 = AIService.hoi_dap_ai(db_session, ma_nd, q2)
    assert res2 is not None

    # 3. Tương tác 3: Tra cứu
    q3 = "hôm nay tôi đã tiêu những gì"
    res3 = AIService.hoi_dap_ai(db_session, ma_nd, q3)
    assert res3 is not None

    # 4. Kiểm tra lấy lịch sử gom nhóm theo ngày
    lich_su = AIService.lay_lich_su_ai_theo_ngay(db_session, ma_nd)
    assert lich_su["tong_so"] >= 3
    assert lich_su["tong_so_ngay"] >= 1

    today_group = lich_su["cac_ngay"][0]
    assert "Hôm nay" in today_group["ngay_hien_thi"]
    assert len(today_group["nhat_ky"]) >= 3

    # Kiểm tra log mới nhất là câu hỏi tra cứu
    latest_log = today_group["nhat_ky"][0]
    assert "tiêu những gì" in latest_log["cau_hoi"] or "hôm nay" in latest_log["cau_hoi"]
    assert latest_log["thoi_gian"] != ""
    assert latest_log["icon"] != ""

    # 5. Kiểm tra tìm kiếm từ khóa
    kq_tim_kiem = AIService.lay_lich_su_ai_theo_ngay(db_session, ma_nd, tu_khoa="cơm gà")
    assert kq_tim_kiem["tong_so"] >= 1
    assert any("cơm gà" in item["cau_hoi"].lower() for day in kq_tim_kiem["cac_ngay"] for item in day["nhat_ky"])

    # 6. Kiểm tra xóa 1 log
    log_to_delete = latest_log["ma_log"]
    del_count = AIService.xoa_lich_su_ai(db_session, ma_nd, ma_log=log_to_delete)
    assert del_count == 1

    lich_su_sau_xoa = AIService.lay_lich_su_ai_theo_ngay(db_session, ma_nd)
    assert lich_su_sau_xoa["tong_so"] == lich_su["tong_so"] - 1

    # 7. Kiểm tra xóa toàn bộ log
    del_all = AIService.xoa_lich_su_ai(db_session, ma_nd)
    assert del_all >= 2
    lich_su_rong = AIService.lay_lich_su_ai_theo_ngay(db_session, ma_nd)
    assert lich_su_rong["tong_so"] == 0

def test_api_ai_logs_endpoints(client, auth_headers_a):
    """Kiểm thử API GET /api/ai/lich-su và DELETE /api/ai/lich-su"""
    # 1. Gửi câu hỏi qua API /api/ai/hoi-dap
    client.post("/api/ai/hoi-dap", json={"cau_hoi": "Ăn trưa 45k cơm sườn"}, headers=auth_headers_a)
    client.post("/api/ai/hoi-dap", json={"cau_hoi": "Hôm nay tôi đã tiêu những gì?"}, headers=auth_headers_a)

    # 2. Gọi GET /api/ai/lich-su
    res = client.get("/api/ai/lich-su", headers=auth_headers_a)
    assert res.status_code == 200
    data = res.json()
    assert "cac_ngay" in data
    assert data["tong_so"] >= 2
    assert len(data["cac_ngay"]) >= 1

    first_day = data["cac_ngay"][0]
    assert len(first_day["nhat_ky"]) >= 2
    first_log_id = first_day["nhat_ky"][0]["ma_log"]

    # 3. Gọi DELETE /api/ai/lich-su/{ma_log}
    res_del_one = client.delete(f"/api/ai/lich-su/{first_log_id}", headers=auth_headers_a)
    assert res_del_one.status_code == 200

    # 4. Gọi DELETE /api/ai/lich-su (xóa tất cả)
    res_del_all = client.delete("/api/ai/lich-su", headers=auth_headers_a)
    assert res_del_all.status_code == 200
    assert res_del_all.json()["status"] == "ok"

def test_ai_session_lifecycle_and_deletion(client, auth_headers_a):
    """Kiểm thử tính năng quản lý nhật ký theo phiên trò chuyện (Sessions)"""
    phien_1 = "test_phien_001"
    phien_2 = "test_phien_002"

    # Gửi 2 tin nhắn trong phiên 1
    client.post("/api/ai/hoi-dap", json={"cau_hoi": "Ăn phở 40k", "ma_phien": phien_1}, headers=auth_headers_a)
    client.post("/api/ai/hoi-dap", json={"cau_hoi": "Uống cafe 25k", "ma_phien": phien_1}, headers=auth_headers_a)

    # Gửi 1 tin nhắn trong phiên 2 (phiên mới sau khi thoát ra vào lại)
    client.post("/api/ai/hoi-dap", json={"cau_hoi": "Đổ xăng xe máy 60k", "ma_phien": phien_2}, headers=auth_headers_a)

    # Lấy lịch sử và kiểm tra gom theo phiên
    res = client.get("/api/ai/lich-su", headers=auth_headers_a)
    assert res.status_code == 200
    data = res.json()
    assert "cac_phien" in data
    assert data["tong_so_phien"] >= 2

    # Lọc riêng phiên 1
    res_p1 = client.get(f"/api/ai/lich-su?ma_phien={phien_1}", headers=auth_headers_a)
    data_p1 = res_p1.json()
    assert data_p1["tong_so_phien"] == 1
    assert data_p1["cac_phien"][0]["ma_phien"] == phien_1
    assert data_p1["cac_phien"][0]["so_luong"] == 2

    # Xóa riêng phiên 1
    del_res = client.delete(f"/api/ai/lich-su?ma_phien={phien_1}", headers=auth_headers_a)
    assert del_res.status_code == 200

    # Kiểm tra phiên 1 đã bị xóa, phiên 2 vẫn còn
    res_after = client.get(f"/api/ai/lich-su?ma_phien={phien_1}", headers=auth_headers_a)
    assert res_after.json()["tong_so_phien"] == 0

    res_p2 = client.get(f"/api/ai/lich-su?ma_phien={phien_2}", headers=auth_headers_a)
    assert res_p2.json()["tong_so_phien"] == 1
    assert res_p2.json()["cac_phien"][0]["ma_phien"] == phien_2

def test_ai_logs_gioi_han_10_ban_ghi_gan_nhat(db_session, user_a):
    """Kiểm thử nghiệp vụ chỉ ghi lại tối đa 10 nhật ký tương tác gần nhất"""
    ma_nd = user_a.ma_nd
    # Xóa sạch log cũ
    db_session.query(LichSuAI).filter(LichSuAI.ma_nd == ma_nd).delete()
    db_session.commit()

    # Thêm 15 bản ghi liên tiếp
    for i in range(15):
        AIService.luu_nhat_ky_ai(
            db=db_session,
            ma_nd=ma_nd,
            cau_hoi=f"Câu hỏi số {i+1}",
            tra_loi=f"Câu trả lời số {i+1}",
            loai_hanh_dong="tu_van",
            ma_phien="phien_test_10"
        )

    # Kiểm tra trong DB chỉ còn tối đa 10 bản ghi
    total_in_db = db_session.query(LichSuAI).filter(LichSuAI.ma_nd == ma_nd).count()
    assert total_in_db == 10

    # Lấy lịch sử qua hàm lay_lich_su_ai_theo_ngay
    res = AIService.lay_lich_su_ai_theo_ngay(db_session, ma_nd)
    assert res["tong_so"] == 10

    # Bản ghi mới nhất phải là câu hỏi số 15
    first_session = res["cac_phien"][0]
    all_q = [item["cau_hoi"] for item in first_session["nhat_ky"]]
    assert "Câu hỏi số 15" in all_q
    # Bản ghi cũ nhất số 1, 2, 3, 4, 5 phải bị dọn dẹp
    assert "Câu hỏi số 1" not in all_q
    assert "Câu hỏi số 5" not in all_q

