from typing import Optional
from pydantic import BaseModel, Field

class DanhMucCreate(BaseModel):
    ten_dm: str = Field(..., min_length=1, max_length=50, description="Tên danh mục")
    loai_dm: str = Field(..., pattern="^(thu|chi)$", description="Loại danh mục: 'thu' hoặc 'chi'")
    icon: Optional[str] = Field("tag", description="Icon minh hoạ")
    mau_sac: Optional[str] = Field("#0ea5e9", description="Mã màu HEX")
    han_muc: Optional[float] = Field(0.0, ge=0, description="Hạn mức nếu là chi")

class DanhMucUpdate(BaseModel):
    ten_dm: Optional[str] = Field(None, min_length=1, max_length=50)
    loai_dm: Optional[str] = Field(None, pattern="^(thu|chi)$")
    icon: Optional[str] = None
    mau_sac: Optional[str] = None
    han_muc: Optional[float] = Field(None, ge=0)

class DanhMucResponse(BaseModel):
    ma_dm: int
    ma_nd: int
    ten_dm: str
    loai_dm: str
    icon: Optional[str] = "tag"
    mau_sac: Optional[str] = "#0ea5e9"
    han_muc: Optional[float] = 0.0

    # Frontend compatibility fields
    id: Optional[int] = None
    user_id: Optional[int] = None
    name: Optional[str] = None
    type: Optional[str] = None
    budget_limit: Optional[float] = 0.0

    class Config:
        from_attributes = True

# Legacy aliases
class CategoryCreate(BaseModel):
    name: str
    type: str
    icon: Optional[str] = "tag"
    color: Optional[str] = "#0ea5e9"
    budget_limit: Optional[float] = 0.0

class CategoryResponse(CategoryCreate):
    id: int
    user_id: int

    class Config:
        from_attributes = True
