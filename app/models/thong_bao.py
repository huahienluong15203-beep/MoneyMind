from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship, synonym
from app.core.database import Base

class ThongBao(Base):
    __tablename__ = "thong_bao"

    id = Column(Integer, primary_key=True, index=True)
    ma_nd = Column(Integer, ForeignKey("nguoi_dung.ma_nd"))
    tieu_de = Column(String(255))
    noi_dung = Column(Text)
    da_xem = Column(Boolean, default=False)
    ngay_tao = Column(DateTime, default=datetime.now)

    nguoi_dung = relationship("NguoiDung", backref="thong_baos")

    user_id = synonym("ma_nd")
    title = synonym("tieu_de")
    message = synonym("noi_dung")
    is_read = synonym("da_xem")
    created_at = synonym("ngay_tao")
