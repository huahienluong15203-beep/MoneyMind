from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class MucTieuTietKiem(Base):
    __tablename__ = "muc_tieu_tiet_kiem"

    ma_mt = Column(Integer, primary_key=True, index=True)
    ma_nd = Column(Integer, ForeignKey("nguoi_dung.ma_nd"))
    ten_muc_tieu = Column(String(100))
    so_tien_muc_tieu = Column(Float)
    so_tien_hien_tai = Column(Float, default=0.0)
    han_chot = Column(String(50), nullable=True)
    trang_thai = Column(String(20), default="dang_thuc_hien")  # "dang_thuc_hien", "hoan_thanh", "huy"

    nguoi_dung = relationship("NguoiDung", back_populates="muc_tieus")

    # Compatibility properties
    @property
    def id(self):
        return self.ma_mt

    @id.setter
    def id(self, val):
        self.ma_mt = val

    @property
    def user_id(self):
        return self.ma_nd

    @user_id.setter
    def user_id(self, val):
        self.ma_nd = val

    @property
    def title(self):
        return self.ten_muc_tieu

    @title.setter
    def title(self, val):
        self.ten_muc_tieu = val

    @property
    def target_amount(self):
        return self.so_tien_muc_tieu

    @target_amount.setter
    def target_amount(self, val):
        self.so_tien_muc_tieu = val

    @property
    def current_amount(self):
        return self.so_tien_hien_tai

    @current_amount.setter
    def current_amount(self, val):
        self.so_tien_hien_tai = val

    @property
    def deadline(self):
        return self.han_chot

    @deadline.setter
    def deadline(self, val):
        self.han_chot = val
