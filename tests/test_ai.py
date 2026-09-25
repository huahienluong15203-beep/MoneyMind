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
