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
