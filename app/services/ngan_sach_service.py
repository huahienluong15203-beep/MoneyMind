from datetime import datetime
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.ngan_sach import NganSach
from app.models.giao_dich import GiaoDich
from app.models.danh_muc import DanhMuc
from app.models.thong_bao import ThongBao
from app.schemas.giao_dich import CanhBaoNganSachInfo
from app.schemas.ngan_sach import CanhBaoNgayResponse

class NganSachService:
    @staticmethod
    def kiem_tra_ngan_sach(
        db: Session,
        ma_nd: int,
        ma_dm: int,
        ngay_gd: Optional[datetime] = None
    ) -> CanhBaoNganSachInfo:
        """
        NFR-02 & UC007: Kiểm tra tức thời hạn mức ngân sách khi lưu giao dịch.
        BR-05: Chỉ phát sinh cảnh báo nếu danh mục liên quan đã được thiết lập ngân sách.
        """
        if not ngay_gd:
            ngay_gd = datetime.now()
        elif ngay_gd.tzinfo is not None:
            ngay_gd = ngay_gd.replace(tzinfo=None)

        thang_nam = ngay_gd.strftime("%Y-%m")

        # Tìm ngân sách đã thiết lập cho danh mục và tháng này
        ngan_sach = db.query(NganSach).filter(
            NganSach.ma_nd == ma_nd,
            NganSach.ma_dm == ma_dm,
            NganSach.thang_nam == thang_nam
        ).first()

        danh_muc = db.query(DanhMuc).filter(DanhMuc.ma_dm == ma_dm).first()
        ten_dm = danh_muc.ten_dm if danh_muc else "Danh mục"

        han_muc = 0.0
        if ngan_sach and ngan_sach.han_muc and ngan_sach.han_muc > 0:
            han_muc = float(ngan_sach.han_muc)
        elif danh_muc and danh_muc.han_muc and danh_muc.han_muc > 0:
            han_muc = float(danh_muc.han_muc)

        if han_muc <= 0:
            return CanhBaoNganSachInfo(
                co_canh_bao=False,
                vuot_ngan_sach=False,
                ty_le=0.0,
                han_muc=0.0,
                so_tien_da_chi=0.0,
                thong_bao=None
            )

        # Tính tổng chi tiêu của danh mục trong tháng
        # Các giao dịch chi trong tháng tương ứng
        start_date = datetime.strptime(f"{thang_nam}-01", "%Y-%m-%d")
        if start_date.month == 12:
            end_date = datetime(start_date.year + 1, 1, 1)
        else:
            end_date = datetime(start_date.year, start_date.month + 1, 1)

        tong_chi = db.query(func.coalesce(func.sum(GiaoDich.so_tien), 0.0)).filter(
            GiaoDich.ma_nd == ma_nd,
            GiaoDich.ma_dm == ma_dm,
            GiaoDich.loai_gd == "chi",
            GiaoDich.ngay_gd >= start_date,
            GiaoDich.ngay_gd < end_date
        ).scalar() or 0.0

        # Cập nhật số tiền đã chi vào bản ghi ngân sách nếu có
        if ngan_sach:
            ngan_sach.so_tien_da_chi = tong_chi
        ty_le = (tong_chi / han_muc) if han_muc > 0 else 0.0
        vuot_ngan_sach = (tong_chi > han_muc)
        co_canh_bao = (ty_le >= 0.9)

        thong_bao_text = None
        if vuot_ngan_sach:
            if ngan_sach:
                ngan_sach.canh_bao_da_gui = True
            phan_tram = round(ty_le * 100)
            thong_bao_text = (
                f"🚨 CẢNH BÁO VƯỢT NGÂN SÁCH: Danh mục '{ten_dm}' trong tháng {thang_nam} "
                f"đã chi tiêu {tong_chi:,.0f} đ / {han_muc:,.0f} đ ({phan_tram}% hạn mức)!"
            )
            title = f"🚨 CẢNH BÁO: HŨ \"{ten_dm}\" VƯỢT HẠN MỨC ({phan_tram}%)!"
            existing_tb = db.query(ThongBao).filter(
                ThongBao.ma_nd == ma_nd,
                ThongBao.da_xem == False,
                ThongBao.noi_dung.like(f"%'{ten_dm}'%")
            ).first()
            if existing_tb:
                existing_tb.tieu_de = title
                existing_tb.noi_dung = thong_bao_text
                existing_tb.ngay_tao = datetime.now()
            else:
                tb = ThongBao(
                    ma_nd=ma_nd,
                    tieu_de=title,
                    noi_dung=thong_bao_text,
                    da_xem=False,
                    ngay_tao=datetime.now()
                )
                db.add(tb)
        elif ty_le >= 0.9:
            phan_tram = round(ty_le * 100)
            thong_bao_text = (
                f"⚠️ CẢNH BÁO SẮP HẾT NGÂN SÁCH: Danh mục '{ten_dm}' trong tháng {thang_nam} "
                f"đã đạt {phan_tram}% hạn mức ({tong_chi:,.0f} đ / {han_muc:,.0f} đ)."
            )
            title = f"⚠️ CẢNH BÁO: HŨ \"{ten_dm}\" ĐÃ CHI TIÊU ĐẠT {phan_tram}% HẠN MỨC!"
            existing_tb = db.query(ThongBao).filter(
                ThongBao.ma_nd == ma_nd,
                ThongBao.da_xem == False,
                ThongBao.noi_dung.like(f"%'{ten_dm}'%")
            ).first()
            if existing_tb:
                existing_tb.tieu_de = title
                existing_tb.noi_dung = thong_bao_text
                existing_tb.ngay_tao = datetime.now()
            else:
                tb = ThongBao(
                    ma_nd=ma_nd,
                    tieu_de=title,
                    noi_dung=thong_bao_text,
                    da_xem=False,
                    ngay_tao=datetime.now()
                )
                db.add(tb)

        db.commit()

        return CanhBaoNganSachInfo(
            co_canh_bao=co_canh_bao,
            vuot_ngan_sach=vuot_ngan_sach,
            ty_le=round(ty_le, 2),
            han_muc=han_muc,
            so_tien_da_chi=tong_chi,
            thong_bao=thong_bao_text
        )

    @staticmethod
    def check_and_generate_login_budget_notifications(db: Session, user) -> None:
        """
        Khi người dùng đăng nhập vào:
        Kiểm tra xem tài khoản có hũ chi tiêu nào chạm hoặc vượt hạn mức (>=90%) không.
        Nếu có, đảm bảo có đúng 1 thông báo cảnh báo trong phần thông báo (tránh tạo trùng lặp nếu đã có thông báo trong ngày).
        """
        now = datetime.now()
        today_start = datetime(now.year, now.month, now.day, 0, 0, 0)

        user_id = getattr(user, 'ma_nd', None) or getattr(user, 'id', None)
        if not user_id:
            return

        chi_categories = db.query(DanhMuc).filter(
            DanhMuc.ma_nd == user_id,
            DanhMuc.loai_dm == "chi",
            DanhMuc.han_muc > 0
        ).all()

        over_jars = []
        approaching_jars = []
        for c in chi_categories:
            txs = db.query(GiaoDich).filter(
                GiaoDich.ma_nd == user_id,
                GiaoDich.ma_dm == c.ma_dm,
                GiaoDich.loai_gd == "chi"
            ).all()
            spent = sum(t.so_tien for t in txs if t.so_tien)
            if spent > c.han_muc:
                pct = round((spent / c.han_muc) * 100)
                over_jars.append({"name": c.ten_dm, "spent": spent, "limit": c.han_muc, "pct": pct})
            elif spent >= c.han_muc * 0.9:
                pct = round((spent / c.han_muc) * 100)
                approaching_jars.append({"name": c.ten_dm, "spent": spent, "limit": c.han_muc, "pct": pct})

        today_notifs = db.query(ThongBao).filter(
            ThongBao.ma_nd == user_id,
            ThongBao.ngay_tao >= today_start
        ).all()
        today_titles_lower = [(n.tieu_de or "").lower() for n in today_notifs]
        today_contents_lower = [(n.noi_dung or "").lower() for n in today_notifs]

        if over_jars:
            has_over_alert = any("vượt" in t for t in today_titles_lower)
            if not has_over_alert:
                max_pct = max(j["pct"] for j in over_jars)
                first_name = over_jars[0]["name"]
                title = f"🚨 CẢNH BÁO: HŨ \"{first_name}\" VƯỢT HẠN MỨC ({max_pct}%)!" if len(over_jars) == 1 else f"🚨 CẢNH BÁO: CHI TIÊU VƯỢT HẠN MỨC ({max_pct}%)!"
                jar_details = "\n".join([f"• Hũ \"{j['name']}\": đã chi {j['spent']:,.0f} đ / {j['limit']:,.0f} đ ({j['pct']}%)" for j in over_jars])
                msg = f"Hệ thống ghi nhận tài khoản của bạn đang có hũ chi tiêu vượt quá hạn mức cho phép:\n\n{jar_details}\n\n🚨 Vui lòng chi tiêu tiết kiệm lại và kiểm soát các khoản chi hôm nay!"
                db.add(ThongBao(ma_nd=user_id, tieu_de=title, noi_dung=msg, da_xem=False, ngay_tao=now))
                db.commit()

        elif approaching_jars:
            has_near_alert = any(("sắp chạm" in t or "sắp hết" in t or "đạt" in t) and any(j["name"].lower() in (t + " " + c) for j in approaching_jars for c in today_contents_lower) for t in today_titles_lower)
            if not has_near_alert:
                max_pct = max(j["pct"] for j in approaching_jars)
                first_name = approaching_jars[0]["name"]
                title = f"⚠️ CẢNH BÁO: HŨ \"{first_name}\" ĐÃ CHI TIÊU ĐẠT {max_pct}% HẠN MỨC!" if len(approaching_jars) == 1 else f"⚠️ CẢNH BÁO: CHI TIÊU SẮP CHẠM HẠN MỨC ({max_pct}%)!"
                jar_details = "\n".join([f"• Hũ \"{j['name']}\": đã chi {j['spent']:,.0f} đ / {j['limit']:,.0f} đ ({j['pct']}%)" for j in approaching_jars])
                msg = f"Hệ thống ghi nhận tài khoản của bạn có hũ chi tiêu sắp chạm trần hạn mức:\n\n{jar_details}\n\n⚠️ Vui lòng cân nhắc chi tiêu tiết kiệm để không bị vượt quá ngân sách!"
                db.add(ThongBao(ma_nd=user_id, tieu_de=title, noi_dung=msg, da_xem=False, ngay_tao=now))
                db.commit()

    @staticmethod
    def lay_danh_sach_canh_bao(db: Session, ma_nd: int, thang_nam: Optional[str] = None) -> List[CanhBaoNgayResponse]:
        """UC007: Trạng thái cảnh báo vượt ngân sách hiện tại"""
        if not thang_nam:
            thang_nam = datetime.now().strftime("%Y-%m")

        ngan_sachs = db.query(NganSach).filter(
            NganSach.ma_nd == ma_nd,
            NganSach.thang_nam == thang_nam
        ).all()

        results = []
        for ns in ngan_sachs:
            dm = db.query(DanhMuc).filter(DanhMuc.ma_dm == ns.ma_dm).first()
            ten_dm = dm.ten_dm if dm else "Không rõ"
            ty_le = (ns.so_tien_da_chi / ns.han_muc) if ns.han_muc > 0 else 0.0

            if ty_le >= 0.9:
                muc_do = "vuot" if ty_le > 1.0 else "nguy_co"
                pct = round(ty_le * 100)
                noi_dung = (
                    f"Đã chi tiêu {ns.so_tien_da_chi:,.0f} đ / {ns.han_muc:,.0f} đ ({pct}%)"
                )
                results.append(CanhBaoNgayResponse(
                    ma_ns=ns.ma_ns,
                    ten_dm=ten_dm,
                    thang_nam=ns.thang_nam,
                    han_muc=ns.han_muc,
                    so_tien_da_chi=ns.so_tien_da_chi,
                    ty_le=round(ty_le, 2),
                    muc_do=muc_do,
                    noi_dung=noi_dung
                ))
        return results

    @staticmethod
    def tinh_so_du_vi_chinh(db: Session, ma_nd: int) -> float:
        """Tính số dư khả dụng ví chính = Tổng thu - Tổng hạn mức cấp các hũ chi tiêu - Tổng tiền vào tiết kiệm"""
        from app.models.muc_tieu_tiet_kiem import MucTieuTietKiem
        txs = db.query(GiaoDich).filter(GiaoDich.ma_nd == ma_nd).all()
        categories = db.query(DanhMuc).filter(DanhMuc.ma_nd == ma_nd).all()
        savings_goals = db.query(MucTieuTietKiem).filter(MucTieuTietKiem.ma_nd == ma_nd).all()

        # Không tính đúp giao dịch hoàn tiền từ hũ tiết kiệm vào t_thu vì khi xóa hũ, total_savings đã giảm tương ứng
        t_thu = sum(t.so_tien for t in txs if t.loai_gd == "thu" and not (t.ghi_chu and "Hoàn tiền từ hũ tiết kiệm" in t.ghi_chu))
        total_savings = sum(g.so_tien_hien_tai for g in savings_goals)

        spent_by_cat = {}
        for t in txs:
            is_savings_tx = t.ghi_chu and ("tiết kiệm" in t.ghi_chu.lower() or "trích quỹ" in t.ghi_chu.lower())
            if t.loai_gd == "chi" and not is_savings_tx:
                spent_by_cat[t.ma_dm] = spent_by_cat.get(t.ma_dm, 0.0) + t.so_tien

        total_allocated_chi = 0.0
        for c in categories:
            if c.loai_dm == "chi" and c.ten_dm != "Tiết kiệm":
                c_spent = spent_by_cat.get(c.ma_dm, 0.0)
                if c.han_muc and c.han_muc > 0:
                    total_allocated_chi += max(float(c.han_muc), c_spent)
                else:
                    total_allocated_chi += c_spent

        return t_thu - total_allocated_chi - total_savings

