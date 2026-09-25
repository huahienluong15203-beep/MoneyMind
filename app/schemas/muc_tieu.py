from typing import Optional
from pydantic import BaseModel, Field

class MucTieuCreate(BaseModel):
    ten_muc_tieu: Optional[str] = None
    title: Optional[str] = None
    so_tien_muc_tieu: Optional[float] = None
    target_amount: Optional[float] = None
    han_chot: Optional[str] = None
    deadline: Optional[str] = None

class MucTieuUpdate(BaseModel):
    ten_muc_tieu: Optional[str] = None
    title: Optional[str] = None
    so_tien_muc_tieu: Optional[float] = None
    target_amount: Optional[float] = None
    so_tien_hien_tai: Optional[float] = None
    han_chot: Optional[str] = None
    deadline: Optional[str] = None
    trang_thai: Optional[str] = None

class MucTieuNopTien(BaseModel):
    amount: Optional[float] = None
    so_tien: Optional[float] = None

class MucTieuResponse(BaseModel):
    ma_mt: int
    ma_nd: int
    ten_muc_tieu: str
    so_tien_muc_tieu: float
    so_tien_hien_tai: float
    han_chot: Optional[str] = None
    trang_thai: str
    phan_tram_hoan_thanh: float = 0.0

    # Compatibility fields
    id: Optional[int] = None
    user_id: Optional[int] = None
    title: Optional[str] = None
    target_amount: Optional[float] = None
    current_amount: Optional[float] = None
    deadline: Optional[str] = None

    class Config:
        from_attributes = True
