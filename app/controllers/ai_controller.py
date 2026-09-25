import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.nguoi_dung import NguoiDung
from app.services.ai_service import AIService
from app.schemas.ai import (
    BaoCaoAIResponse, GoiYNganSachResponse,
    HoiDapAIRequest, HoiDapAIResponse
)

router = APIRouter(prefix="/api/ai", tags=["Tính năng thông minh AI (UC010, UC011, UC012)"])

@router.get("/bao-cao", response_model=BaoCaoAIResponse, summary="Xem báo cáo tài chính AI tháng (UC010 & TC-07 & TC-08)")
def lay_bao_cao_ai_thang(
    thang: Optional[int] = Query(None, ge=1, le=12, description="Tháng báo cáo (1-12)"),
    nam: Optional[int] = Query(None, ge=2020, description="Năm báo cáo"),
    db: Session = Depends(get_db),
    current_user: NguoiDung = Depends(get_current_user)
):
    """
    UC010 & BR-04 & TC-07 & TC-08:
    - Kiểm tra bảng bao_cao_ai (cache DB). Nếu đã có, trả về ngay mà không gọi Gemini (TC-07).
    - Nếu chưa có, ẩn danh hoá dữ liệu (NFR-04, BR-03), gọi AI Engine với timeout 5s (NFR-03).
    - Nếu timeout > 5s, trả về mã 503 (TC-08).
    - Lưu kết quả vào bao_cao_ai và trả về.
    """
    now = datetime.now()
    thang_val = thang or now.month
    nam_val = nam or now.year

    # Gọi AIService để lấy hoặc tạo báo cáo (kèm cache)
    bc, is_cached = AIService.sinh_bao_cao_thang(
        db=db,
        ma_nd=current_user.ma_nd,
        thang=thang_val,
        nam=nam_val
    )

    goi_y_list = []
    if bc.goi_y_dieu_chinh:
        try:
            goi_y_list = json.loads(bc.goi_y_dieu_chinh)
        except Exception:
            goi_y_list = [bc.goi_y_dieu_chinh]

    goi_y_ns = None
    if bc.goi_y_ngan_sach:
        try:
            goi_y_ns = json.loads(bc.goi_y_ngan_sach)
        except Exception:
            pass

    return BaoCaoAIResponse(
        ma_bc=bc.ma_bc,
        thang_nam=bc.thang_nam,
        noi_dung_tom_tat=bc.noi_dung_tom_tat,
        goi_y_dieu_chinh=goi_y_list,
        goi_y_ngan_sach=goi_y_ns,
        cached=is_cached,
        ngay_tao=bc.ngay_tao
    )

@router.get("/goi-y-ngan-sach", response_model=GoiYNganSachResponse, summary="Nhận gợi ý hạn mức ngân sách AI (UC011)")
def lay_goi_y_ngan_sach(
    db: Session = Depends(get_db),
    current_user: NguoiDung = Depends(get_current_user)
):
    """
    UC011: AI phân tích lịch sử chi tiêu và đề xuất hạn mức ngân sách tham khảo
    cho tháng tiếp theo kèm lý do ngắn gọn.
    """
    res = AIService.goi_y_ngan_sach(db=db, ma_nd=current_user.ma_nd)
    return GoiYNganSachResponse(**res)

@router.post("/hoi-dap", response_model=HoiDapAIResponse, summary="Hỏi đáp tự nhiên với AI (UC012 & TC-09)")
def hoi_dap_ai(
    payload: HoiDapAIRequest,
    db: Session = Depends(get_db),
    current_user: NguoiDung = Depends(get_current_user)
):
    """
    UC012 & TC-09:
    - Đặt câu hỏi tự nhiên về chi tiêu cá nhân.
    - Dữ liệu được ẩn danh hóa trước khi gửi cho AI.
    - AI từ chối trả lời nếu câu hỏi nằm ngoài phạm vi tài chính cá nhân (TC-09).
    """
    tra_loi = AIService.hoi_dap_ai(
        db=db,
        ma_nd=current_user.ma_nd,
        cau_hoi=payload.cau_hoi,
        lich_su_chat=payload.lich_su_chat
    )
    return HoiDapAIResponse(tra_loi=tra_loi)
