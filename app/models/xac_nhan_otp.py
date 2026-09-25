from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from app.core.database import Base

class XacNhanOTP(Base):
    __tablename__ = "xac_nhan_otp"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), index=True)
    otp_code = Column(String(10))
    het_han = Column(DateTime)
    da_dung = Column(Boolean, default=False)
    ngay_tao = Column(DateTime, default=datetime.utcnow)
