from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

class GiaoDich(Base):
    __tablename__ = "giao_dich"

    ma_gd = Column(Integer, primary_key=True, index=True)
    ma_nd = Column(Integer, ForeignKey("nguoi_dung.ma_nd"))
    ma_dm = Column(Integer, ForeignKey("danh_muc.ma_dm"))
    so_tien = Column(Float)
    loai_gd = Column(String(10))  # "thu" hoặc "chi"
    ngay_gd = Column(DateTime, default=datetime.now)
    ghi_chu = Column(Text, nullable=True)
    ngay_tao = Column(DateTime, default=datetime.utcnow)

    nguoi_dung = relationship("NguoiDung", back_populates="giao_dichs")
    danh_muc = relationship("DanhMuc", back_populates="giao_dichs")

    # Compatibility properties
    @property
    def id(self):
        return self.ma_gd

    @id.setter
    def id(self, val):
        self.ma_gd = val

    @property
    def user_id(self):
        return self.ma_nd

    @user_id.setter
    def user_id(self, val):
        self.ma_nd = val

    @property
    def category_id(self):
        return self.ma_dm

    @category_id.setter
    def category_id(self, val):
        self.ma_dm = val

    @property
    def amount(self):
        return self.so_tien

    @amount.setter
    def amount(self, val):
        self.so_tien = val

    @property
    def type(self):
        return self.loai_gd

    @type.setter
    def type(self, val):
        self.loai_gd = val

    @property
    def date(self):
        return self.ngay_gd

    @date.setter
    def date(self, val):
        self.ngay_gd = val

    @property
    def note(self):
        return self.ghi_chu

    @note.setter
    def note(self, val):
        self.ghi_chu = val
