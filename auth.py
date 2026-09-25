"""
auth.py - Xác thực, mã hóa và bảo mật JWT
Chuyển tiếp và tương thích ngược từ app.core.security
"""
from app.core.security import (
    SECRET_KEY,
    REFRESH_SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
    pwd_context,
    security,
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
    get_current_user
)

__all__ = [
    "SECRET_KEY",
    "REFRESH_SECRET_KEY",
    "ALGORITHM",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "REFRESH_TOKEN_EXPIRE_DAYS",
    "pwd_context",
    "security",
    "get_password_hash",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "verify_refresh_token",
    "get_current_user"
]