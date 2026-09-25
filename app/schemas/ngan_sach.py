from typing import Optional
from pydantic import BaseModel, Field

class NganSachCreate(BaseModel):
    ma_dm: int = Field(..., description="Mã danh mục chi tiêu")
    thang_nam: str = Field(..., pattern=r"^\d{4}-\d{2}$", description="Tháng năm áp dụng định dạng YYYY-MM")
    han_muc: float = Field(..., description="Hạn mức ngân sách (phải > 0)")

class NganSachUpdate(BaseModel):
    han_muc: float = Field(..., description="Hạn mức ngân sách mới (phải > 0)")

class NganSachResponse(BaseModel):
    ma_ns: int
    ma_nd: int
    ma_dm: int
    thang_nam: str
    han_muc: float
    so_tien_da_chi: float
    canh_bao_da_gui: bool
    ten_dm: Optional[str] = None
    ty_le: Optional[float] = None

    class Config:
        from_attributes = True

class CanhBaoNgayResponse(BaseModel):
    ma_ns: int
    ten_dm: str
    thang_nam: str
    han_muc: float
    so_tien_da_chi: float
    ty_le: float
    muc_do: str  # "nguy_co" (>= 90%) hoặc "vuot" (>= 100%)
    noi_dung: str
