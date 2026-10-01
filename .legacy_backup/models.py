"""
models.py - Mô hình thực thể SQLAlchemy ORM
Chuyển tiếp và tương thích ngược từ gói kiến trúc app.models
"""
from app.models import (
    NguoiDung,
    DanhMuc,
    GiaoDich,
    NganSach,
    MucTieuTietKiem,
    BaoCaoAI,
    DatLaiMatKhau,
    ThongBao,
    XacNhanOTP,
    User,
    Category,
    Transaction,
    SavingsGoal,
    Notification
)
from app.core.database import Base

__all__ = [
    "Base",
    "NguoiDung",
    "DanhMuc",
    "GiaoDich",
    "NganSach",
    "MucTieuTietKiem",
    "BaoCaoAI",
    "DatLaiMatKhau",
    "ThongBao",
    "XacNhanOTP",
    "User",
    "Category",
    "Transaction",
    "SavingsGoal",
    "Notification"
]