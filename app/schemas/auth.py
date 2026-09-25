from typing import Optional
from pydantic import BaseModel, Field, EmailStr

class DangKyRequest(BaseModel):
    email: str = Field(..., description="Email người dùng")
    password: str = Field(..., min_length=4, description="Mật khẩu đăng nhập")
    ho_ten: Optional[str] = Field(None, description="Họ và tên người dùng")

class DangNhapRequest(BaseModel):
    email: str = Field(..., description="Email hoặc tên đăng nhập")
    password: str = Field(..., description="Mật khẩu")

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str] = None

class RefreshTokenRequest(BaseModel):
    refresh_token: str

# Legacy compatibility schemas
class UserCreate(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
