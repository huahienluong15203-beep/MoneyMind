from datetime import datetime
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.ngan_sach import NganSach
from app.models.giao_dich import GiaoDich
from app.models.danh_muc import DanhMuc
from app.models.thong_bao import ThongBao
from app.models.ket_chuyen_ngan_sach import KetChuyenNganSach
from app.schemas.giao_dich import CanhBaoNganSachInfo
from app.schemas.ngan_sach import CanhBaoNgayResponse
from app.schemas.ket_chuyen_ngan_sach import KetChuyenNganSachResponse

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

        # Tính tổng chi tiêu của danh mục trong tháng
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

        if han_muc <= 0:
            if tong_chi > 0:
                vuot_ngan_sach = True
                co_canh_bao = True
                ty_le = 1.0
                thong_bao_text = (
                    f"🚨 CẢNH BÁO VƯỢT HẠN MỨC: Danh mục '{ten_dm}' trong tháng {thang_nam} "
                    f"chưa được cấp hạn mức nhưng đã chi tiêu {tong_chi:,.0f} đ (vượt hạn mức 0 đ)!"
                )
                title = f"🚨 CẢNH BÁO: HŨ \"{ten_dm}\" VƯỢT HẠN MỨC!"
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
                    co_canh_bao=True,
                    vuot_ngan_sach=True,
                    ty_le=1.0,
                    han_muc=0.0,
                    so_tien_da_chi=tong_chi,
                    thong_bao=thong_bao_text
                )
            else:
                return CanhBaoNganSachInfo(
                    co_canh_bao=False,
                    vuot_ngan_sach=False,
                    ty_le=0.0,
                    han_muc=0.0,
                    so_tien_da_chi=0.0,
                    thong_bao=None
                )
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
        Kiểm tra xem tài khoản có hũ chi tiêu nào chạm hoặc vượt hạn mức (>=90%) TRONG THÁNG HIỆN TẠI không.
        Nếu có, đảm bảo có đúng 1 thông báo cảnh báo trong phần thông báo (tránh tạo trùng lặp nếu đã có thông báo trong ngày).
        """
        now = datetime.now()
        today_start = datetime(now.year, now.month, now.day, 0, 0, 0)
        start_this = datetime(now.year, now.month, 1, 0, 0, 0)
        end_this = datetime(now.year + 1, 1, 1, 0, 0, 0) if now.month == 12 else datetime(now.year, now.month + 1, 1, 0, 0, 0)
        now_ym = now.strftime("%Y-%m")

        user_id = getattr(user, 'ma_nd', None) or getattr(user, 'id', None)
        if not user_id:
            return

        # Tự động kết chuyển hạn mức chưa dùng hết từ tháng trước sang tháng này
        try:
            NganSachService.tu_dong_ket_chuyen_thang_moi(db, user_id, now_ym)
        except Exception as e:
            print("Lỗi tự động kết chuyển ngân sách:", e)

        chi_categories = db.query(DanhMuc).filter(
            DanhMuc.ma_nd == user_id,
            DanhMuc.loai_dm == "chi"
        ).all()

        over_jars = []
        approaching_jars = []
        for c in chi_categories:
            ns = db.query(NganSach).filter(
                NganSach.ma_nd == user_id,
                NganSach.ma_dm == c.ma_dm,
                NganSach.thang_nam == now_ym
            ).first()
            limit = float(ns.han_muc) if (ns and ns.han_muc and ns.han_muc > 0) else 0.0
            if limit <= 0:
                continue

            txs = db.query(GiaoDich).filter(
                GiaoDich.ma_nd == user_id,
                GiaoDich.ma_dm == c.ma_dm,
                GiaoDich.loai_gd == "chi",
                GiaoDich.ngay_gd >= start_this,
                GiaoDich.ngay_gd < end_this
            ).all()
            spent = sum(t.so_tien for t in txs if t.so_tien)
            if spent > limit:
                pct = round((spent / limit) * 100)
                over_jars.append({"name": c.ten_dm, "spent": spent, "limit": limit, "pct": pct})
            elif spent >= limit * 0.9:
                pct = round((spent / limit) * 100)
                approaching_jars.append({"name": c.ten_dm, "spent": spent, "limit": limit, "pct": pct})

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
    def tinh_chi_tiet_vi_chinh(db: Session, ma_nd: int) -> dict:
        """
        Tính chi tiết tài chính ví chính và số dư thực tế khả dụng.
        Số dư ví chính = Tổng thu thực tế - Tổng chi thực tế (bao gồm tiền đã nạp vào các hũ tiết kiệm đang hoạt động)
                        - Tổng hạn mức khả dụng chưa chi tiêu đang nằm trong các hũ chi tiêu của tháng hiện tại.
        Loại trừ các khoản tiền hoàn trả hoặc mục tiêu tiết kiệm đã xóa.
        """
        txs = db.query(GiaoDich).filter(GiaoDich.ma_nd == ma_nd).all()

        def _is_refund_or_deleted(t):
            if not t.ghi_chu:
                return False
            gc = t.ghi_chu.lower()
            return "(đã xoá)" in gc or "(đã xóa)" in gc or "hoàn trả" in gc or "hoàn tiền" in gc

        t_thu = sum(
            t.so_tien for t in txs 
            if t.loai_gd == "thu"
        )
        t_chi = sum(
            t.so_tien for t in txs 
            if t.loai_gd == "chi" and not _is_refund_or_deleted(t)
        )

        now = datetime.now()
        start_month = datetime(now.year, now.month, 1)
        end_month = datetime(now.year + 1, 1, 1) if now.month == 12 else datetime(now.year, now.month + 1, 1)
        now_ym = now.strftime("%Y-%m")

        categories = db.query(DanhMuc).filter(
            DanhMuc.ma_nd == ma_nd,
            DanhMuc.loai_dm == "chi",
            DanhMuc.ten_dm != "Tiết kiệm"
        ).all()

        total_unspent_in_jars = 0.0
        total_limit_in_jars = 0.0

        for c in categories:
            ns = db.query(NganSach).filter(
                NganSach.ma_nd == ma_nd,
                NganSach.ma_dm == c.ma_dm,
                NganSach.thang_nam == now_ym
            ).first()
            # Ưu tiên dùng hạn mức cấp mới (do người dùng đặt cho tháng này)
            # Nếu không, dùng hạn mức gốc của danh mục (c.han_muc)
            # Tránh dùng ns.han_muc bị thổi phồng do kết chuyển cũ
            if ns and ns.han_muc_cap_moi and ns.han_muc_cap_moi > 0:
                limit = float(ns.han_muc_cap_moi)
            elif ns and ns.han_muc is not None and ns.han_muc > 0 and (not ns.so_du_chuyen_sang or ns.so_du_chuyen_sang == 0):
                limit = float(ns.han_muc)
            else:
                limit = float(c.han_muc or 0.0)

            if limit > 0:
                total_limit_in_jars += limit
                spent = sum(
                    t.so_tien for t in txs
                    if t.ma_dm == c.ma_dm and t.loai_gd == "chi" and not _is_refund_or_deleted(t)
                    and t.ngay_gd and t.ngay_gd >= start_month and t.ngay_gd < end_month
                )
                unspent = max(0.0, limit - spent)
                total_unspent_in_jars += unspent

        so_du = float(t_thu - t_chi - total_unspent_in_jars)
        return {
            "so_du": so_du,
            "tong_thu": float(t_thu),
            "tong_chi": float(t_chi),
            "tong_cap_hu": float(total_limit_in_jars),
            "tong_trong_hu": float(total_unspent_in_jars)
        }

    @staticmethod
    def tinh_so_du_vi_chinh(db: Session, ma_nd: int) -> float:
        """
        Tính số dư thực tế khả dụng của ví chính.
        Số dư ví chính = Tổng thu thực tế - Tổng chi thực tế (bao gồm tiền đã nạp vào các hũ tiết kiệm đang hoạt động)
                        - Tổng hạn mức khả dụng chưa chi tiêu đang nằm trong các hũ chi tiêu của tháng hiện tại.
        Loại trừ các khoản tiền hoàn trả hoặc mục tiêu tiết kiệm đã xóa.
        """
        return NganSachService.tinh_chi_tiet_vi_chinh(db, ma_nd)["so_du"]

    @staticmethod
    def tu_dong_ket_chuyen_thang_moi(db: Session, ma_nd: int, target_ym: Optional[str] = None) -> List[dict]:
        """
        Tự động hoàn trả số dư hạn mức chưa dùng hết từ tháng trước về ví chính.
        - Nếu tháng trước danh mục chi tiêu có hạn mức và chưa chi tiêu hết, số dư còn lại TỰ ĐỘNG HOÀN VỀ VÍ CHÍNH.
        - Tạo giao dịch THU để ghi nhận khoản tiền được hoàn về.
        - Ghi lại lịch sử chi tiết vào bảng KetChuyenNganSach để phục vụ tra cứu.
        - Tạo thông báo hệ thống tóm tắt số tiền đã được hoàn về ví chính.
        """
        if not target_ym:
            target_ym = datetime.now().strftime("%Y-%m")

        target_dt = datetime.strptime(f"{target_ym}-01", "%Y-%m-%d")
        if target_dt.month == 1:
            prev_dt = datetime(target_dt.year - 1, 12, 1)
        else:
            prev_dt = datetime(target_dt.year, target_dt.month - 1, 1)

        prev_ym = prev_dt.strftime("%Y-%m")
        start_prev = datetime(prev_dt.year, prev_dt.month, 1, 0, 0, 0)
        end_prev = datetime(target_dt.year, target_dt.month, 1, 0, 0, 0)

        categories = db.query(DanhMuc).filter(
            DanhMuc.ma_nd == ma_nd,
            DanhMuc.loai_dm == "chi",
            DanhMuc.ten_dm != "Tiết kiệm"
        ).all()

        # Tìm một danh mục thu để gắn vào giao dịch hoàn tiền
        thu_category = db.query(DanhMuc).filter(
            DanhMuc.ma_nd == ma_nd,
            DanhMuc.loai_dm == "thu"
        ).first()
        if not thu_category:
            thu_category = DanhMuc(
                ma_nd=ma_nd,
                ten_dm="Hoàn tiền ngân sách",
                loai_dm="thu",
                icon="wallet",
                mau_sac="#10b981",
                han_muc=0.0
            )
            db.add(thu_category)
            db.flush()

        rolled_over_items = []

        for c in categories:
            # Kiểm tra xem danh mục này đã được kết chuyển từ prev_ym sang target_ym chưa
            existing_kc = db.query(KetChuyenNganSach).filter(
                KetChuyenNganSach.ma_nd == ma_nd,
                KetChuyenNganSach.ma_dm == c.ma_dm,
                KetChuyenNganSach.thang_nguon == prev_ym,
                KetChuyenNganSach.thang_dich == target_ym
            ).first()
            if existing_kc:
                continue

            # Xác định hạn mức tháng trước
            ns_prev = db.query(NganSach).filter(
                NganSach.ma_nd == ma_nd,
                NganSach.ma_dm == c.ma_dm,
                NganSach.thang_nam == prev_ym
            ).first()

            limit_prev = 0.0
            if ns_prev and ns_prev.han_muc is not None and ns_prev.han_muc > 0:
                limit_prev = float(ns_prev.han_muc)
            elif c.han_muc and c.han_muc > 0:
                limit_prev = float(c.han_muc)

            # Tính số tiền đã chi thực tế trong tháng trước
            spent_prev = db.query(func.coalesce(func.sum(GiaoDich.so_tien), 0.0)).filter(
                GiaoDich.ma_nd == ma_nd,
                GiaoDich.ma_dm == c.ma_dm,
                GiaoDich.loai_gd == "chi",
                GiaoDich.ngay_gd >= start_prev,
                GiaoDich.ngay_gd < end_prev
            ).scalar() or 0.0

            # Nếu tháng trước có hạn mức
            if limit_prev > 0:
                # Đảm bảo bản ghi NganSach của tháng trước tồn tại và lưu đúng số đã chi
                if not ns_prev:
                    ns_prev = NganSach(
                        ma_nd=ma_nd,
                        ma_dm=c.ma_dm,
                        thang_nam=prev_ym,
                        han_muc=limit_prev,
                        so_tien_da_chi=spent_prev,
                        canh_bao_da_gui=(spent_prev > limit_prev)
                    )
                    db.add(ns_prev)
                else:
                    ns_prev.so_tien_da_chi = spent_prev

                remaining = max(0.0, limit_prev - spent_prev)
                # Ghi lại lịch sử xử lý kết chuyển (kể cả khi đã dùng hết hạn mức)
                kc = KetChuyenNganSach(
                    ma_nd=ma_nd,
                    ma_dm=c.ma_dm,
                    thang_nguon=prev_ym,
                    thang_dich=target_ym,
                    han_muc_thang_truoc=limit_prev,
                    da_chi_thang_truoc=spent_prev,
                    so_tien_chuyen=remaining,
                    ngay_tao=datetime.now(),
                    ghi_chu=f"Kết chuyển hạn mức hũ \"{c.ten_dm}\" từ Tháng {prev_dt.month:02d}/{prev_dt.year} sang Tháng {target_dt.month:02d}/{target_dt.year}"
                )
                db.add(kc)

                if remaining > 0:
                    rolled_over_items.append({
                        "name": c.ten_dm,
                        "amount": remaining,
                        "prev_spent": spent_prev,
                        "prev_limit": limit_prev
                    })
                    # Số dư hạn mức chưa dùng của tháng trước tự động quay về trạng thái khả dụng của ví chính
                    # một cách tự nhiên (do tháng mới bắt đầu tính lại unspent của tháng mới).
                    # Không tạo giao dịch THU giả mạo để tránh làm sai lệch tổng thu và báo cáo tài chính.

        db.flush()

        # =========================================================================
        # PHASE 2: Cấp ngân sách tháng mới chảy vào các hũ từ trên xuống (Waterfall)
        # =========================================================================
        chi_categories_ordered = db.query(DanhMuc).filter(
            DanhMuc.ma_nd == ma_nd,
            DanhMuc.loai_dm == "chi",
            DanhMuc.ten_dm != "Tiết kiệm"
        ).order_by(DanhMuc.ma_dm.asc()).all()

        unallocated_cats = []
        for c in chi_categories_ordered:
            ns_curr = db.query(NganSach).filter(
                NganSach.ma_nd == ma_nd,
                NganSach.ma_dm == c.ma_dm,
                NganSach.thang_nam == target_ym
            ).first()
            if not ns_curr:
                unallocated_cats.append(c)

        if unallocated_cats:
            # Tính tiền khả dụng trong ví chính trước khi phân bổ vào các hũ tháng mới
            txs = db.query(GiaoDich).filter(GiaoDich.ma_nd == ma_nd).all()
            def _is_refund_or_del(t):
                if not t.ghi_chu:
                    return False
                gc = t.ghi_chu.lower()
                return "(đã xoá)" in gc or "(đã xóa)" in gc or "hoàn trả" in gc or "hoàn tiền" in gc

            t_thu = sum(
                t.so_tien for t in txs 
                if t.loai_gd == "thu" and not (t.ghi_chu and ("hoàn tiền từ hũ tiết kiệm" in t.ghi_chu.lower() or "hoàn trả hạn mức" in t.ghi_chu.lower()))
            )
            t_chi = sum(
                t.so_tien for t in txs 
                if t.loai_gd == "chi" and not _is_refund_or_del(t)
            )

            # Trừ hạn mức của các hũ đã được cấp trước đó trong target_ym (nếu có)
            existing_allocated = db.query(func.coalesce(func.sum(NganSach.han_muc), 0.0)).filter(
                NganSach.ma_nd == ma_nd,
                NganSach.thang_nam == target_ym
            ).scalar() or 0.0

            available_wallet = max(0.0, (t_thu - t_chi) - existing_allocated)

            fully_funded = []
            partially_funded = []
            unfunded = []

            for c in unallocated_cats:
                # Định mức mong muốn từ tháng trước
                kc_item = db.query(KetChuyenNganSach).filter(
                    KetChuyenNganSach.ma_nd == ma_nd,
                    KetChuyenNganSach.ma_dm == c.ma_dm,
                    KetChuyenNganSach.thang_dich == target_ym
                ).first()

                target_limit = 0.0
                if kc_item and kc_item.han_muc_thang_truoc and kc_item.han_muc_thang_truoc > 0:
                    target_limit = float(kc_item.han_muc_thang_truoc)
                else:
                    ns_prev = db.query(NganSach).filter(
                        NganSach.ma_nd == ma_nd,
                        NganSach.ma_dm == c.ma_dm,
                        NganSach.thang_nam == prev_ym
                    ).first()
                    if ns_prev and ns_prev.han_muc and ns_prev.han_muc > 0:
                        target_limit = float(ns_prev.han_muc)
                    elif c.han_muc and c.han_muc > 0:
                        target_limit = float(c.han_muc)

                if target_limit <= 0:
                    ns_new = NganSach(
                        ma_nd=ma_nd,
                        ma_dm=c.ma_dm,
                        thang_nam=target_ym,
                        han_muc=0.0,
                        han_muc_cap_moi=0.0,
                        so_du_chuyen_sang=0.0,
                        so_tien_da_chi=0.0
                    )
                    db.add(ns_new)
                    # KHÔNG ghi đè c.han_muc — chỉ cập nhật bảng NganSach
                    continue

                if available_wallet >= target_limit:
                    allocated = target_limit
                    available_wallet -= target_limit
                    fully_funded.append({
                        "name": c.ten_dm,
                        "allocated": allocated,
                        "target": target_limit
                    })
                elif available_wallet > 0:
                    allocated = available_wallet
                    shortage = target_limit - allocated
                    available_wallet = 0.0
                    partially_funded.append({
                        "name": c.ten_dm,
                        "allocated": allocated,
                        "target": target_limit,
                        "shortage": shortage
                    })
                else:
                    allocated = 0.0
                    shortage = target_limit
                    unfunded.append({
                        "name": c.ten_dm,
                        "allocated": 0.0,
                        "target": target_limit,
                        "shortage": shortage
                    })

                ns_new = NganSach(
                    ma_nd=ma_nd,
                    ma_dm=c.ma_dm,
                    thang_nam=target_ym,
                    han_muc=allocated,
                    han_muc_cap_moi=allocated,
                    so_du_chuyen_sang=0.0,
                    so_tien_da_chi=0.0
                )
                db.add(ns_new)
                # KHÔNG ghi đè c.han_muc — giữ nguyên hạn mức gốc DanhMuc

            # Thông báo tự động về tình trạng cấp tiền vào các hũ
            if partially_funded or unfunded:
                tieu_de_tb = f"⚠️ CẢNH BÁO: VÍ CHÍNH KHÔNG ĐỦ TIỀN CẤP ĐỦ HẠN MỨC THÁNG {target_dt.month:02d}/{target_dt.year}"
                lines = [f"Hệ thống đã tự động cấp hạn mức Tháng {target_dt.month:02d}/{target_dt.year} từ ví chính vào các hũ theo thứ tự ưu tiên:\n"]
                if fully_funded:
                    lines.append("✅ Hũ đã cấp đủ hạn mức định mức:")
                    for f in fully_funded:
                        lines.append(f"• Hũ \"{f['name']}\": {f['allocated']:,.0f} đ (100%)")
                    lines.append("")
                if partially_funded:
                    lines.append("⚠️ Hũ chưa đủ hạn mức (Ví chính hết tiền giữa chừng):")
                    for p in partially_funded:
                        lines.append(f"• Hũ \"{p['name']}\": chỉ cấp được {p['allocated']:,.0f} / {p['target']:,.0f} đ (còn thiếu {p['shortage']:,.0f} đ)")
                    lines.append("")
                if unfunded:
                    lines.append("❌ Hũ chưa được cấp tiền (Ví chính còn 0 đ):")
                    for u in unfunded:
                        lines.append(f"• Hũ \"{u['name']}\": 0 / {u['target']:,.0f} đ (còn thiếu {u['shortage']:,.0f} đ)")
                    lines.append("")

                total_shortage = sum(p['shortage'] for p in partially_funded) + sum(u['shortage'] for u in unfunded)
                lines.append(f"💡 Tổng số tiền còn thiếu để đạt định mức: {total_shortage:,.0f} đ.")
                lines.append("Bạn có thể nạp thêm thu nhập vào ví chính để cấp thêm cho các hũ, hoặc tự do điều chỉnh lại hạn mức bất kỳ lúc nào!")

                noi_dung_tb = "\n".join(lines)
                existing_shortage_tb = db.query(ThongBao).filter(
                    ThongBao.ma_nd == ma_nd,
                    ThongBao.tieu_de == tieu_de_tb
                ).first()
                if not existing_shortage_tb:
                    db.add(ThongBao(ma_nd=ma_nd, tieu_de=tieu_de_tb, noi_dung=noi_dung_tb, da_xem=False, ngay_tao=datetime.now()))

            elif fully_funded:
                tieu_de_tb = f"✨ TỰ ĐỘNG CẤP HẠN MỨC THÁNG {target_dt.month:02d}/{target_dt.year}"
                lines = [f"Hệ thống đã tự động cấp hạn mức Tháng {target_dt.month:02d}/{target_dt.year} từ ví chính cho {len(fully_funded)} hũ chi tiêu theo thứ tự ưu tiên:\n"]
                for f in fully_funded:
                    lines.append(f"• Hũ \"{f['name']}\": {f['allocated']:,.0f} đ")
                lines.append(f"\n✅ Tất cả các hũ đã được cấp đủ 100% hạn mức theo định mức tháng trước!")
                lines.append(f"Số dư khả dụng còn lại trong ví chính: {available_wallet:,.0f} đ.")
                noi_dung_tb = "\n".join(lines)
                existing_full_tb = db.query(ThongBao).filter(
                    ThongBao.ma_nd == ma_nd,
                    ThongBao.tieu_de == tieu_de_tb
                ).first()
                if not existing_full_tb:
                    db.add(ThongBao(ma_nd=ma_nd, tieu_de=tieu_de_tb, noi_dung=noi_dung_tb, da_xem=False, ngay_tao=datetime.now()))

        db.commit()
        return rolled_over_items

    @staticmethod
    def kiem_tra_hu_con_thieu(db: Session, ma_nd: int) -> dict:
        """
        Kiem tra cac hu con thieu so voi dinh muc thang nay (KHONG tu dong cap tien).
        Tra ve danh sach hu con thieu de frontend hoi nguoi dung co muon bo sung khong.
        """
        now = datetime.now()
        now_ym = now.strftime("%Y-%m")
        if now.month == 1:
            prev_dt = datetime(now.year - 1, 12, 1)
        else:
            prev_dt = datetime(now.year, now.month - 1, 1)
        prev_ym = prev_dt.strftime("%Y-%m")

        chi_categories = db.query(DanhMuc).filter(
            DanhMuc.ma_nd == ma_nd,
            DanhMuc.loai_dm == "chi",
            DanhMuc.ten_dm != "Tiết kiệm"
        ).order_by(DanhMuc.ma_dm.asc()).all()

        wallet_info = NganSachService.tinh_chi_tiet_vi_chinh(db, ma_nd)
        available_wallet = max(0.0, wallet_info["so_du"])
        shortage_list = []
        total_shortage = 0.0

        for c in chi_categories:
            ns_curr = db.query(NganSach).filter(
                NganSach.ma_nd == ma_nd, NganSach.ma_dm == c.ma_dm,
                NganSach.thang_nam == now_ym
            ).first()
            ns_prev = db.query(NganSach).filter(
                NganSach.ma_nd == ma_nd, NganSach.ma_dm == c.ma_dm,
                NganSach.thang_nam == prev_ym
            ).first()
            kc = db.query(KetChuyenNganSach).filter(
                KetChuyenNganSach.ma_nd == ma_nd,
                KetChuyenNganSach.ma_dm == c.ma_dm,
                KetChuyenNganSach.thang_dich == now_ym
            ).first()

            target_limit = 0.0
            if kc and kc.han_muc_thang_truoc and kc.han_muc_thang_truoc > 0:
                target_limit = float(kc.han_muc_thang_truoc)
            elif ns_prev and ns_prev.han_muc and ns_prev.han_muc > 0:
                target_limit = float(ns_prev.han_muc)
            elif c.han_muc and c.han_muc > 0:
                target_limit = float(c.han_muc)

            if target_limit <= 0:
                continue
            current_limit = float(ns_curr.han_muc or 0.0) if ns_curr else 0.0
            shortage = max(0.0, target_limit - current_limit)
            if shortage > 0:
                shortage_list.append({
                    "ma_dm": c.ma_dm, "name": c.ten_dm,
                    "current_limit": current_limit,
                    "target_limit": target_limit,
                    "shortage": shortage
                })
                total_shortage += shortage

        return {
            "co_hu_thieu": len(shortage_list) > 0,
            "total_shortage": total_shortage,
            "available_wallet": available_wallet,
            "shortage_list": shortage_list
        }

    @staticmethod
    def thuc_hien_bo_sung_hu(db: Session, ma_nd: int) -> dict:
        """
        Thực hiện bổ sung tiền từ ví chính vào các hũ còn thiếu (sau khi người dùng xác nhận).
        Trừ từ ví chính vào các hũ còn thiếu theo thứ tự ưu tiên (waterfall).
        """
        now = datetime.now()
        now_ym = now.strftime("%Y-%m")
        if now.month == 1:
            prev_dt = datetime(now.year - 1, 12, 1)
        else:
            prev_dt = datetime(now.year, now.month - 1, 1)
        prev_ym = prev_dt.strftime("%Y-%m")

        wallet_info = NganSachService.tinh_chi_tiet_vi_chinh(db, ma_nd)
        available_wallet = max(0.0, wallet_info["so_du"])
        if available_wallet <= 0:
            return {"thuc_hien": False, "ly_do": "Ví chính không còn tiền khả dụng."}

        chi_categories = db.query(DanhMuc).filter(
            DanhMuc.ma_nd == ma_nd,
            DanhMuc.loai_dm == "chi",
            DanhMuc.ten_dm != "Tiết kiệm"
        ).order_by(DanhMuc.ma_dm.asc()).all()

        fully_topped = []
        partially_topped = []

        for c in chi_categories:
            ns_curr = db.query(NganSach).filter(
                NganSach.ma_nd == ma_nd, NganSach.ma_dm == c.ma_dm,
                NganSach.thang_nam == now_ym
            ).first()
            ns_prev = db.query(NganSach).filter(
                NganSach.ma_nd == ma_nd, NganSach.ma_dm == c.ma_dm,
                NganSach.thang_nam == prev_ym
            ).first()
            kc = db.query(KetChuyenNganSach).filter(
                KetChuyenNganSach.ma_nd == ma_nd,
                KetChuyenNganSach.ma_dm == c.ma_dm,
                KetChuyenNganSach.thang_dich == now_ym
            ).first()

            target_limit = 0.0
            if kc and kc.han_muc_thang_truoc and kc.han_muc_thang_truoc > 0:
                target_limit = float(kc.han_muc_thang_truoc)
            elif ns_prev and ns_prev.han_muc and ns_prev.han_muc > 0:
                target_limit = float(ns_prev.han_muc)
            elif c.han_muc and c.han_muc > 0:
                target_limit = float(c.han_muc)

            if target_limit <= 0:
                continue
            current_limit = float(ns_curr.han_muc or 0.0) if ns_curr else 0.0
            shortage = max(0.0, target_limit - current_limit)
            if shortage <= 0:
                continue
            if available_wallet <= 0:
                partially_topped.append({
                    "name": c.ten_dm, "topup": 0.0,
                    "current": current_limit, "target": target_limit,
                    "shortage": shortage, "fully": False
                })
                continue
            topup = min(shortage, available_wallet)
            available_wallet -= topup
            new_limit = current_limit + topup
            if ns_curr:
                ns_curr.han_muc = new_limit
                ns_curr.han_muc_cap_moi = float(ns_curr.han_muc_cap_moi or 0.0) + topup
            else:
                ns_curr = NganSach(
                    ma_nd=ma_nd, ma_dm=c.ma_dm, thang_nam=now_ym,
                    han_muc=new_limit, han_muc_cap_moi=topup,
                    so_du_chuyen_sang=0.0, so_tien_da_chi=0.0
                )
                db.add(ns_curr)
            c.han_muc = new_limit
            remaining_shortage = max(0.0, target_limit - new_limit)
            if remaining_shortage <= 0:
                fully_topped.append({
                    "name": c.ten_dm, "topup": topup,
                    "current": new_limit, "target": target_limit, "fully": True
                })
            else:
                partially_topped.append({
                    "name": c.ten_dm, "topup": topup, "current": new_limit,
                    "target": target_limit, "shortage": remaining_shortage, "fully": False
                })

        db.flush()
        all_topped = fully_topped + partially_topped
        if all_topped:
            now_m = now.month
            now_y = now.year
            tieu_de = f"\u2705 B\u1ed4 SUNG H\u1ea0N M\u1ee8C C\u00c1C H\u0168 \u2013 TH\u00c1NG {now_m:02d}/{now_y}"
            lines_msg = []
            if fully_topped:
                lines_msg.append("\u2705 H\u0169 \u0111\u00e3 \u0111\u01b0\u1ee3c c\u1ea5p \u0111\u1ee7 h\u1ea1n m\u1ee9c:")
                for f in fully_topped:
                    lines_msg.append(f"  \u2022 H\u0169 \"{f['name']}\": +{f['topup']:,.0f} \u0111 \u2192 {f['current']:,.0f}/{f['target']:,.0f} \u0111 (100%)")
            if partially_topped:
                still = [p for p in partially_topped if p.get("shortage", 0) > 0]
                if still:
                    lines_msg.append("\n\u26a0\ufe0f H\u0169 v\u1eabn c\u00f2n thi\u1ebfu:")
                    for p in still:
                        pct = round((p["current"] / p["target"]) * 100) if p["target"] > 0 else 0
                        lines_msg.append(
                            f"  \u2022 H\u0169 \"{p['name']}\": +{p['topup']:,.0f} \u0111 \u2192 {p['current']:,.0f}/{p['target']:,.0f} \u0111 ({pct}%) \u2014 c\u00f2n thi\u1ebfu {p['shortage']:,.0f} \u0111"
                        )
            noi_dung = "\n".join(lines_msg) if lines_msg else ""
            existing = db.query(ThongBao).filter(
                ThongBao.ma_nd == ma_nd, ThongBao.tieu_de == tieu_de,
                ThongBao.ngay_tao >= datetime(now.year, now.month, now.day, now.hour, now.minute, 0)
            ).first()
            if not existing:
                db.add(ThongBao(ma_nd=ma_nd, tieu_de=tieu_de, noi_dung=noi_dung, da_xem=False, ngay_tao=now))
        db.commit()
        return {
            "thuc_hien": bool(all_topped),
            "fully_topped": fully_topped,
            "partially_topped": partially_topped,
            "vi_chinh_con_lai": available_wallet
        }

    @staticmethod
    def cap_tien_waterfall_khi_co_thu_nhap(db: Session, ma_nd: int, so_tien_thu_moi: float) -> dict:
        """
        Khi nguoi dung ghi nhan giao dich THU (thu nhap moi):
        KHONG tu dong phan bo vao hu. Chi kiem tra cac hu con thieu va tra ve thong tin
        de frontend hoi nguoi dung co muon bo sung khong.
        """
        kiem_tra = NganSachService.kiem_tra_hu_con_thieu(db, ma_nd)
        if not kiem_tra["co_hu_thieu"]:
            return {"thuc_hien": False, "ly_do": "Tat ca cac hu da du han muc.", "kiem_tra": kiem_tra}
        return {
            "thuc_hien": False,
            "can_confirm": True,
            "kiem_tra": kiem_tra
        }

    @staticmethod
    def lay_lich_su_ket_chuyen(
        db: Session, ma_nd: int,
        thang_nam: Optional[str] = None, ma_dm: Optional[int] = None
    ) -> List[KetChuyenNganSachResponse]:
        """Tra cuu lich su ket chuyen han muc cua nguoi dung"""
        query = db.query(KetChuyenNganSach).filter(KetChuyenNganSach.ma_nd == ma_nd)
        if thang_nam:
            query = query.filter(
                (KetChuyenNganSach.thang_nguon == thang_nam) |
                (KetChuyenNganSach.thang_dich == thang_nam)
            )
        if ma_dm:
            query = query.filter(KetChuyenNganSach.ma_dm == ma_dm)
        records = query.order_by(KetChuyenNganSach.ngay_tao.desc(), KetChuyenNganSach.ma_kc.desc()).all()
        results = []
        for r in records:
            dm = db.query(DanhMuc).filter(DanhMuc.ma_dm == r.ma_dm).first()
            ten_dm = dm.ten_dm if dm else "Danh muc"
            results.append(KetChuyenNganSachResponse(
                ma_kc=r.ma_kc, ma_nd=r.ma_nd, ma_dm=r.ma_dm, ten_dm=ten_dm,
                thang_nguon=r.thang_nguon, thang_dich=r.thang_dich,
                han_muc_thang_truoc=r.han_muc_thang_truoc, da_chi_thang_truoc=r.da_chi_thang_truoc,
                so_tien_chuyen=r.so_tien_chuyen, ngay_tao=r.ngay_tao, ghi_chu=r.ghi_chu
            ))
        return results

