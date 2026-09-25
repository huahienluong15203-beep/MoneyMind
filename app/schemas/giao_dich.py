from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field

class GiaoDichCreate(BaseModel):
    amount: Optional[float] = None
    so_tien: Optional[float] = None
    type: Optional[str] = None
    loai_gd: Optional[str] = None
    category_id: Optional[int] = None
    ma_dm: Optional[int] = None
    note: Optional[str] = None
    ghi_chu: Optional[str] = None
    date: Optional[datetime] = None
    ngay_gd: Optional[datetime] = None

class GiaoDichUpdate(BaseModel):
    so_tien: Optional[float] = None
    amount: Optional[float] = None
    loai_gd: Optional[str] = None
    type: Optional[str] = None
    ma_dm: Optional[int] = None
    category_id: Optional[int] = None
    ghi_chu: Optional[str] = None
    note: Optional[str] = None
    ngay_gd: Optional[datetime] = None
    date: Optional[datetime] = None

class GiaoDichResponse(BaseModel):
    ma_gd: int
    ma_nd: int
    ma_dm: int
    so_tien: float
    loai_gd: str
    ngay_gd: datetime
    ghi_chu: Optional[str] = None
    ngay_tao: Optional[datetime] = None

    # Compatibility fields
    id: Optional[int] = None
    user_id: Optional[int] = None
    category_id: Optional[int] = None
    amount: Optional[float] = None
    type: Optional[str] = None
    date: Optional[datetime] = None
    note: Optional[str] = None

    class Config:
        from_attributes = True

class CanhBaoNganSachInfo(BaseModel):
    co_canh_bao: bool = False
    vuot_ngan_sach: bool = False
    ty_le: float = 0.0
    han_muc: float = 0.0
    so_tien_da_chi: float = 0.0
    thong_bao: Optional[str] = None

class GiaoDichCreateResponse(BaseModel):
    giao_dich: GiaoDichResponse
    canh_bao: CanhBaoNganSachInfo

# Legacy schemas
class TransactionCreate(BaseModel):
    amount: float
    type: str
    category_id: int
    note: Optional[str] = None

class TransactionResponse(TransactionCreate):
    id: int
    user_id: int
    date: datetime

    class Config:
        from_attributes = True
