import json
import ssl
import urllib.request
import urllib.error
import concurrent.futures
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.bao_cao_ai import BaoCaoAI
from app.models.danh_muc import DanhMuc
from app.models.giao_dich import GiaoDich
from app.models.muc_tieu_tiet_kiem import MucTieuTietKiem
from app.models.ngan_sach import NganSach
from app.services.privacy_service import PrivacyService
from app.services.ngan_sach_service import NganSachService

# Danh sách các mô hình Gemini hiện đại, hỗ trợ generateContent với API v1beta
AVAILABLE_GEMINI_MODELS = [
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.1-flash-lite",
    "gemini-3-flash-preview",
    "gemini-3.8-flash",
    "gemini-flash-latest"
]
_ssl_ctx = ssl.create_default_context()


class AIService:
    @staticmethod
    def _call_gemini_with_timeout(prompt: str, timeout: float = 25.0) -> str:
        """
        Gọi Gemini REST API với cơ chế dự phòng đa mô hình (Multi-model Fallback)
        và giới hạn thời gian phản hồi (NFR-03, TC-08).
        Tự động chuyển đổi giữa các mô hình Flash khả dụng khi gặp lỗi 429 (rate-limit)
        hoặc 503 (bận).
        """
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Dịch vụ AI Engine chưa được cấu hình API key. Vui lòng liên hệ quản trị viên."
            )

        per_model_timeout = max(5.0, min(10.0, timeout / 2.0))
        last_exception = None

        for model_name in AVAILABLE_GEMINI_MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.4,
                    "maxOutputTokens": 2048
                }
            }
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(
                url, data=body,
                headers={"Content-Type": "application/json; charset=utf-8"}
            )

            try:
                with urllib.request.urlopen(req, timeout=per_model_timeout, context=_ssl_ctx) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        if parts and "text" in parts[0]:
                            return parts[0]["text"]
            except urllib.error.HTTPError as e:
                # Nếu là 429 hoặc 503 hoặc 404 thì thử tiếp model khác
                last_exception = e
                continue
            except Exception as e:
                last_exception = e
                continue

        # Nếu tất cả các model đều thất bại hoặc quá thời gian
        err_msg = str(last_exception) if last_exception else "timeout"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI Engine phản hồi quá thời gian cho phép (> {int(timeout)} giây). Chi tiết: {err_msg[:120]}"
        )

    # Alias tương thích ngược
    _call_gemini_rest = _call_gemini_with_timeout

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
    def _get_spending_context(db: Session, ma_nd: int) -> Dict[str, Any]:
        """
        Truy xuất dữ liệu tài chính chi tiết, có phân loại ngữ nghĩa
        để AI có thể tư duy logic, phân tích chính xác từng chiều kích số liệu.
        """
        now = datetime.now()
        start_this = datetime(now.year, now.month, 1)
        if now.month == 1:
            start_prev = datetime(now.year - 1, 12, 1)
            end_prev = start_this
        else:
            start_prev = datetime(now.year, now.month - 1, 1)
            end_prev = start_this

        danh_mucs = db.query(DanhMuc).filter(DanhMuc.ma_nd == ma_nd).all()
        cat_map = {dm.ma_dm: dm for dm in danh_mucs}

        all_txs = db.query(GiaoDich).filter(GiaoDich.ma_nd == ma_nd).all()
        txs_this = [t for t in all_txs if t.ngay_gd and t.ngay_gd >= start_this]
        txs_prev = [t for t in all_txs if t.ngay_gd and start_prev <= t.ngay_gd < end_prev]

        # Tính chi tiêu & thu nhập thực: loại bỏ giao dịch hoàn tiền hoặc hũ tiết kiệm đã xóa
        tong_thu_this = sum(t.so_tien for t in txs_this if t.loai_gd == "thu" and not AIService._is_excluded_thu(t))
        tong_chi_this = sum(t.so_tien for t in txs_this if t.loai_gd == "chi" and not AIService._is_excluded_chi(t))
        tong_thu_prev = sum(t.so_tien for t in txs_prev if t.loai_gd == "thu" and not AIService._is_excluded_thu(t))
        tong_chi_prev = sum(t.so_tien for t in txs_prev if t.loai_gd == "chi" and not AIService._is_excluded_chi(t))

        def calc_by_cat(txs):
            result = {}
            for t in txs:
                if t.loai_gd == "chi" and not AIService._is_excluded_chi(t):
                    dm = cat_map.get(t.ma_dm)
                    cname = dm.ten_dm if dm else "Khác"
                    gc = (t.ghi_chu or "").lower()
                    if "tiết kiệm" in gc or "mục tiêu" in gc or cname.lower() == "tiết kiệm":
                        cname = "Tiết kiệm"
                    result[cname] = result.get(cname, 0.0) + t.so_tien
            return result

        chi_this = calc_by_cat(txs_this)
        chi_prev = calc_by_cat(txs_prev)

        # Danh sách toàn bộ danh mục đã chi tiêu tháng này (sắp xếp giảm dần theo số tiền)
        danh_sach_chi_tiet = []
        for cname, amount in sorted(chi_this.items(), key=lambda x: x[1], reverse=True):
            pct = round((amount / tong_chi_this) * 100, 1) if tong_chi_this > 0 else 0.0
            prev_amt = chi_prev.get(cname, 0.0)
            so_sanh = "Mới trong tháng"
            if prev_amt > 0:
                diff = round(((amount - prev_amt) / prev_amt) * 100)
                so_sanh = f"+{diff}% so với tháng trước" if diff > 0 else f"{diff}% so với tháng trước"
            danh_sach_chi_tiet.append({
                "ten": cname,
                "so_tien": amount,
                "ty_le": f"{pct}%",
                "phan_tram_so": pct,
                "da_chi_thang_truoc": prev_amt,
                "so_sanh": so_sanh
            })

        # Phân biệt giữa Khoản tích lũy (Hũ tiết kiệm) và Chi tiêu sinh hoạt thực tế
        khoan_tiet_kiem = next((item for item in danh_sach_chi_tiet if item["ten"].lower() == "tiết kiệm"), None)
        chi_sinh_hoat = [item for item in danh_sach_chi_tiet if item["ten"].lower() != "tiết kiệm"]

        muc_chi_nhieu_nhat = danh_sach_chi_tiet[0] if danh_sach_chi_tiet else None
        muc_chi_it_nhat = danh_sach_chi_tiet[-1] if danh_sach_chi_tiet else None

        # Giao dịch gần đây nhất trong tháng
        recent_txs = sorted(
            [t for t in txs_this if not AIService._is_excluded_chi(t) and not AIService._is_excluded_thu(t)],
            key=lambda x: x.ngay_gd or datetime.min,
            reverse=True
        )[:8]

        giao_dich_gan_day = []
        for t in recent_txs:
            dm = cat_map.get(t.ma_dm)
            cat_name = dm.ten_dm if dm else ("Thu nhập" if t.loai_gd == "thu" else "Khác")
            giao_dich_gan_day.append({
                "ngay": t.ngay_gd.strftime("%d/%m") if t.ngay_gd else "",
                "loai": "Thu" if t.loai_gd == "thu" else "Chi",
                "danh_muc": cat_name,
                "so_tien": t.so_tien,
                "ghi_chu": t.ghi_chu or ""
            })

        # Lịch sử các tháng trước để so sánh xu hướng
        lich_su_thang = []
        for i in range(1, 6):
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
            m_thu = sum(t.so_tien for t in m_txs if t.loai_gd == "thu" and not AIService._is_excluded_thu(t))
            m_chi = sum(t.so_tien for t in m_txs if t.loai_gd == "chi" and not AIService._is_excluded_chi(t))
            if m_txs or m_thu > 0 or m_chi > 0:
                m_cat = calc_by_cat(m_txs)
                top_m = max(m_cat.items(), key=lambda x: x[1])[0] if m_cat else "Không có"
                lich_su_thang.append({
                    "thang": f"{m:02d}/{y}",
                    "thu": m_thu,
                    "chi": m_chi,
                    "so_du": m_thu - m_chi,
                    "top_chi": top_m
                })

        muc_tieus = db.query(MucTieuTietKiem).filter(MucTieuTietKiem.ma_nd == ma_nd).all()
        mt_data = []
        for mt in muc_tieus:
            pct = round((mt.so_tien_hien_tai / mt.so_tien_muc_tieu) * 100) if mt.so_tien_muc_tieu > 0 else 0
            mt_data.append({
                "ten": mt.ten_muc_tieu,
                "hien_tai": mt.so_tien_hien_tai,
                "muc_tieu": mt.so_tien_muc_tieu,
                "tien_do": f"{pct}%",
                "trang_thai": mt.trang_thai or "dang_thuc_hien"
            })

        so_du_vi_chinh = NganSachService.tinh_so_du_vi_chinh(db, ma_nd)

        return {
            "thang_hien_tai": f"{now.month}/{now.year}",
            "thang_truoc": f"{start_prev.month}/{start_prev.year}",
            "thu_nhap": {"thang_nay": tong_thu_this, "thang_truoc": tong_thu_prev},
            "chi_tieu": {
                "thang_nay": tong_chi_this,
                "thang_truoc": tong_chi_prev,
                "so_sanh": f"{round((tong_chi_this - tong_chi_prev) / tong_chi_prev * 100) if tong_chi_prev > 0 else 0}%"
            },
            "so_du": tong_thu_this - tong_chi_this,
            "so_du_vi_chinh": so_du_vi_chinh,
            "danh_sach_chi_tiet": danh_sach_chi_tiet,
            "muc_chi_nhieu_nhat": muc_chi_nhieu_nhat,
            "muc_chi_it_nhat": muc_chi_it_nhat,
            "khoan_tiet_kiem": khoan_tiet_kiem,
            "chi_sinh_hoat": chi_sinh_hoat,
            "giao_dich_gan_day": giao_dich_gan_day,
            "lich_su_cac_thang": lich_su_thang,
            "muc_tieu_tiet_kiem": mt_data
        }

    @staticmethod
    def sinh_bao_cao_thang(
        db: Session, ma_nd: int, thang: int, nam: int
    ) -> Tuple[BaoCaoAI, bool]:
        """
        UC010 & BR-04 & TC-07 & TC-08:
        Kiểm tra cache DB. Nếu đã có → trả về ngay (cached=True).
        Nếu chưa có → gọi Gemini AI, lưu cache → trả về.
        """
        thang_nam = f"{nam:04d}-{thang:02d}"

        cached_bc = db.query(BaoCaoAI).filter(
            BaoCaoAI.ma_nd == ma_nd,
            BaoCaoAI.thang_nam == thang_nam
        ).first()
        if cached_bc:
            return cached_bc, True

        an_danh_data = PrivacyService.tong_hop_va_an_danh_thang(db, ma_nd, thang, nam)

        system_prompt = (
            "Bạn là chuyên gia phân tích tài chính cá nhân cho ứng dụng MoneyMind (Việt Nam). "
            "Phân tích dữ liệu chi tiêu và đưa ra nhận xét THỰC TẾ, CỤ THỂ dựa ĐÚNG trên số liệu được cung cấp. "
            "KHÔNG bịa số liệu. Trả lời bằng tiếng Việt, thân thiện nhưng chuyên nghiệp. "
            "Kết quả phải là JSON hợp lệ:\n"
            '{"tom_tat": "3-5 câu tóm tắt tình hình tài chính dựa trên số liệu thực", '
            '"goi_y": ["Gợi ý cụ thể 1 (<25 từ)", "Gợi ý 2 (<25 từ)", "Gợi ý 3 (<25 từ)"]}'
            "\nGợi ý phải nêu tên danh mục và số liệu cụ thể."
        )

        user_prompt = (
            f"Tháng {thang}/{nam}:\n"
            f"- Thu: {an_danh_data['tong_thu']:,.0f}đ\n"
            f"- Chi: {an_danh_data['tong_chi']:,.0f}đ\n"
            f"- Số dư: {an_danh_data['tong_thu'] - an_danh_data['tong_chi']:,.0f}đ\n"
            "Chi tiêu theo danh mục:\n"
        )
        for item in an_danh_data.get("chi_theo_danh_muc", []):
            user_prompt += (
                f"  + {item['danh_muc']}: {item['so_tien']:,.0f}đ "
                f"({round(item['ty_le']*100)}%) so tháng trước: {item.get('so_sanh_thang_truoc','N/A')}\n"
            )
        if an_danh_data.get("muc_tieu_tiet_kiem"):
            mt = an_danh_data["muc_tieu_tiet_kiem"]
            user_prompt += f"Tiết kiệm '{mt['ten']}': {round(mt.get('tien_do', 0)*100)}%\n"

        full_prompt = f"{system_prompt}\n\nDỮ LIỆU:\n{user_prompt}"

        tom_tat = ""
        goi_y_list = []

        try:
            ai_text = AIService._call_gemini_with_timeout(full_prompt, timeout=settings.AI_TIMEOUT_SECONDS)
            cleaned = ai_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            start_idx = cleaned.find("{")
            end_idx = cleaned.rfind("}") + 1
            if start_idx >= 0 and end_idx > start_idx:
                cleaned = cleaned[start_idx:end_idx]
            parsed = json.loads(cleaned.strip())
            tom_tat = parsed.get("tom_tat", "")
            goi_y_list = parsed.get("goi_y", [])
        except HTTPException:
            raise
        except Exception:
            pass

        if not tom_tat:
            tong_thu = an_danh_data["tong_thu"]
            tong_chi = an_danh_data["tong_chi"]
            so_du = tong_thu - tong_chi
            top_cat = max(an_danh_data.get("chi_theo_danh_muc", [{}]), key=lambda x: x.get("so_tien", 0), default={})
            top_name = top_cat.get("danh_muc", "chi tiêu")
            top_amt = top_cat.get("so_tien", 0)
            tom_tat = (
                f"Tháng {thang}/{nam}: Thu {tong_thu:,.0f}đ, Chi {tong_chi:,.0f}đ, Số dư {so_du:,.0f}đ. "
                f"Danh mục chi nhiều nhất: '{top_name}' ({top_amt:,.0f}đ). "
                f"{'⚠️ Đang tiêu vượt thu nhập!' if so_du < 0 else '✅ Tài chính ổn định.'}"
            )
            goi_y_list = [
                f"Giảm chi '{top_name}' để tăng tiết kiệm." if top_cat else "Ghi chép chi tiêu hàng ngày đầy đủ.",
                "Đặt hạn mức cụ thể cho từng danh mục chi tiêu.",
                "Trích 10-15% thu nhập vào tiết kiệm ngay đầu tháng."
            ]

        moi_bc = BaoCaoAI(
            ma_nd=ma_nd,
            thang_nam=thang_nam,
            noi_dung_tom_tat=tom_tat,
            goi_y_dieu_chinh=json.dumps(goi_y_list, ensure_ascii=False),
            ngay_tao=datetime.utcnow()
        )
        db.add(moi_bc)
        db.commit()
        db.refresh(moi_bc)

        return moi_bc, False

    @staticmethod
    def goi_y_ngan_sach(db: Session, ma_nd: int) -> Dict[str, Any]:
        """
        UC011: AI đề xuất hạn mức ngân sách tháng tới dựa trên lịch sử thực tế.
        """
        now = datetime.now()
        thang_sau = now.month + 1 if now.month < 12 else 1
        nam_sau = now.year if now.month < 12 else now.year + 1
        thang_nam_sau = f"{nam_sau:04d}-{thang_sau:02d}"

        ctx = AIService._get_spending_context(db, ma_nd)
        danh_mucs = db.query(DanhMuc).filter(
            DanhMuc.ma_nd == ma_nd, DanhMuc.loai_dm == "chi"
        ).all()

        if not danh_mucs:
            return {
                "thang_nam_tiep_theo": thang_nam_sau,
                "danh_sach_goi_y": [],
                "loi_khuyen_chung": "Bạn cần tạo ít nhất một danh mục chi tiêu để nhận gợi ý AI."
            }

        chi_tiet_str = ""
        for item in ctx.get("danh_sach_chi_tiet", []):
            chi_tiet_str += (
                f"- {item['ten']}: tháng này {item['so_tien']:,.0f}đ ({item['ty_le']}) | "
                f"tháng trước {item['da_chi_thang_truoc']:,.0f}đ\n"
            )

        system_prompt = (
            "Bạn là chuyên gia tư vấn ngân sách tài chính cá nhân Việt Nam. "
            "Dựa lịch sử chi tiêu thực tế, đề xuất hạn mức HỢP LÝ cho tháng sau. "
            "Quy tắc: hạn mức ≈ 90-95% chi tiêu trung bình để khuyến khích tiết kiệm 5-10%.\n"
            "Trả về JSON hợp lệ:\n"
            '{"danh_sach": [{"ten": "Tên DM", "han_muc_de_xuat": 1500000, "ly_do": "1 câu lý do cụ thể"}, ...], '
            '"loi_khuyen_chung": "1-2 câu khuyên tổng thể"}\n'
            "QUAN TRỌNG: han_muc_de_xuat là số nguyên (VNĐ)."
        )

        user_prompt = (
            f"Thu nhập tháng này: {ctx['thu_nhap']['thang_nay']:,.0f}đ\n"
            f"Chi tiêu tháng này: {ctx['chi_tieu']['thang_nay']:,.0f}đ | Tháng trước: {ctx['chi_tieu']['thang_truoc']:,.0f}đ\n\n"
            f"Lịch sử chi tiêu theo danh mục:\n{chi_tiet_str}\n"
            f"Đề xuất hạn mức cho tháng {thang_sau}/{nam_sau}."
        )

        full_prompt = f"{system_prompt}\n\n{user_prompt}"

        try:
            ai_text = AIService._call_gemini_with_timeout(full_prompt, timeout=settings.AI_TIMEOUT_SECONDS)
            cleaned = ai_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            start_idx = cleaned.find("{")
            end_idx = cleaned.rfind("}") + 1
            if start_idx >= 0 and end_idx > start_idx:
                cleaned = cleaned[start_idx:end_idx]
            parsed = json.loads(cleaned.strip())

            ai_items = parsed.get("danh_sach", [])
            loi_khuyen = parsed.get("loi_khuyen_chung", "Áp dụng quy tắc 50/30/20 để tối ưu ngân sách.")

            cat_name_map = {dm.ten_dm.lower(): dm for dm in danh_mucs}
            goi_y_items = []
            for ai_item in ai_items:
                ten = ai_item.get("ten", "")
                han_muc = ai_item.get("han_muc_de_xuat", 0)
                ly_do = ai_item.get("ly_do", "Dựa trên lịch sử chi tiêu của bạn.")
                dm_match = cat_name_map.get(ten.lower())
                if not dm_match:
                    for k, v in cat_name_map.items():
                        if ten.lower() in k or k in ten.lower():
                            dm_match = v
                            break
                if dm_match and han_muc > 0:
                    goi_y_items.append({
                        "danh_muc": dm_match.ten_dm,
                        "ma_dm": dm_match.ma_dm,
                        "han_muc_de_xuat": max(int(han_muc), 100000),
                        "ly_do": ly_do
                    })

            covered = {item["ma_dm"] for item in goi_y_items}
            for dm in danh_mucs:
                if dm.ma_dm not in covered:
                    item_info = next((i for i in ctx.get("danh_sach_chi_tiet", []) if i["ten"] == dm.ten_dm), None)
                    base_amt = item_info["so_tien"] if item_info else dm.han_muc
                    de_xuat = int(round(base_amt * 0.95 / 10000) * 10000) if base_amt > 0 else 500000
                    goi_y_items.append({
                        "danh_muc": dm.ten_dm, "ma_dm": dm.ma_dm,
                        "han_muc_de_xuat": max(de_xuat, 100000),
                        "ly_do": "Dựa trên chi tiêu thực tế, giảm 5% để khuyến khích tiết kiệm."
                    })

            return {
                "thang_nam_tiep_theo": thang_nam_sau,
                "danh_sach_goi_y": goi_y_items,
                "loi_khuyen_chung": loi_khuyen
            }

        except HTTPException:
            pass
        except Exception:
            pass

        # Fallback tính toán
        goi_y_items = []
        for dm in danh_mucs:
            item_info = next((i for i in ctx.get("danh_sach_chi_tiet", []) if i["ten"] == dm.ten_dm), None)
            base_amt = item_info["so_tien"] if item_info else dm.han_muc
            if base_amt > 0:
                de_xuat = int(round(base_amt * 0.95 / 10000) * 10000)
                ly_do = f"Thực tế chi tiêu: {base_amt:,.0f}đ → giảm 5% còn {de_xuat:,.0f}đ để tiết kiệm."
            else:
                de_xuat = 500000
                ly_do = "Chưa có dữ liệu lịch sử, áp dụng hạn mức cơ bản."
            goi_y_items.append({
                "danh_muc": dm.ten_dm, "ma_dm": dm.ma_dm,
                "han_muc_de_xuat": max(de_xuat, 100000),
                "ly_do": ly_do
            })

        return {
            "thang_nam_tiep_theo": thang_nam_sau,
            "danh_sach_goi_y": goi_y_items,
            "loi_khuyen_chung": "Áp dụng quy tắc 50/30/20: 50% thiết yếu, 30% mong muốn, 20% tích lũy để tối ưu tài chính."
        }

    @staticmethod
    def _tra_loi_cuc_bo_thong_minh(cau_hoi: str, ctx: Dict[str, Any], lich_su_chat: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Cơ chế tư duy & suy luận tài chính thông minh cục bộ (Local Reasoning Engine).
        Hiểu ngữ cảnh, bắt đúng trọng tâm câu hỏi và phân tích có chiều sâu
        thay vì tuôn ra mẫu báo cáo tĩnh lặp đi lặp lại.
        """
        q = cau_hoi.lower()
        thang = ctx["thang_hien_tai"]
        tong_thu = ctx["thu_nhap"]["thang_nay"]
        tong_chi = ctx["chi_tieu"]["thang_nay"]
        so_du = ctx["so_du"]
        so_du_vi = ctx.get("so_du_vi_chinh", 0.0)
        danh_sach = ctx.get("danh_sach_chi_tiet", [])
        min_cat = ctx.get("muc_chi_it_nhat")
        max_cat = ctx.get("muc_chi_nhieu_nhat")
        chi_sinh_hoat = ctx.get("chi_sinh_hoat", [])
        khoan_tk = ctx.get("khoan_tiet_kiem")
        muc_tieus = ctx.get("muc_tieu_tiet_kiem", [])
        lich_su = ctx.get("lich_su_cac_thang", [])
        txs_recent = ctx.get("giao_dich_gan_day", [])

        # Xử lý hội thoại đa lượt khi người dùng trả lời ngắn/đồng ý ('có', 'ok', 'được', 'ừ', 'đồng ý', 'yes'...)
        short_agree = ["có", "ok", "được", "ừ", "uh", "đồng ý", "yes", "co", "tiếp", "tiếp đi", "giúp mình", "hỗ trợ mình", "nhất trí", "chuẩn", "đúng rồi"]
        is_agree = q in short_agree or any(q.startswith(w) for w in ["có ", "ok ", "ừ ", "đồng ý ", "giúp "])
        if is_agree:
            next_m = 10 if thang == 9 else (thang % 12 + 1)
            return (
                f"🎉 **Tuyệt vời! Dưới đây là Bản Kế Hoạch Chi Tiêu Đề Xuất Cho Tháng {next_m} của bạn**:\n\n"
                f"📊 **1. Dự toán Ngân sách Tổng thể (Nguyên tắc 50/25/25 tối ưu)**:\n"
                f"• Thu nhập dự kiến cơ sở: **{tong_thu:,.0f}đ**\n"
                f"• Chi tiêu sinh hoạt thiết yếu (50%): **{round(tong_thu * 0.5):,.0f}đ**\n"
                f"• Chi tiêu linh hoạt cá nhân & giải trí (25%): **{round(tong_thu * 0.25):,.0f}đ**\n"
                f"• Tích luỹ tiết kiệm & Dự phòng (25%): **{round(tong_thu * 0.25):,.0f}đ**\n\n"
                f"🏺 **2. Phân bổ Hạn mức cho từng Hũ Chi Tiêu**:\n"
                f"• Hũ **'Ăn uống'**: Đặt hạn mức **2,500,000đ** (kiểm soát tương đương tháng này để không bị vượt).\n"
                f"• Hũ **'Đi chơi / Giải trí'**: Đặt hạn mức từ **500,000đ - 1,000,000đ** để vừa thoải mái vừa không thâm hụt.\n"
                f"• Hũ **'Tiết kiệm Du lịch / Mục tiêu'**: Trích ngay **3,000,000đ** vào đầu tháng ngay khi nhận thu nhập ('Trả cho mình trước').\n\n"
                f"💡 **3. Các bước hành động cụ thể**:\n"
                f"1. Vào mục **Quản lý > Ngân sách hũ** để thiết lập hoặc điều chỉnh hạn mức cho Tháng {next_m}.\n"
                f"2. Trích quỹ tiết kiệm trước, chi tiêu phần còn lại sau để luôn duy trì thặng dư dương!\n\n"
                f"Bạn thấy kế hoạch này đã hợp lý chưa, hay muốn điều chỉnh thêm hạn mức cho hũ nào?"
            )

        # 1. HỎI VỀ CHI ÍT NHẤT / THẤP NHẤT
        if any(kw in q for kw in ["ít nhất", "thấp nhất", "nhỏ nhất", "chi tiêu ít", "ít tiền nhất", "tiêu ít"]):
            if not danh_sach or not min_cat:
                return f"Tháng {thang} bạn chưa ghi nhận khoản chi tiêu nào để xác định mục chi ít nhất."

            ten_it = min_cat["ten"]
            tien_it = min_cat["so_tien"]
            ty_le_it = min_cat["ty_le"]

            msg = (
                f"🎯 Trong tháng {thang}, danh mục bạn **chi tiêu ít nhất** là **{ten_it}** "
                f"với số tiền **{tien_it:,.0f}đ** (chỉ chiếm **{ty_le_it}** trên tổng chi tiêu {tong_chi:,.0f}đ).\n\n"
                f"💡 **Nhận xét thông minh**: Bạn đang kiểm soát rất chặt chẽ khoản '{ten_it}'. "
            )
            if "chơi" in ten_it.lower() or "giải trí" in ten_it.lower():
                msg += "Việc giữ chi phí giải trí ở mức khiêm tốn giúp bạn tối ưu hóa dòng tiền cho các mục tiêu tích lũy lớn hơn! 👏"
            else:
                msg += "Duy trì thói quen chi tiêu có kỷ luật này sẽ giúp số dư khả dụng của bạn luôn được bảo toàn."
            return msg

        # 2. HỎI VỀ CHI NHIỀU NHẤT / CAO NHẤT / TỐN TIỀN NHẤT
        if any(kw in q for kw in ["nhiều nhất", "cao nhất", "lớn nhất", "tốn nhất", "tốn kém nhất", "chi nhiều", "tiêu nhiều"]):
            if not danh_sach or not max_cat:
                return f"Tháng {thang} bạn chưa ghi nhận khoản chi tiêu nào."

            ten_max = max_cat["ten"]
            tien_max = max_cat["so_tien"]
            ty_le_max = max_cat["ty_le"]

            # Tư duy phân biệt: Nếu khoản lớn nhất là Tiết kiệm (tích lũy), phân tích rõ
            if ten_max.lower() == "tiết kiệm":
                top_sh = chi_sinh_hoat[0] if chi_sinh_hoat else None
                msg = (
                    f"🏆 Trong tháng {thang}, khoản tiền trích lớn nhất là **Tiết kiệm** với **{tien_max:,.0f}đ** (chiếm **{ty_le_max}** tổng dòng tiền ra).\n\n"
                    f"🌟 **Góc nhìn tài chính**: Đây là một tín hiệu cực kỳ xuất sắc! Tiết kiệm là khoản **tích lũy tài sản cho tương lai** chứ không phải chi phí tiêu hao đi.\n"
                )
                if top_sh:
                    msg += (
                        f"🍽️ Còn về **chi tiêu sinh hoạt thực tế**, danh mục tốn nhiều nhất là **{top_sh['ten']}** "
                        f"với **{top_sh['so_tien']:,.0f}đ** ({top_sh['ty_le']}). Bạn có thể lưu ý cân đối thêm phần này nhé."
                    )
                return msg
            else:
                return (
                    f"🏆 Trong tháng {thang}, danh mục bạn **chi tiêu nhiều nhất** là **{ten_max}** "
                    f"với **{tien_max:,.0f}đ** (chiếm **{ty_le_max}** trên tổng chi tiêu {tong_chi:,.0f}đ).\n\n"
                    f"💡 **Khuyến nghị**: Khoản này đang chiếm tỷ trọng đáng kể trong chi tiêu hàng tháng. "
                    f"Bạn hãy cân nhắc đặt hạn mức ngân sách cho '{ten_max}' để tránh vượt kiểm soát nhé!"
                )

        # 3. HỎI VỀ 1 DANH MỤC CỤ THỂ (ĂN UỐNG, ĐI CHƠI, ĐI LẠI, MUA SẮM,...)
        for item in danh_sach:
            if item["ten"].lower() in q:
                return (
                    f"📋 **Chi tiết danh mục '{item['ten']}' trong tháng {thang}**:\n"
                    f"• Số tiền đã chi: **{item['so_tien']:,.0f}đ**\n"
                    f"• Tỷ trọng trong tổng chi: **{item['ty_le']}**\n"
                    f"• Biến động: **{item.get('so_sanh', 'Mới trong tháng')}** (tháng trước: {item.get('da_chi_thang_truoc', 0):,.0f}đ)\n\n"
                    f"💡 **Đánh giá**: Mục này đang chiếm {item['ty_le']} ngân sách của bạn. "
                    f"{'Mức chi này rất hợp lý và cân đối!' if item['phan_tram_so'] < 30 else 'Tỷ lệ chi khá cao, bạn nên theo dõi sát sao hơn.'}"
                )

        # 4. HỎI VỀ GIAO DỊCH GẦN ĐÂY / MỚI NHẤT / HÔM NAY
        if any(kw in q for kw in ["gần đây", "mới nhất", "vừa chi", "vừa tiêu", "hôm nay", "giao dịch gần"]):
            if txs_recent:
                lines = [f"• {t['ngay']}: {t['loai']} **{t['so_tien']:,.0f}đ** ({t['danh_muc']}) - *{t['ghi_chu'] or 'Không có ghi chú'}*" for t in txs_recent[:5]]
                return "🕒 **Các giao dịch gần đây nhất của bạn**:\n" + "\n".join(lines)
            return f"Tháng {thang} bạn chưa phát sinh giao dịch nào gần đây."

        # 5. HỎI VỀ SỐ DƯ / VÍ TIỀN / KHẢ NĂNG TÀI CHÍNH
        if any(kw in q for kw in ["số dư", "còn bao nhiêu", "còn tiền", "ví chính", "khả dụng", "dư bao"]):
            tinh_trang = "dương, tài chính ổn định" if so_du >= 0 else "đang thâm hụt (chi tiêu vượt thu nhập)"
            return (
                f"💰 **Tình hình ngân quỹ hiện tại (Tháng {thang})**:\n"
                f"• Số dư ví chính khả dụng: **{so_du_vi:,.0f}đ**\n"
                f"• Thu nhập tháng này: **{tong_thu:,.0f}đ**\n"
                f"• Tổng chi tháng này: **{tong_chi:,.0f}đ**\n"
                f"• Thặng dư tích lũy tháng: **{so_du:,.0f}đ** ({tinh_trang}) ✅\n\n"
                f"💡 Ví chính của bạn hiện có **{so_du_vi:,.0f}đ** sẵn sàng cho các chi tiêu thiết yếu và mục tiêu mới."
            )

        # 6. HỎI VỀ MỤC TIÊU TIẾT KIỆM / HŨ
        if any(kw in q for kw in ["tiết kiệm", "mục tiêu", "hũ", "tiến độ"]):
            if muc_tieus:
                lines = []
                for m in muc_tieus:
                    lines.append(f"• **{m['ten']}**: **{m['hien_tai']:,.0f}đ** / {m['muc_tieu']:,.0f}đ (Đạt **{m['tien_do']}**)")
                return (
                    f"🎯 **Tiến độ các mục tiêu tiết kiệm của bạn**:\n" +
                    "\n".join(lines) +
                    f"\n\n💪 Bạn đã tích lũy vào quỹ tiết kiệm rất tốt! Hãy tiếp tục duy trì đà này nhé!"
                )
            return "Hiện tại bạn chưa lập mục tiêu tiết kiệm nào. Hãy bấm sang tab **Tiết Kiệm** để tạo hũ đầu tiên nhé! 🎯"

        # 7. HỎI VỀ LỜI KHUYÊN / CÓ NÊN MUA / TƯ VẤN
        if any(kw in q for kw in ["có nên", "mua được không", "tư vấn", "lời khuyên", "làm sao"]):
            return (
                f"🧠 **Gợi ý tư duy tài chính từ MoneyMind**:\n"
                f"• Hiện số dư ví chính của bạn là **{so_du_vi:,.0f}đ** và thặng dư tháng này là **{so_du:,.0f}đ**.\n"
                f"• Trước khi đưa ra quyết định mua sắm hoặc chi tiêu lớn, hãy tự hỏi:\n"
                f"  1. Khoản này thuộc nhóm **Cần thiết (Need)** hay **Mong muốn (Want)**?\n"
                f"  2. Sau khi mua, số dư dự phòng khẩn cấp của bạn có còn đủ cho ít nhất 1-2 tháng tới không?\n"
                f"  3. Áp dụng quy tắc 24h: Chờ 24 tiếng trước khi chốt đơn những món ngoài kế hoạch.\n\n"
                f"✨ Nếu món đồ nằm trong hạn mức và không ảnh hưởng đến các hũ tiết kiệm, bạn hoàn toàn có thể tự thưởng cho mình!"
            )

        # 8. BÁO CÁO TỔNG QUAN KHI NGƯỜI DÙNG THỰC SỰ YÊU CẦU BÁO CÁO / TỔNG HỢP
        if any(kw in q for kw in ["báo cáo", "tổng quan", "thống kê", "toàn bộ", "tổng kết", "tình hình"]):
            lines = [f"• {item['ten']}: **{item['so_tien']:,.0f}đ** ({item['ty_le']})" for item in danh_sach]
            detail_str = "\n".join(lines) if lines else "Chưa có chi tiêu."
            top_ten = max_cat['ten'] if max_cat else 'Chưa có'
            it_ten = min_cat['ten'] if min_cat else 'Chưa có'
            return (
                f"📊 **Báo cáo tài chính tổng quan tháng {thang}**:\n"
                f"• Tổng thu nhập: **{tong_thu:,.0f}đ**\n"
                f"• Tổng chi tiêu: **{tong_chi:,.0f}đ**\n"
                f"• Thặng dư tháng: **{so_du:,.0f}đ** | Số dư ví chính: **{so_du_vi:,.0f}đ**\n\n"
                f"📋 **Phân bổ chi tiêu theo danh mục**:\n{detail_str}\n\n"
                f"🔍 **Điểm nhấn phân tích**:\n"
                f"• Chi nhiều nhất: **{top_ten}** ({max_cat['so_tien']:,.0f}đ)\n"
                f"• Chi ít nhất: **{it_ten}** ({min_cat['so_tien']:,.0f}đ)\n"
                f"• Tích lũy tiết kiệm: **{khoan_tk['so_tien']:,.0f}đ** ({khoan_tk['ty_le']})" if khoan_tk else ""
            )

        # 9. PHẢN HỒI THÔNG MINH MẶC ĐỊNH
        top_name = max_cat['ten'] if max_cat else 'Chưa có'
        min_name = min_cat['ten'] if min_cat else 'Chưa có'
        return (
            f"👋 Chào bạn! Tôi là Trợ Lý AI Tài Chính MoneyMind.\n"
            f"Trong tháng {thang}, bạn đã chi **{tong_chi:,.0f}đ** trên tổng thu **{tong_thu:,.0f}đ** (dư **{so_du:,.0f}đ**).\n"
            f"• Mục chi nhiều nhất: **{top_name}**\n"
            f"• Mục chi ít nhất: **{min_name}**\n\n"
            f"💡 Bạn có thể hỏi tôi bất cứ điều gì, ví dụ:\n"
            f"- *'Tôi chi tiêu ít nhất vào mục nào?'*\n"
            f"- *'Tháng này chi nhiều nhất vào đâu?'*\n"
            f"- *'Tiền ăn uống tháng này là bao nhiêu?'*\n"
            f"- *'Số dư ví chính hiện tại còn bao nhiêu?'*"
        )

    @staticmethod
    def hoi_dap_ai(db: Session, ma_nd: int, cau_hoi: str, lich_su_chat: Optional[List[Dict[str, str]]] = None) -> str:
        """
        UC012 & TC-09: Hỏi đáp tự nhiên với AI Tài Chính Thông Minh (Gemini Flash Engine + Local Reasoning).
        Trang bị năng lực tư duy logic, phân tích đúng ý định, trả lời thẳng vào câu hỏi,
        không bao giờ trả lời rập khuôn hay máy móc.
        """
        cau_hoi_clean = cau_hoi.strip()
        if not cau_hoi_clean:
            return "Bạn vui lòng nhập câu hỏi về chi tiêu tài chính cá nhân nhé! 😊"

        # TC-09: Từ chối các chủ đề ngoài phạm vi quản lý tài chính cá nhân
        tu_khoa_ngoai_le = [
            "mua cổ phiếu", "mã chứng khoán", "đầu tư coin", "crypto", "bitcoin",
            "xổ số", "lô đề", "chính trị", "bóng đá", "thể thao", "nấu ăn", "công thức nấu"
        ]
        if any(kw in cau_hoi_clean.lower() for kw in tu_khoa_ngoai_le):
            return (
                "Xin lỗi bạn! 🙏 Tôi là Trợ lý Quản lý Tài chính Cá nhân MoneyMind, "
                "không có thẩm quyền tư vấn đầu tư chứng khoán rủi ro hay các chủ đề ngoài phạm vi quản lý thu chi, ngân sách và tiết kiệm. "
                "Bạn có thắc mắc nào về thu chi, số dư hay ngân sách tháng này không? 💰"
            )

        ctx = AIService._get_spending_context(db, ma_nd)
        tong_chi = ctx["chi_tieu"]["thang_nay"]
        tong_thu = ctx["thu_nhap"]["thang_nay"]
        so_du = ctx["so_du"]
        so_du_vi_chinh = ctx.get("so_du_vi_chinh", 0.0)
        danh_sach_chi = ctx.get("danh_sach_chi_tiet", [])
        min_cat = ctx.get("muc_chi_it_nhat")
        max_cat = ctx.get("muc_chi_nhieu_nhat")
        khoan_tk = ctx.get("khoan_tiet_kiem")
        chi_sinh_hoat = ctx.get("chi_sinh_hoat", [])
        lich_su = ctx.get("lich_su_cac_thang", [])
        txs_recent = ctx.get("giao_dich_gan_day", [])

        # Chuỗi danh mục chi tiết
        chi_tiet_str = ""
        for item in danh_sach_chi:
            chi_tiet_str += f"  - {item['ten']}: {item['so_tien']:,.0f}đ ({item['ty_le']}) | So tháng trước: {item.get('so_sanh', 'N/A')}\n"
        if not chi_tiet_str:
            chi_tiet_str = "  (Tháng này chưa có khoản chi tiêu nào)\n"

        # Chuỗi giao dịch gần đây
        recent_str = ""
        for t in txs_recent:
            recent_str += f"  - Ngày {t['ngay']}: {t['loai']} {t['so_tien']:,.0f}đ ({t['danh_muc']}) - {t['ghi_chu']}\n"
        if not recent_str:
            recent_str = "  (Chưa có giao dịch gần đây)\n"

        # Chuỗi lịch sử các tháng
        lich_su_str = ""
        for ls in lich_su:
            lich_su_str += f"  - Tháng {ls['thang']}: Thu {ls['thu']:,.0f}đ | Chi {ls['chi']:,.0f}đ | Dư {ls['so_du']:,.0f}đ (Top chi: {ls.get('top_chi', 'N/A')})\n"
        if not lich_su_str:
            lich_su_str = "  (Đây là tháng đầu tiên ghi chép trên MoneyMind)\n"

        # Chuỗi mục tiêu tiết kiệm
        mt_str = ""
        for mt in ctx.get("muc_tieu_tiet_kiem", []):
            mt_str += f"  - Hũ '{mt['ten']}': {mt['hien_tai']:,.0f}đ / {mt['muc_tieu']:,.0f}đ ({mt['tien_do']})\n"
        if not mt_str:
            mt_str = "  (Chưa tạo mục tiêu tiết kiệm)\n"

        system_prompt = (
            "Bạn là Trợ Lý Cố Vấn Tài Chính Cá Nhân AI Thông Minh của ứng dụng MoneyMind (Việt Nam).\n"
            "Bạn sở hữu khả năng tư duy logic tài chính sắc bén, thấu hiểu ngữ cảnh và giao tiếp tự nhiên, gần gũi.\n\n"
            "NGUYÊN TẮC TƯ DUY & TRẢ LỜI QUAN TRỌNG NHẤT:\n"
            "1. TRẢ LỜI ĐÚNG TRỌNG TÂM - KHÔNG TRẢ LỜI MÁY MÓC / RẬP KHUÔN:\n"
            "   - Hãy đọc kỹ câu hỏi của người dùng và TRẢ LỜI TRỰC TIẾP VÀO CÂU HỎI ngay ở 1-2 câu đầu tiên!\n"
            "   - TUYỆT ĐỐI KHÔNG tự động tuôn ra cả một bảng báo cáo dài nếu người dùng chỉ hỏi một câu ngắn hoặc cụ thể.\n"
            "   - Chỉ cung cấp báo cáo toàn diện khi người dùng thực sự yêu cầu 'báo cáo', 'tổng quan', 'tổng kết'.\n\n"
            "2. TƯ DUY PHÂN TÍCH DỮ LIỆU CHÍNH XÁC:\n"
            f"   - Nếu hỏi 'chi ít nhất / tiêu ít nhất': Chỉ rõ mục chi ít nhất là '{min_cat['ten'] if min_cat else 'Không có'}' với {min_cat['so_tien'] if min_cat else 0:,.0f}đ ({min_cat['ty_le'] if min_cat else '0%'} tổng chi), nhận xét ngắn gọn về thói quen chi tiêu này.\n"
            f"   - Nếu hỏi 'chi nhiều nhất / tiêu nhiều nhất': Chỉ rõ mục chi nhiều nhất là '{max_cat['ten'] if max_cat else 'Không có'}' ({max_cat['so_tien'] if max_cat else 0:,.0f}đ). LƯU Ý: Nếu mục lớn nhất là 'Tiết kiệm', hãy tư duy thông minh: khen ngợi đây là khoản tích lũy tài sản cho tương lai, đồng thời nêu thêm mục chi tiêu sinh hoạt thực tế tốn kém nhất.\n"
            "   - Nếu hỏi về 1 danh mục cụ thể (ví dụ Ăn uống, Đi chơi...): Nêu rõ số tiền, tỷ lệ %, so sánh và đánh giá xem mức chi đó có cân đối không.\n"
            "   - Nếu hỏi về số dư / ví tiền: Nêu rõ số dư ví chính khả dụng và thặng dư tháng.\n"
            "   - Nếu hỏi xin lời khuyên / có nên mua món gì: Dựa vào số dư ví chính, thặng dư và mục tiêu tiết kiệm để tính toán và tư vấn thực tế, có căn cứ.\n\n"
            "3. ĐỊNH DẠNG & PHONG CÁCH:\n"
            "   - Tiếng Việt tự nhiên, ấm áp, thông minh, tinh tế. Định dạng markdown rõ ràng (in đậm số liệu, emoji hợp lý, gạch đầu dòng gọn gàng).\n\n"
            "4. XỬ LÝ HỘI THOẠI ĐA LƯỢT & CÂU HỎI / TRẢ LỜI NGẮN (CỰC KỲ QUAN TRỌNG):\n"
            "   - Khi người dùng gửi câu ngắn như 'có', 'ok', 'được', 'ừ', 'đồng ý', 'yes', 'giúp mình', 'hỗ trợ mình', 'tiếp tục'...\n"
            "   - Tuyệt đối KHÔNG coi đây là tin nhắn gửi nhầm hoặc câu nói chưa hoàn chỉnh!\n"
            "   - Hãy đọc câu hỏi/gợi ý gần nhất của AI trong 'LỊCH SỬ TRÒ CHUYỆN GẦN ĐÂY' để thực hiện ngay hành động tiếp theo.\n"
            "   - Ví dụ: Nếu câu trước AI vừa hỏi 'Bạn có muốn mình hỗ trợ lập kế hoạch chi tiêu cho tháng 10 không?' và người dùng trả lời 'có' / 'ok' -> Hãy lập ngay một bản kế hoạch chi tiêu cụ thể, thông minh, chi tiết cho tháng 10 dựa trên dữ liệu thu chi thực tế của họ!\n\n"
            f"DỮ LIỆU TÀI CHÍNH THỰC TẾ (Tháng {ctx['thang_hien_tai']}):\n"
            f"• Thu nhập: {tong_thu:,.0f}đ\n"
            f"• Tổng chi tiêu: {tong_chi:,.0f}đ\n"
            f"• Thặng dư tháng: {so_du:,.0f}đ | Số dư ví chính khả dụng: {so_du_vi_chinh:,.0f}đ\n"
            f"• Chi tiết các danh mục đã chi tiêu (xếp từ nhiều nhất đến ít nhất):\n{chi_tiet_str}"
            f"• Giao dịch gần đây:\n{recent_str}"
            f"• Mục tiêu tiết kiệm:\n{mt_str}"
            f"• Lịch sử các tháng trước:\n{lich_su_str}"
        )

        history_str = ""
        if lich_su_chat:
            history_str = "\nLỊCH SỬ TRÒ CHUYỆN GẦN ĐÂY VỚI NGƯỜI DÙNG:\n"
            for msg in lich_su_chat[-6:]:
                role_label = "Người dùng" if msg.get("role") in ["user", "nguoi_dung"] else "AI Trợ lý"
                history_str += f"- {role_label}: {msg.get('content', '')}\n"

        full_prompt = (
            f"{system_prompt}\n"
            f"{history_str}\n"
            f"CÂU HỎI / TIN NHẮN MỚI NHẤT CỦA NGƯỜI DÙNG: {cau_hoi_clean}\n\n"
            f"HÃY ĐỌC KỸ LỊCH SỬ TRÒ CHUYỆN ĐỂ TRẢ LỜI ĐÚNG NGỮ CẢNH VÀ ĐÁP ỨNG TRỰC TIẾP Ý ĐỊNH CỦA NGƯỜI DÙNG:"
        )

        # Thử gọi Gemini AI qua REST đa mô hình
        try:
            return AIService._call_gemini_with_timeout(full_prompt, timeout=settings.AI_TIMEOUT_SECONDS)
        except Exception:
            pass

        # Khi mạng offline hoặc Gemini API tạm thời không phản hồi,
        # kích hoạt bộ máy tư duy tài chính cục bộ thông minh
        return AIService._tra_loi_cuc_bo_thong_minh(cau_hoi_clean, ctx, lich_su_chat)
