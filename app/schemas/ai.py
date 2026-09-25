from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class BaoCaoAIResponse(BaseModel):
    ma_bc: Optional[int] = None
    thang_nam: str
    noi_dung_tom_tat: str
    goi_y_dieu_chinh: List[str]
    goi_y_ngan_sach: Optional[Dict[str, Any]] = None
    cached: bool = False
    ngay_tao: Optional[datetime] = None
    badge_an_danh: str = "🔒 Cam kết bảo mật: Dữ liệu đã được ẩn danh hoá trước khi phân tích AI"

class GoiYNganSachItem(BaseModel):
    danh_muc: str
    ma_dm: int
    han_muc_de_xuat: float
    ly_do: str

class GoiYNganSachResponse(BaseModel):
    thang_nam_tiep_theo: str
    danh_sach_goi_y: List[GoiYNganSachItem]
    loi_khuyen_chung: str

class HoiDapAIRequest(BaseModel):
    cau_hoi: str = Field(..., min_length=1, description="Câu hỏi ngôn ngữ tự nhiên về chi tiêu")
    lich_su_chat: Optional[List[Dict[str, str]]] = Field(None, description="Lịch sử trò chuyện đa lượt gần nhất")

class HoiDapAIResponse(BaseModel):
    tra_loi: str
    badge_an_danh: str = "🔒 Dữ liệu cá nhân đã được ẩn danh hoá trước khi xử lý"
