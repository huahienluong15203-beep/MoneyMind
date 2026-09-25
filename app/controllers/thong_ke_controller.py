from datetime import datetime, timedelta
from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.nguoi_dung import NguoiDung
from app.models.giao_dich import GiaoDich
from app.models.danh_muc import DanhMuc
from app.models.muc_tieu_tiet_kiem import MucTieuTietKiem
from app.schemas.thong_ke import TongQuanResponse, ChiTietDanhMuc, XuHuongThang

router = APIRouter(prefix="/api/thong-ke", tags=["Thống kê và báo cáo (UC009)"])

@router.get("/tong-quan", response_model=TongQuanResponse, summary="Xem số liệu tổng quan Dashboard & Biểu đồ (UC009)")
def lay_thong_ke_tong_quan(
    db: Session = Depends(get_db),
    current_user: NguoiDung = Depends(get_current_user)
):
    """
    UC009:
    - 3 thẻ số liệu tổng quan (số dư, thu, chi trong tháng)
    - Dữ liệu Pie chart phân bổ chi tiêu theo danh mục
    - Dữ liệu Bar chart so sánh thu/chi 6 tháng gần nhất
    - Danh sách giao dịch gần đây nhất
    """
    now = datetime.now()
    start_of_month = datetime(now.year, now.month, 1)

    # Giao dịch toàn bộ và tháng này
    all_txs = db.query(GiaoDich).filter(GiaoDich.ma_nd == current_user.ma_nd).all()
    month_txs = [t for t in all_txs if t.ngay_gd and t.ngay_gd >= start_of_month]

    def _is_refund_excluded(t):
        if not t.ghi_chu:
            return False
        gc = t.ghi_chu.lower()
        return "(đã xoá)" in gc or "(đã xóa)" in gc or "hoàn trả" in gc or "hoàn tiền" in gc

    tong_thu = sum(t.so_tien for t in month_txs if t.loai_gd == "thu" and not (t.ghi_chu and "hoàn tiền từ hũ tiết kiệm" in t.ghi_chu.lower()))
    tong_chi = sum(t.so_tien for t in month_txs if t.loai_gd == "chi" and not _is_refund_excluded(t))
    so_du = tong_thu - tong_chi

    # Chi theo danh mục (Pie chart)
    danh_mucs = {dm.ma_dm: dm for dm in db.query(DanhMuc).filter(DanhMuc.ma_nd == current_user.ma_nd).all()}
    cat_spent: Dict[int, float] = {}
    for t in month_txs:
        if t.loai_gd == "chi" and not _is_refund_excluded(t):
            cat_spent[t.ma_dm] = cat_spent.get(t.ma_dm, 0.0) + t.so_tien

    chi_theo_danh_muc: List[ChiTietDanhMuc] = []
    palette = ["#0ea5e9", "#f43f5e", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899", "#14b8a6", "#64748b"]
    idx = 0
    for ma_dm, amount in cat_spent.items():
        dm = danh_mucs.get(ma_dm)
        name = dm.ten_dm if dm else "Khác"
        color = dm.mau_sac if (dm and dm.mau_sac) else palette[idx % len(palette)]
        icon = dm.icon if (dm and dm.icon) else "tag"
        ty_le = round((amount / tong_chi) * 100, 1) if tong_chi > 0 else 0.0

        chi_theo_danh_muc.append(ChiTietDanhMuc(
            ma_dm=ma_dm,
            ten_dm=name,
            so_tien=amount,
            ty_le=ty_le,
            mau_sac=color,
            icon=icon
        ))
        idx += 1

    # Xu hướng 6 tháng gần nhất (Bar chart)
    xu_huong_6_thang: List[XuHuongThang] = []
    for i in range(5, -1, -1):
        m = now.month - i
        y = now.year
        while m <= 0:
            m += 12
            y -= 1
        m_start = datetime(y, m, 1)
        if m == 12:
            m_end = datetime(y + 1, 1, 1)
        else:
            m_end = datetime(y, m + 1, 1)

        m_txs = [t for t in all_txs if t.ngay_gd and m_start <= t.ngay_gd < m_end]
        m_thu = sum(t.so_tien for t in m_txs if t.loai_gd == "thu" and not (t.ghi_chu and "hoàn tiền từ hũ tiết kiệm" in t.ghi_chu.lower()))
        m_chi = sum(t.so_tien for t in m_txs if t.loai_gd == "chi" and not _is_refund_excluded(t))
        xu_huong_6_thang.append(XuHuongThang(
            thang=f"{m:02d}/{y}",
            tong_thu=m_thu,
            tong_chi=m_chi
        ))

    # 5 giao dịch gần đây nhất
    recent_txs = db.query(GiaoDich).filter(
        GiaoDich.ma_nd == current_user.ma_nd
    ).order_by(desc(GiaoDich.ngay_gd)).limit(5).all()

    giao_dich_gan_day = []
    for t in recent_txs:
        dm = danh_mucs.get(t.ma_dm)
        giao_dich_gan_day.append({
            "ma_gd": t.ma_gd,
            "id": t.ma_gd,
            "so_tien": t.so_tien,
            "amount": t.so_tien,
            "loai_gd": t.loai_gd,
            "type": t.loai_gd,
            "ten_dm": dm.ten_dm if dm else "Khác",
            "icon": dm.icon if dm else "tag",
            "mau_sac": dm.mau_sac if dm else "#0ea5e9",
            "ghi_chu": t.ghi_chu or "",
            "ngay_gd": t.ngay_gd.strftime("%d/%m/%Y") if t.ngay_gd else ""
        })

    return TongQuanResponse(
        tong_thu=tong_thu,
        tong_chi=tong_chi,
        so_du=so_du,
        chi_theo_danh_muc=chi_theo_danh_muc,
        xu_huong_6_thang=xu_huong_6_thang,
        giao_dich_gan_day=giao_dich_gan_day
    )
