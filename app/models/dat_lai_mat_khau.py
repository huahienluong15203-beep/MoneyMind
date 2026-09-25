from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from app.core.database import Base

class DatLaiMatKhau(Base):
    __tablename__ = "dat_lai_mat_khau"

    id = Column(Integer, primary_key=True, index=True)
    ma_nd = Column(Integer, ForeignKey("nguoi_dung.ma_nd"))
    token = Column(String(255), unique=True, index=True)
    het_han = Column(DateTime)
    da_dung = Column(Boolean, default=False)
