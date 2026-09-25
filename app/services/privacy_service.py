from typing import Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.giao_dich import GiaoDich
from app.models.danh_muc import DanhMuc
from app.models.muc_tieu_tiet_kiem import MucTieuTietKiem

class PrivacyService:
    """
    NFR-04 & BR-03:
    Dịch vụ ẩn danh hóa dữ liệu trước khi gửi cho AI Engine.
    Loại bỏ hoàn toàn họ tên, email, id cá nhân, và các nội dung ghi chú tự do.
    Chỉ giữ lại số liệu thống kê tổng hợp và tên danh mục chi tiêu chung.
    """

    @staticmethod
    def _is_excluded_chi(t) -> bool:
        if not t.ghi_chu:
            return False
        gc = t.ghi_chu.lower()
        return "(đã xoá)" in gc or "(đã xóa)" in gc or "hoàn trả" in gc or "hoàn tiền" in gc

    @staticmethod
    def _is_excluded_thu(t) -> bool:
        if not t.ghi_chu:
            return False
        gc = t.ghi_chu.lower()
        return "hoàn tiền từ hũ tiết kiệm" in gc or "hoàn trả hạn mức" in gc

    @staticmethod
    def tong_hop_va_an_danh_thang(
        db: Session,
        ma_nd: int,
        thang: int,
        nam: int
    ) -> Dict[str, Any]:
        start_date = datetime(nam, thang, 1)
        if thang == 12:
            end_date = datetime(nam + 1, 1, 1)
            prev_start = datetime(nam, 11, 1)
            prev_end = start_date
        elif thang == 1:
            end_date = datetime(nam, 2, 1)
            prev_start = datetime(nam - 1, 12, 1)
            prev_end = start_date
        else:
            end_date = datetime(nam, thang + 1, 1)
            prev_start = datetime(nam, thang - 1, 1)
            prev_end = start_date

        # Giao dịch tháng hiện tại
        txs = db.query(GiaoDich).filter(
            GiaoDich.ma_nd == ma_nd,
            GiaoDich.ngay_gd >= start_date,
            GiaoDich.ngay_gd < end_date
        ).all()

        # Giao dịch tháng trước để so sánh xu hướng
        txs_prev = db.query(GiaoDich).filter(
            GiaoDich.ma_nd == ma_nd,
            GiaoDich.ngay_gd >= prev_start,
            GiaoDich.ngay_gd < prev_end
        ).all()

        danh_mucs = {dm.ma_dm: dm.ten_dm for dm in db.query(DanhMuc).filter(DanhMuc.ma_nd == ma_nd).all()}

        tong_thu = sum(t.so_tien for t in txs if t.loai_gd == "thu" and not PrivacyService._is_excluded_thu(t))
        tong_chi = sum(t.so_tien for t in txs if t.loai_gd == "chi" and not PrivacyService._is_excluded_chi(t))

        # Chi tiêu theo danh mục tháng trước
        prev_spent_by_cat: Dict[str, float] = {}
        for t in txs_prev:
            if t.loai_gd == "chi" and not PrivacyService._is_excluded_chi(t):
                cname = danh_mucs.get(t.ma_dm, "Khác")
                gc = (t.ghi_chu or "").lower()
                if "tiết kiệm" in gc or "mục tiêu" in gc or cname.lower() == "tiết kiệm":
                    cname = "Tiết kiệm"
                prev_spent_by_cat[cname] = prev_spent_by_cat.get(cname, 0.0) + t.so_tien

        # Chi tiêu theo danh mục tháng này
        spent_by_cat: Dict[str, float] = {}
        for t in txs:
            if t.loai_gd == "chi" and not PrivacyService._is_excluded_chi(t):
                cname = danh_mucs.get(t.ma_dm, "Khác")
                gc = (t.ghi_chu or "").lower()
                if "tiết kiệm" in gc or "mục tiêu" in gc or cname.lower() == "tiết kiệm":
                    cname = "Tiết kiệm"
                spent_by_cat[cname] = spent_by_cat.get(cname, 0.0) + t.so_tien

        chi_theo_danh_muc = []
        for cname, amount in sorted(spent_by_cat.items(), key=lambda x: x[1], reverse=True):
            ty_le = round(amount / tong_chi, 3) if tong_chi > 0 else 0.0
            prev_amount = prev_spent_by_cat.get(cname, 0.0)
            if prev_amount > 0:
                diff_pct = round(((amount - prev_amount) / prev_amount) * 100)
                so_sanh = f"+{diff_pct}%" if diff_pct > 0 else f"{diff_pct}%"
            else:
                so_sanh = "Mới"

            chi_theo_danh_muc.append({
                "danh_muc": cname,
                "so_tien": amount,
                "ty_le": ty_le,
                "so_sanh_thang_truoc": so_sanh
            })

        # Mục tiêu tiết kiệm (chỉ lấy tên danh mục và tiến độ, không lấy thông tin cá nhân)
        muc_tieus = db.query(MucTieuTietKiem).filter(
            MucTieuTietKiem.ma_nd == ma_nd,
            MucTieuTietKiem.trang_thai == "dang_thuc_hien"
        ).all()
        muc_tieu_data = []
        for mt in muc_tieus:
            pct = round((mt.so_tien_hien_tai / mt.so_tien_muc_tieu), 2) if mt.so_tien_muc_tieu > 0 else 0.0
            muc_tieu_data.append({
                "ten": mt.ten_muc_tieu,
                "tien_do": pct
            })

        # Dữ liệu hoàn toàn ẩn danh, không có họ tên, email, hay ghi chú tự do
        an_danh_payload = {
            "thang": thang,
            "nam": nam,
            "tong_thu": tong_thu,
            "tong_chi": tong_chi,
            "chi_theo_danh_muc": chi_theo_danh_muc,
            "muc_tieu_tiet_kiem": muc_tieu_data[0] if muc_tieu_data else None
        }

        return an_danh_payload

    @staticmethod
    def an_danh_hoi_dap(
        db: Session,
        ma_nd: int
    ) -> Dict[str, Any]:
        """Tạo ngữ cảnh ẩn danh cho hỏi đáp tài chính cá nhân UC012"""
        now = datetime.now()
        start_date = datetime(now.year, now.month, 1)

        txs = db.query(GiaoDich).filter(
            GiaoDich.ma_nd == ma_nd,
            GiaoDich.ngay_gd >= start_date
        ).all()

        danh_mucs = {dm.ma_dm: dm.ten_dm for dm in db.query(DanhMuc).filter(DanhMuc.ma_nd == ma_nd).all()}

        tong_thu = sum(t.so_tien for t in txs if t.loai_gd == "thu" and not PrivacyService._is_excluded_thu(t))
        tong_chi = sum(t.so_tien for t in txs if t.loai_gd == "chi" and not PrivacyService._is_excluded_chi(t))

        chi_tiet_chi = {}
        for t in txs:
            if t.loai_gd == "chi" and not PrivacyService._is_excluded_chi(t):
                cname = danh_mucs.get(t.ma_dm, "Khác")
                gc = (t.ghi_chu or "").lower()
                if "tiết kiệm" in gc or "mục tiêu" in gc or cname.lower() == "tiết kiệm":
                    cname = "Tiết kiệm"
                chi_tiet_chi[cname] = chi_tiet_chi.get(cname, 0.0) + t.so_tien

        muc_tieus = db.query(MucTieuTietKiem).filter(
            MucTieuTietKiem.ma_nd == ma_nd
        ).all()

        return {
            "thang_hien_tai": f"{now.month}/{now.year}",
            "tong_thu": tong_thu,
            "tong_chi": tong_chi,
            "so_du": tong_thu - tong_chi,
            "chi_tiet_danh_muc": chi_tiet_chi,
            "so_luong_muc_tieu": len(muc_tieus)
        }
