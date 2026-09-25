from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class DanhMuc(Base):
    __tablename__ = "danh_muc"

    ma_dm = Column(Integer, primary_key=True, index=True)
    ma_nd = Column(Integer, ForeignKey("nguoi_dung.ma_nd"))
    ten_dm = Column(String(50), index=True)
    loai_dm = Column(String(10))  # "thu" hoặc "chi"
    icon = Column(String(50), default="tag")
    mau_sac = Column(String(20), default="#0ea5e9")
    han_muc = Column(Float, default=0.0)

    nguoi_dung = relationship("NguoiDung", back_populates="danh_mucs")
    giao_dichs = relationship("GiaoDich", back_populates="danh_muc", cascade="all, delete-orphan")
    ngan_sachs = relationship("NganSach", back_populates="danh_muc", cascade="all, delete-orphan")

    # Compatibility properties
    @property
    def id(self):
        return self.ma_dm

    @id.setter
    def id(self, val):
        self.ma_dm = val

    @property
    def user_id(self):
        return self.ma_nd

    @user_id.setter
    def user_id(self, val):
        self.ma_nd = val

    @property
    def name(self):
        return self.ten_dm

    @name.setter
    def name(self, val):
        self.ten_dm = val

    @property
    def type(self):
        return self.loai_dm

    @type.setter
    def type(self, val):
        self.loai_dm = val

    @property
    def budget_limit(self):
        return self.han_muc

    @budget_limit.setter
    def budget_limit(self, val):
        self.han_muc = val
