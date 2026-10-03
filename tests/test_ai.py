"""
Kiểm thử tự động cho module AI (UC010, UC011, UC012)
Bao gồm:
- TC-07: Gọi lại API báo cáo AI tháng đã có trong cache -> không gọi Gemini lần 2 (A1)
- TC-08: AI Engine mô phỏng timeout > 5s -> trả 503 (A2)
- TC-09: Hỏi câu hỏi ngoài phạm vi -> từ chối trả lời (A1)
"""
from datetime import datetime
from unittest.mock import patch
from fastapi import status, HTTPException
from app.models import BaoCaoAI
from app.services.ai_service import AIService

def test_tc07_bao_cao_ai_cache_db(client, db_session, user_a, auth_headers_a):
    """
    TC-07:
    Input: Gọi lại API báo cáo AI tháng đã có trong cache
    Kết quả mong đợi: Không gọi Gemini API lần 2; trả kết quả từ bao_cao_ai (A1)
    """
    thang = 8
    nam = 2026
    thang_nam = f"{nam:04d}-{thang:02d}"

    # Đưa sẵn bản ghi vào cache DB
    cached_bc = BaoCaoAI(
        ma_nd=user_a.ma_nd,
        thang_nam=thang_nam,
        noi_dung_tom_tat="Báo cáo đã lưu trong cache DB.",
        goi_y_dieu_chinh='["Gợi ý cache 1", "Gợi ý cache 2", "Gợi ý cache 3"]',
        ngay_tao=datetime.utcnow()
    )
    db_session.add(cached_bc)
    db_session.commit()

    # Gọi API với mock _call_gemini_with_timeout để kiểm tra không bị gọi
    with patch.object(AIService, "_call_gemini_with_timeout") as mock_gemini:
        res = client.get(f"/api/ai/bao-cao?thang={thang}&nam={nam}", headers=auth_headers_a)
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["cached"] is True
        assert data["noi_dung_tom_tat"] == "Báo cáo đã lưu trong cache DB."
        assert len(data["goi_y_dieu_chinh"]) == 3
        # Đảm bảo không gọi tới Gemini API
        mock_gemini.assert_not_called()

def test_tc08_ai_engine_timeout_503(client, user_a, auth_headers_a):
    """
    TC-08:
    Input: AI Engine mô phỏng timeout > 5 giây (mock)
    Kết quả mong đợi: Trả về mã 503 theo luồng A2, không làm sập tiến trình
    """
    with patch.object(AIService, "_call_gemini_with_timeout", side_effect=HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="AI Engine phản hồi quá thời gian cho phép (> 5 giây). Vui lòng thử lại sau."
    )):
        res = client.get("/api/ai/bao-cao?thang=9&nam=2026", headers=auth_headers_a)
        assert res.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "quá thời gian cho phép" in res.json()["detail"].lower()

def test_tc09_hoi_dap_ngoai_pham_vi(client, auth_headers_a):
    """
    TC-09:
    Input: Hỏi câu hỏi ngoài phạm vi (ví dụ: "nên mua cổ phiếu nào?")
    Kết quả mong đợi: AI từ chối trả lời theo system prompt (A1)
    """
    payload = {"cau_hoi": "Tôi nên mua cổ phiếu nào để có lãi nhanh nhất?"}
    res = client.post("/api/ai/hoi-dap", json=payload, headers=auth_headers_a)
    assert res.status_code == status.HTTP_200_OK
    tra_loi = res.json()["tra_loi"]
    # Kiểm tra từ chối tư vấn đầu tư theo system prompt
    assert "xin lỗi" in tra_loi.lower() or "không có thẩm quyền" in tra_loi.lower() or "quản lý chi tiêu" in tra_loi.lower()

def test_uc011_goi_y_ngan_sach(client, cat_chi_a, auth_headers_a):
    """UC011: Lấy gợi ý hạn mức ngân sách tháng tới"""
    res = client.get("/api/ai/goi-y-ngan-sach", headers=auth_headers_a)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert "danh_sach_goi_y" in data
    assert "thang_nam_tiep_theo" in data
    assert len(data["danh_sach_goi_y"]) >= 1
    assert data["danh_sach_goi_y"][0]["danh_muc"] == cat_chi_a.ten_dm

def test_ai_canh_bao_tu_ngu_khong_phu_hop(client, auth_headers_a):
    """Kiểm tra AI phát hiện từ ngữ thô tục/tiêu cực và đưa ra cảnh báo chuẩn mực"""
    res = client.post("/api/ai/hoi-dap", json={"cau_hoi": "đm ứng dụng này"}, headers=auth_headers_a)
    assert res.status_code == 200
    tra_loi = res.json()["tra_loi"]
    assert "cảnh báo về ngôn từ không phù hợp" in tra_loi.lower() or "văn minh, tích cực" in tra_loi.lower()

def test_ai_tu_choi_ngoai_pham_vi_thoi_tiet(client, auth_headers_a):
    """Kiểm tra AI từ chối các câu hỏi lạc đề ngoài phạm vi tài chính cá nhân"""
    res = client.post("/api/ai/hoi-dap", json={"cau_hoi": "dự báo thời tiết hôm nay thế nào?"}, headers=auth_headers_a)
    assert res.status_code == 200
    tra_loi = res.json()["tra_loi"]
    assert "chỉ chuyên trách hỗ trợ" in tra_loi.lower() or "ngoài phạm vi" in tra_loi.lower()

def test_ai_chao_hoi_ngan_gon(client, auth_headers_a):
    """Kiểm tra AI phản hồi lời chào ngắn gọn, không tuôn báo cáo dài"""
    res = client.post("/api/ai/hoi-dap", json={"cau_hoi": "xin chào"}, headers=auth_headers_a)
    assert res.status_code == 200
    tra_loi = res.json()["tra_loi"]
    assert "xin chào bạn" in tra_loi.lower() or "trợ lý ai tài chính" in tra_loi.lower()

def test_ai_hoi_so_tien_va_ghi_nhan_da_luot(client, db_session, user_a, auth_headers_a):
    """
    Kiểm tra xử lý đúng trọng tâm:
    1. Người dùng kể 'nãy tôi vừa đi ăn bún chả' (chưa có số tiền) -> AI hỏi số tiền
    2. Người dùng trả lời '35k' -> AI tự động kết hợp ngữ cảnh và tạo giao dịch thành công
    """
    # Lượt 1: Kể chi tiêu nhưng thiếu số tiền
    res1 = client.post("/api/ai/hoi-dap", json={"cau_hoi": "nãy tôi vừa đi ăn bún chả"}, headers=auth_headers_a)
    assert res1.status_code == 200
    tra_loi_1 = res1.json()["tra_loi"]
    assert "bún chả" in tra_loi_1.lower()
    assert "bao nhiêu tiền" in tra_loi_1.lower()
    assert "ăn uống" in tra_loi_1.lower()

    # Lượt 2: Người dùng gửi số tiền '35k'
    res2 = client.post("/api/ai/hoi-dap", json={"cau_hoi": "35k"}, headers=auth_headers_a)
    assert res2.status_code == 200
    tra_loi_2 = res2.json()["tra_loi"]
    assert "ghi nhận giao dịch thành công" in tra_loi_2.lower()
    assert "35,000" in tra_loi_2 or "35.000" in tra_loi_2
