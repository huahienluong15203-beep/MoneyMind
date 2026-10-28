from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class NguoiDungUpdate(BaseModel):
    ho_ten: Optional[str] = None
    dob: Optional[str] = None
    occupation: Optional[str] = None
    goals: Optional[str] = None
    mat_khau_cu: Optional[str] = None
    mat_khau_moi: Optional[str] = None

class NguoiDungResponse(BaseModel):
    ma_nd: int
    email: str
    ho_ten: Optional[str] = None
    dob: Optional[str] = None
    occupation: Optional[str] = None
    goals: Optional[str] = None
    ngay_tao: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

