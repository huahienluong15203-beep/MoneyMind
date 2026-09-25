from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base

class NguoiDung(Base):
    __tablename__ = "nguoi_dung"

    ma_nd = Column(Integer, primary_key=True, index=True)
    ho_ten = Column(String(100), nullable=True)
    email = Column(String(100), unique=True, index=True)
    mat_khau_hash = Column(String(255))
    trang_thai = Column(String(20), default="hoat_dong")  # "hoat_dong", "khoa"
    so_lan_sai = Column(Integer, default=0)
    khoa_den = Column(DateTime, nullable=True)
    dob = Column(String, nullable=True)
    occupation = Column(String, nullable=True)
    goals = Column(String, nullable=True)
    ngay_tao = Column(DateTime, default=datetime.utcnow)

    # Relationships
    danh_mucs = relationship("DanhMuc", back_populates="nguoi_dung", cascade="all, delete-orphan")
    giao_dichs = relationship("GiaoDich", back_populates="nguoi_dung", cascade="all, delete-orphan")
    ngan_sachs = relationship("NganSach", back_populates="nguoi_dung", cascade="all, delete-orphan")
    muc_tieus = relationship("MucTieuTietKiem", back_populates="nguoi_dung", cascade="all, delete-orphan")
    bao_caos = relationship("BaoCaoAI", back_populates="nguoi_dung", cascade="all, delete-orphan")

    # Compatibility properties for legacy code
    @property
    def id(self):
        return self.ma_nd

    @id.setter
    def id(self, val):
        self.ma_nd = val

    @property
    def username(self):
        return self.email

    @username.setter
    def username(self, val):
        self.email = val

    @property
    def hashed_password(self):
        return self.mat_khau_hash

    @hashed_password.setter
    def hashed_password(self, val):
        self.mat_khau_hash = val

    @property
    def full_name(self):
        return self.ho_ten

    @full_name.setter
    def full_name(self, val):
        self.ho_ten = val
