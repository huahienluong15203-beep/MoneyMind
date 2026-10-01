from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class KetChuyenNganSachResponse(BaseModel):
    ma_kc: int
    ma_nd: int
    ma_dm: int
    ten_dm: Optional[str] = "Danh mục"
    thang_nguon: str
    thang_dich: str
    han_muc_thang_truoc: float
    da_chi_thang_truoc: float
    so_tien_chuyen: float
    ngay_tao: datetime
    ghi_chu: Optional[str] = None

    class Config:
        from_attributes = True
