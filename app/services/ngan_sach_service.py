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
            if t.loai_gd == "thu" and not (t.ghi_chu and ("hoàn tiền từ hũ tiết kiệm" in t.ghi_chu.lower() or "hoàn trả hạn mức" in t.ghi_chu.lower()))
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
            limit = float(ns.han_muc) if (ns and ns.han_muc is not None and ns.han_muc > 0) else float(c.han_muc or 0.0)

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
        Tự động kết chuyển số dư hạn mức chưa dùng hết từ tháng trước sang tháng mới (BR - Hạn mức).
        - Nếu tháng trước danh mục chi tiêu có hạn mức và chưa chi tiêu hết, số dư còn lại tự động kết chuyển sang tháng mới.
        - Ghi lại lịch sử chi tiết vào bảng KetChuyenNganSach để phục vụ tra cứu.
        - Tạo thông báo hệ thống tóm tắt số dư đã kết chuyển sang tháng mới.
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

                remaining = limit_prev - spent_prev
                if remaining > 0:
                    # Ghi lại lịch sử kết chuyển
                    kc = KetChuyenNganSach(
                        ma_nd=ma_nd,
                        ma_dm=c.ma_dm,
                        thang_nguon=prev_ym,
                        thang_dich=target_ym,
                        han_muc_thang_truoc=limit_prev,
                        da_chi_thang_truoc=spent_prev,
                        so_tien_chuyen=remaining,
                        ngay_tao=datetime.now(),
                        ghi_chu=f"Kết chuyển số dư hạn mức chưa dùng hết từ Tháng {prev_dt.month:02d}/{prev_dt.year} sang Tháng {target_dt.month:02d}/{target_dt.year}"
                    )
                    db.add(kc)

                    rolled_over_items.append({
                        "name": c.ten_dm,
                        "amount": remaining,
                        "prev_spent": spent_prev,
                        "prev_limit": limit_prev
                    })

                    # Cập nhật hoặc tạo NganSach cho tháng đích
                    ns_target = db.query(NganSach).filter(
                        NganSach.ma_nd == ma_nd,
                        NganSach.ma_dm == c.ma_dm,
                        NganSach.thang_nam == target_ym
                    ).first()

                    if ns_target:
                        ns_target.so_du_chuyen_sang = (ns_target.so_du_chuyen_sang or 0.0) + remaining
                        cap_moi = ns_target.han_muc_cap_moi or 0.0
                        ns_target.han_muc = cap_moi + ns_target.so_du_chuyen_sang
                    else:
                        ns_target = NganSach(
                            ma_nd=ma_nd,
                            ma_dm=c.ma_dm,
                            thang_nam=target_ym,
                            han_muc=remaining,
                            so_tien_da_chi=0.0,
                            canh_bao_da_gui=False,
                            so_du_chuyen_sang=remaining,
                            han_muc_cap_moi=0.0
                        )
                        db.add(ns_target)

        if rolled_over_items:
            # Tạo thông báo hệ thống
            tieu_de = f"🔄 KẾT CHUYỂN HẠN MỨC SANG THÁNG {target_dt.month:02d}/{target_dt.year}"
            details = "\n".join([
                f"• Hũ \"{item['name']}\": số dư còn {item['amount']:,.0f} đ (đã dùng {item['prev_spent']:,.0f}/{item['prev_limit']:,.0f} đ) đã chuyển sang Tháng {target_dt.month:02d}"
                for item in rolled_over_items
            ])
            noi_dung = (
                f"Hệ thống đã tự động kết chuyển các khoản hạn mức chưa dùng hết từ Tháng {prev_dt.month:02d}/{prev_dt.year} "
                f"sang Tháng {target_dt.month:02d}/{target_dt.year} để bạn tiếp tục sử dụng:\n\n{details}\n\n"
                f"💡 Bạn có thể tra cứu lịch sử kết chuyển và cấp thêm hạn mức chi tiêu nếu có nhu cầu!"
            )
            existing_tb = db.query(ThongBao).filter(
                ThongBao.ma_nd == ma_nd,
                ThongBao.tieu_de == tieu_de
            ).first()
            if not existing_tb:
                db.add(ThongBao(ma_nd=ma_nd, tieu_de=tieu_de, noi_dung=noi_dung, da_xem=False, ngay_tao=datetime.now()))

        db.commit()
        return rolled_over_items

    @staticmethod
    def lay_lich_su_ket_chuyen(
        db: Session,
        ma_nd: int,
        thang_nam: Optional[str] = None,
        ma_dm: Optional[int] = None
    ) -> List[KetChuyenNganSachResponse]:
        """Tra cứu lịch sử kết chuyển hạn mức của người dùng"""
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
            ten_dm = dm.ten_dm if dm else "Danh mục"
            results.append(KetChuyenNganSachResponse(
                ma_kc=r.ma_kc,
                ma_nd=r.ma_nd,
                ma_dm=r.ma_dm,
                ten_dm=ten_dm,
                thang_nguon=r.thang_nguon,
                thang_dich=r.thang_dich,
                han_muc_thang_truoc=r.han_muc_thang_truoc,
                da_chi_thang_truoc=r.da_chi_thang_truoc,
                so_tien_chuyen=r.so_tien_chuyen,
                ngay_tao=r.ngay_tao,
                ghi_chu=r.ghi_chu
            ))
        return results

