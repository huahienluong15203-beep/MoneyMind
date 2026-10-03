from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class LichSuAI(Base):
    __tablename__ = "lich_su_ai"

    ma_log = Column(Integer, primary_key=True, index=True)
    ma_nd = Column(Integer, ForeignKey("nguoi_dung.ma_nd", ondelete="CASCADE"), index=True)
    ma_phien = Column(String(50), nullable=True, index=True)  # Định danh phiên trò chuyện
    cau_hoi = Column(Text, nullable=False)
    tra_loi = Column(Text, nullable=False)
    loai_hanh_dong = Column(String(50), nullable=True)  # them_giao_dich, sua_giao_dich, xoa_giao_dich, tra_cuu, tao_hu, nop_hu, rut_hu, doi_muc_tieu, xoa_hu, ngan_sach, suc_khoe, tu_van
    ngay_tao = Column(DateTime, default=datetime.utcnow, index=True)

    nguoi_dung = relationship("NguoiDung", back_populates="lich_su_ai")

    # Compatibility properties
    @property
    def id(self):
        return self.ma_log

    @id.setter
    def id(self, val):
        self.ma_log = val

    @property
    def user_id(self):
        return self.ma_nd

    @user_id.setter
    def user_id(self, val):
        self.ma_nd = val

    @property
    def question(self):
        return self.cau_hoi

    @property
    def answer(self):
        return self.tra_loi

    @property
    def action_type(self):
        return self.loai_hanh_dong

    @property
    def created_at(self):
        return self.ngay_tao
