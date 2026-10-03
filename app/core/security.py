from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)

# Quản lý phiên đăng nhập đơn thiết bị (Single Active Session)
ACTIVE_USER_SESSIONS: dict = {}

def set_active_session(user_id: int, session_id: str, email: Optional[str] = None):
    ACTIVE_USER_SESSIONS[user_id] = session_id
    if email:
        ACTIVE_USER_SESSIONS[email] = session_id

def get_active_session(user_id: int, email: Optional[str] = None) -> Optional[str]:
    return ACTIVE_USER_SESSIONS.get(user_id) or (ACTIVE_USER_SESSIONS.get(email) if email else None)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password[:72])

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password[:72], hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None, session_id: Optional[str] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    if session_id:
        to_encode["session_id"] = session_id
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token(data: dict, session_id: Optional[str] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    if session_id:
        to_encode["session_id"] = session_id
    return jwt.encode(to_encode, settings.REFRESH_SECRET_KEY, algorithm=settings.ALGORITHM)

def verify_refresh_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, settings.REFRESH_SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "refresh":
            return None
        return payload.get("sub")
    except JWTError:
        return None

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Không thể xác thực thông tin đăng nhập",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not credentials:
        raise credentials_exception

    try:
        token = credentials.credentials
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email_or_user: str = payload.get("sub")
        if email_or_user is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Tránh circular import bằng cách import models trong hàm hoặc từ app.models
    from app.models.nguoi_dung import NguoiDung
    user = db.query(NguoiDung).filter(NguoiDung.email == email_or_user).first()
    if user is None:
        raise credentials_exception

    # Kiểm tra tính hợp lệ của phiên đăng nhập (Đơn thiết bị - Kicked out nếu đăng nhập thiết bị khác)
    token_session_id = payload.get("session_id")
    active_sid = ACTIVE_USER_SESSIONS.get(user.ma_nd) or getattr(user, "session_id", None)
    if active_sid and user.ma_nd not in ACTIVE_USER_SESSIONS:
        ACTIVE_USER_SESSIONS[user.ma_nd] = active_sid
        if user.email:
            ACTIVE_USER_SESSIONS[user.email] = active_sid

    if token_session_id and active_sid and token_session_id != active_sid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tài khoản của bạn đã được đăng nhập trên một thiết bị khác.",
            headers={"WWW-Authenticate": "Bearer", "X-Logout-Reason": "concurrent_login"}
        )

    # Ràng buộc bảo mật: kiểm tra trạng thái khóa tài khoản (TC-02)
    if user.trang_thai == "khoa":
        if user.khoa_den and datetime.utcnow() < user.khoa_den:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Tài khoản đang bị tạm khóa do nhập sai mật khẩu nhiều lần. Vui lòng thử lại sau {settings.LOCKOUT_MINUTES} phút."
            )
        else:
            # Tự động mở khóa sau khi hết hạn
            user.trang_thai = "hoat_dong"
            user.so_lan_sai = 0
            user.khoa_den = None
            db.commit()

    return user
