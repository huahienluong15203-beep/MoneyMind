from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base

class BaoCaoAI(Base):
    __tablename__ = "bao_cao_ai"

    ma_bc = Column(Integer, primary_key=True, index=True)
    ma_nd = Column(Integer, ForeignKey("nguoi_dung.ma_nd"))
    thang_nam = Column(String(20))  # định dạng YYYY-MM
    noi_dung_tom_tat = Column(Text)
    goi_y_dieu_chinh = Column(Text)
    goi_y_ngan_sach = Column(Text, nullable=True)
    ngay_tao = Column(DateTime, default=datetime.utcnow)

    nguoi_dung = relationship("NguoiDung", back_populates="bao_caos")
