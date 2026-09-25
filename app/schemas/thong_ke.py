from typing import List, Dict, Any
from pydantic import BaseModel, Field

class ChiTietDanhMuc(BaseModel):
    ma_dm: int
    ten_dm: str
    so_tien: float
    ty_le: float
    mau_sac: str
    icon: str

class XuHuongThang(BaseModel):
    thang: str
    tong_thu: float
    tong_chi: float

class TongQuanResponse(BaseModel):
    tong_thu: float
    tong_chi: float
    so_du: float
    chi_theo_danh_muc: List[ChiTietDanhMuc] = []
    xu_huong_6_thang: List[XuHuongThang] = []
    giao_dich_gan_day: List[Dict[str, Any]] = []

# Legacy alias
class SummaryResponse(BaseModel):
    tong_thu: float
    tong_chi: float
    so_du: float
