from app.models.nguoi_dung import NguoiDung
from app.models.danh_muc import DanhMuc
from app.models.giao_dich import GiaoDich
from app.models.ngan_sach import NganSach
from app.models.muc_tieu_tiet_kiem import MucTieuTietKiem
from app.models.bao_cao_ai import BaoCaoAI
from app.models.dat_lai_mat_khau import DatLaiMatKhau
from app.models.thong_bao import ThongBao
from app.models.xac_nhan_otp import XacNhanOTP

# Compatibility aliases
User = NguoiDung
Category = DanhMuc
Transaction = GiaoDich
SavingsGoal = MucTieuTietKiem
Notification = ThongBao

__all__ = [
    "NguoiDung",
    "DanhMuc",
    "GiaoDich",
    "NganSach",
    "MucTieuTietKiem",
    "BaoCaoAI",
    "DatLaiMatKhau",
    "ThongBao",
    "XacNhanOTP",
    "User",
    "Category",
    "Transaction",
    "SavingsGoal",
    "Notification"
]
