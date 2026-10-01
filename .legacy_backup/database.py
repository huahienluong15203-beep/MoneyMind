"""
database.py - Kết nối CSDL và migration
Chuyển tiếp và tương thích ngược từ app.core.database
"""
from app.core.database import (
    engine,
    SessionLocal,
    Base,
    get_db,
    migrate_legacy_data
)

__all__ = [
    "engine",
    "SessionLocal",
    "Base",
    "get_db",
    "migrate_legacy_data"
]