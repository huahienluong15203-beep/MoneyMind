from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base

class KetChuyenNganSach(Base):
    __tablename__ = "ket_chuyen_ngan_sach"

    ma_kc = Column(Integer, primary_key=True, index=True)
    ma_nd = Column(Integer, ForeignKey("nguoi_dung.ma_nd"), index=True)
    ma_dm = Column(Integer, ForeignKey("danh_muc.ma_dm"), index=True)
    thang_nguon = Column(String(20), index=True)  # Định dạng YYYY-MM, ví dụ: "2026-09"
    thang_dich = Column(String(20), index=True)   # Định dạng YYYY-MM, ví dụ: "2026-10"
    han_muc_thang_truoc = Column(Float, default=0.0)
    da_chi_thang_truoc = Column(Float, default=0.0)
    so_tien_chuyen = Column(Float, default=0.0)    # Số dư còn lại chưa tiêu hết được chuyển sang
    ngay_tao = Column(DateTime, default=datetime.now)
    ghi_chu = Column(String(255), nullable=True)

    nguoi_dung = relationship("NguoiDung")
    danh_muc = relationship("DanhMuc")
