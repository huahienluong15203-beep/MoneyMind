from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base

class NganSach(Base):
    __tablename__ = "ngan_sach"

    ma_ns = Column(Integer, primary_key=True, index=True)
    ma_nd = Column(Integer, ForeignKey("nguoi_dung.ma_nd"))
    ma_dm = Column(Integer, ForeignKey("danh_muc.ma_dm"))
    thang_nam = Column(String(20))  # định dạng YYYY-MM, ví dụ: "2026-09"
    han_muc = Column(Float)
    so_tien_da_chi = Column(Float, default=0.0)
    canh_bao_da_gui = Column(Boolean, default=False)
    so_du_chuyen_sang = Column(Float, default=0.0)  # Số dư hạn mức chuyển từ tháng trước sang
    han_muc_cap_moi = Column(Float, default=0.0)    # Hạn mức cấp mới trong tháng này

    nguoi_dung = relationship("NguoiDung", back_populates="ngan_sachs")
    danh_muc = relationship("DanhMuc", back_populates="ngan_sachs")
