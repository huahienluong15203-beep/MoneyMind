import re
import json
import ssl
import urllib.request
import urllib.error
import concurrent.futures
from datetime import datetime, timedelta, date
from typing import Dict, Any, Tuple, List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.bao_cao_ai import BaoCaoAI
from app.models.danh_muc import DanhMuc
from app.models.giao_dich import GiaoDich
from app.models.muc_tieu_tiet_kiem import MucTieuTietKiem
from app.models.ngan_sach import NganSach
from app.models.thong_bao import ThongBao
from app.services.privacy_service import PrivacyService
from app.services.ngan_sach_service import NganSachService

# Danh sách các mô hình Gemini THẾ HỆ MỚI NHẤT của Google
# Tự động ưu tiên Gemini 3.8 Flash -> Gemini 3.7 Flash -> Gemini 3.6 -> Gemini 3.5 -> Flash Latest
AVAILABLE_GEMINI_MODELS = [
    "gemini-3.8-flash",        # Thế hệ mới nhất hiện tại của Google
    "gemini-3.7-flash",        # Thế hệ 3.7 Flash
    "gemini-3.6-flash",        # Thế hệ 3.6 Flash
    "gemini-3.5-flash",        # Thế hệ 3.5 Flash
    "gemini-flash-latest",     # Alias luôn trỏ tới bản mới nhất
    "gemini-3.1-flash-lite",   # Bản nhẹ dự phòng
    "gemini-2.0-flash",        # Bản 2.0 dự phòng
    "gemini-2.5-flash"         # Bản 2.5 dự phòng
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

        per_model_timeout = max(8.0, min(20.0, timeout))
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
                f"2. Trích quỹ tiết kiệm trước, chi tiêu phần còn lại sau để luôn có tiền tích lũy dư dả mỗi tháng!\n\n"
                f"Bạn thấy kế hoạch này đã hợp lý chưa, hay muốn điều chỉnh thêm hạn mức cho hũ nào?"
            )

        # 0. HỎI VỀ LIỆT KÊ CHI TIẾT DANH MỤC / DANH SÁCH CHI TIÊU
        if any(kw in q for kw in ["liệt kê", "danh sách danh mục", "chi tiết chi tiêu", "chi tiết danh mục", "các danh mục", "tất cả danh mục", "chi những gì", "tiêu những gì"]):
            if not danh_sach:
                return f"Tháng {thang} bạn chưa ghi nhận khoản chi tiêu nào để liệt kê danh mục."
            lines = []
            for item in danh_sach:
                lines.append(f"• **{item['ten']}**: **{item['so_tien']:,.0f}đ** (chiếm {item['ty_le']} tổng chi)")
            list_text = "\n".join(lines)
            max_name = max_cat['ten'] if max_cat else 'N/A'
            max_val = max_cat['so_tien'] if max_cat else 0
            return (
                f"📋 **Chi tiết chi tiêu theo từng danh mục trong tháng {thang}** (Tổng chi: **{tong_chi:,.0f}đ**):\n\n"
                f"{list_text}\n\n"
                f"💡 **Tóm tắt**: Mục chiếm nhiều nhất là **{max_name}** ({max_val:,.0f}đ). "
                f"Bạn có muốn xem chi tiết các giao dịch của danh mục nào không?"
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
                f"• Tiền còn dư tháng này (Thu trừ Chi): **{so_du:,.0f}đ** ({tinh_trang}) ✅\n\n"
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
                f"• Hiện số dư ví chính của bạn là **{so_du_vi:,.0f}đ** và số tiền còn dư trong tháng này là **{so_du:,.0f}đ**.\n"
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
                f"• Tiền còn dư tháng này: **{so_du:,.0f}đ** | Số dư ví chính: **{so_du_vi:,.0f}đ**\n\n"
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
    def _match_keyword(kw: str, text: str) -> bool:
        pattern = r'(?:^|[^\w])' + re.escape(kw) + r'(?:[^\w]|$)'
        return bool(re.search(pattern, text, flags=re.IGNORECASE))

    @staticmethod
    def _parse_vietnamese_amount(t: str) -> float:
        # Triệu / củ / tr kết hợp lẻ: 2tr5, 2 triệu 5, 2 củ 3, 1tr200
        m = re.search(r'(\d+)\s*(?:tr|triệu|củ)\s*(\d+)\s*(?:k|nghìn|ngàn)?', t)
        if m:
            trieu = float(m.group(1))
            phan_le = float(m.group(2))
            if phan_le < 10:
                return trieu * 1_000_000 + phan_le * 100_000
            elif phan_le < 100:
                return trieu * 1_000_000 + phan_le * 10_000
            else:
                return trieu * 1_000_000 + phan_le * 1_000
        
        m = re.search(r'(\d+)\s*củ\s*rưỡi', t)
        if m:
            return float(m.group(1)) * 1_000_000 + 500_000

        m = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:triệu|trieu|tr|m|củ)\b', t)
        if m:
            return float(m.group(1).replace(',', '.')) * 1_000_000

        m = re.search(r'(\d+)\s*lít\s*rưỡi', t)
        if m:
            return float(m.group(1)) * 100_000 + 50_000

        m = re.search(r'(\d+)\s*lít\b', t)
        if m:
            return float(m.group(1)) * 100_000

        m = re.search(r'(\d+)\s*chục\b', t)
        if m:
            return float(m.group(1)) * 10_000

        m = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:nghìn|nghin|ngàn|ngan|k|ng)\b', t)
        if m:
            return float(m.group(1).replace(',', '.')) * 1_000

        m = re.search(r'\b(\d{1,3}(?:[.,]\d{3})+)\s*(?:đ|vnd|đồng|dong)?\b', t)
        if m:
            return float(re.sub(r'[.,]', '', m.group(1)))

        m = re.search(r'\b(\d{4,})\s*(?:đ|vnd|đồng|dong)?\b', t)
        if m:
            return float(m.group(1))

        m = re.search(r'\b(\d+)\s*(?:đ|vnd|đồng|dong)\b', t)
        if m:
            return float(m.group(1))

        return 0.0

    @staticmethod
    def _lam_sach_mo_ta_giao_dich(raw: str, default_name: str = "Chi tiêu") -> str:
        """
        Làm sạch mô tả giao dịch:
        - Loại bỏ từ nối, trạng từ thừa: 'vừa', 'mới', 'vừa đi', 'mới đi', 'tôi', 'mình'...
        - Loại bỏ số tiền trong mô tả ('hết 35k', '35000', '20k'...) vì đã có cột số tiền riêng.
        - Viết hoa chữ cái đầu và giữ lại hành động cốt lõi (ví dụ: 'Ăn bánh cuốn', 'Mua cafe').
        """
        s = raw.strip()

        # 1. Dọn dẹp tiền tố đính chính, nhầm, lộn, cảm thán hội thoại và từ nối
        for _ in range(5):
            s = re.sub(r'^(?:à|ơ|ủa|ơ\s*kìa|ấy)\s+[,:\-]?\s*', '', s, flags=re.IGNORECASE)
            s = re.sub(r'^(?:lộn(?:\s*rồi|\s*nè|\s*nhé|\s*quá)?|nhầm(?:\s*rồi|\s*nè|\s*nhé|\s*quá)?|quên(?:\s*mất)?)\s*[,:\-]?\s*', '', s, flags=re.IGNORECASE)
            s = re.sub(r'^(?:nói\s*lộn|nói\s*nhầm|ghi\s*lộn|ghi\s*nhầm|đính\s*chính(?:\s*lại)?|sửa\s*lại)(?:\s+rồi)?\s*[,:\-]?\s*', '', s, flags=re.IGNORECASE)
            s = re.sub(r'^(?:thực\s*ra|thật\s*ra|đúng\s*ra)(?:\s+là)?\s*[,:\-]?\s*', '', s, flags=re.IGNORECASE)
            s = re.sub(r'^(?:ý\s*là|ý\s*tôi\s*là|ý\s*mình\s*là|đúng\s*hơn\s*là)\s*[,:\-]?\s*', '', s, flags=re.IGNORECASE)
            s = re.sub(r'^(?:hãy\s+)?(?:báo(?:\s*cáo)?|ghi\s*nhận(?:\s*giúp)?|thêm\s*(?:giao\s*dịch)?|ghi\s*sổ|lưu\s*(?:giao\s*dịch)?|tạo\s*(?:giao\s*dịch)?|nhập\s*(?:giúp)?|lưu|thêm|ghi)\s+', '', s, flags=re.IGNORECASE)
            s = re.sub(r'^(?:tôi|mình|em|anh|chị|bạn|chúng\s*tôi)\s+', '', s, flags=re.IGNORECASE)
            s = re.sub(r'^(?:hôm\s*nay|hôm\s*qua|sáng\s*nay|trưa\s*nay|chiều\s*nay|tối\s*nay|tối\s*qua)\s+[,:\-]?\s*', '', s, flags=re.IGNORECASE)
            s = re.sub(r'^(?:vừa\s*mới|vừa\s*đi|mới\s*đi|vừa|mới|có|đã|lại)\s+', '', s, flags=re.IGNORECASE)
            s = re.sub(r'^đi\s+(ăn|uống|mua|nhậu|chơi)\b', r'\1', s, flags=re.IGNORECASE)

        # 2. Nếu cấu trúc 'chi 200k đi xem phim', 'nộp 500k tiền điện' -> bỏ 'chi 200k '
        s = re.sub(r'^(?:chi|tiêu|trả|nộp|chuyển)\s+[\d.,]+\s*(?:tr|triệu|củ|k|nghìn|ngàn|đ|vnd|đồng|dong|lít)?\s*(?:cho|để|vào)?\s*', '', s, flags=re.IGNORECASE)

        # 3. Nếu số tiền ở đầu câu (vd: 50k xăng, 35k tiền bánh cuốn)
        s = re.sub(r'^[\d.,]+\s*(?:tr|triệu|củ|k|nghìn|ngàn|đ|vnd|đồng|dong|lít)\s*(?:tiền)?\s*', '', s, flags=re.IGNORECASE)

        # 4. Loại bỏ phần số tiền và từ nối 'hết', 'mất', 'tốn' ở cuối câu
        s = re.sub(r'\s*(?:hết|mất|tốn|chi\s*hết|tiêu\s*hết|giá)\s+[\d.,]+.*$', '', s, flags=re.IGNORECASE)
        s = re.sub(r'\s*(?:hết|mất|tốn|chi\s*hết|tiêu\s*hết|giá)\s+(?:một|hai|ba|bốn|năm|sáu|bảy|tám|chín|mười|\d+).*$', '', s, flags=re.IGNORECASE)
        s = re.sub(r'\s*[\d.,]+\s*(?:tr|triệu|củ|k|nghìn|ngàn|đ|vnd|đồng|dong|lít|chục)(?:\s*\d+)?\b.*$', '', s, flags=re.IGNORECASE)
        s = re.sub(r'\s*[\d.,]+\s*(?:đ|vnd|đồng|dong)?$', '', s, flags=re.IGNORECASE)
        s = re.sub(r'\s*\b\d+\s*$', '', s)

        # 5. Dọn dẹp dấu câu thừa ở cuối hoặc đầu
        s = re.sub(r'^[:,\-\s]+', '', s)
        s = re.sub(r'[:,\-\s]+$', '', s)

        s = s.strip()
        if not s or len(s) < 2:
            return default_name
        return s[0].upper() + s[1:]

    @staticmethod
    def _xu_ly_xoa_hu_tiet_kiem(db: Session, ma_nd: int, t: str) -> Optional[str]:
        goals = db.query(MucTieuTietKiem).filter(MucTieuTietKiem.ma_nd == ma_nd).all()
        if not goals:
            return "Hiện tại bạn chưa có hũ tiết kiệm nào để xóa."

        matched_goal = None
        for g in goals:
            g_name = g.ten_muc_tieu.lower()
            if g_name in t or any(w in t for w in g_name.split() if len(w) > 2):
                matched_goal = g
                break
        if not matched_goal and len(goals) == 1:
            matched_goal = goals[0]

        if not matched_goal:
            ds = ", ".join([f"\"{g.ten_muc_tieu}\"" for g in goals])
            return f"Bạn muốn xóa hũ tiết kiệm nào? Hiện tại bạn đang có các hũ: {ds}. Hãy nói rõ tên hũ nhé!"

        refund_amt = float(matched_goal.so_tien_hien_tai or 0.0)
        goal_title = matched_goal.ten_muc_tieu

        # Đổi ghi chú các giao dịch tích lũy thành (đã xoá) để hoàn lại số dư khả dụng cho ví chính
        goal_txs = db.query(GiaoDich).filter(
            GiaoDich.ma_nd == ma_nd,
            GiaoDich.ghi_chu.like(f"%{goal_title}%")
        ).all()
        for gtx in goal_txs:
            gtx.ghi_chu = f"Mục tiêu: {goal_title} (đã xoá)"

        if refund_amt > 0:
            tb = ThongBao(
                ma_nd=ma_nd,
                tieu_de="💰 Hoàn Tiền Hũ Tiết Kiệm Về Ví Chính",
                noi_dung=f"Đã hoàn trả {refund_amt:,.0f} đ từ hũ '{goal_title}' về ví chính để bạn sử dụng cho các mục tiêu khác.",
                da_xem=False,
                ngay_tao=datetime.now()
            )
            db.add(tb)

        db.delete(matched_goal)
        db.commit()
        so_du_vi = NganSachService.tinh_so_du_vi_chinh(db, ma_nd)

        return (
            f"Đã xóa hũ tiết kiệm **\"{goal_title}\"** thành công! 🗑️\n\n"
            f"• **Số tiền hoàn trả về ví chính:** **+{refund_amt:,.0f}đ**\n"
            f"• 💳 **Số dư ví chính khả dụng:** **{so_du_vi:,.0f}đ**\n\n"
            f"Khoản tiền tích lũy từ hũ đã được hoàn trả nguyên vẹn về ví chính để bạn sử dụng."
        )

    @staticmethod
    def _xu_ly_rut_tien_hu(db: Session, ma_nd: int, t: str, amount: float) -> Optional[str]:
        goals = db.query(MucTieuTietKiem).filter(MucTieuTietKiem.ma_nd == ma_nd).all()
        if not goals:
            return "Hiện tại bạn chưa có hũ tiết kiệm nào để rút tiền."

        matched_goal = None
        for g in goals:
            g_name = g.ten_muc_tieu.lower()
            if g_name in t or any(w in t for w in g_name.split() if len(w) > 2):
                matched_goal = g
                break
        if not matched_goal and len(goals) == 1:
            matched_goal = goals[0]

        if not matched_goal:
            ds = ", ".join([f"\"{g.ten_muc_tieu}\"" for g in goals])
            return f"Bạn muốn rút tiền từ hũ nào? Danh sách hũ hiện có: {ds}. Hãy nói rõ tên hũ nhé!"

        if amount <= 0:
            return f"Bạn vui lòng cho biết số tiền muốn rút từ hũ **\"{matched_goal.ten_muc_tieu}\"** (hiện có **{matched_goal.so_tien_hien_tai:,.0f}đ**) nhé!"

        if amount > matched_goal.so_tien_hien_tai:
            return (
                f"Hũ **\"{matched_goal.ten_muc_tieu}\"** hiện chỉ có **{matched_goal.so_tien_hien_tai:,.0f}đ**, "
                f"không đủ để rút **{amount:,.0f}đ** bạn nhé! 😊\n\n"
                f"Bạn có thể rút tối đa {matched_goal.so_tien_hien_tai:,.0f}đ ạ."
            )

        matched_goal.so_tien_hien_tai -= amount
        if matched_goal.so_tien_hien_tai < matched_goal.so_tien_muc_tieu:
            matched_goal.trang_thai = "dang_thuc_hien"

        dm_sav = db.query(DanhMuc).filter(DanhMuc.ma_nd == ma_nd, DanhMuc.ten_dm == "Tiết kiệm").first()
        now = datetime.now()
        tx = GiaoDich(
            ma_nd=ma_nd,
            ma_dm=dm_sav.ma_dm if dm_sav else None,
            so_tien=amount,
            loai_gd="thu",
            ghi_chu=f"Rút tiền từ hũ {matched_goal.ten_muc_tieu} về ví chính",
            ngay_gd=now,
            ngay_tao=datetime.utcnow()
        )
        db.add(tx)
        db.commit()
        db.refresh(matched_goal)

        so_du_vi = NganSachService.tinh_so_du_vi_chinh(db, ma_nd)
        pct = round((matched_goal.so_tien_hien_tai / matched_goal.so_tien_muc_tieu) * 100) if matched_goal.so_tien_muc_tieu > 0 else 0

        return (
            f"Đã rút tiền từ hũ tiết kiệm về ví chính thành công! 💸\n\n"
            f"📋 **Thông tin rút tiền:**\n"
            f"• **Hũ trích tiền:** {matched_goal.ten_muc_tieu}\n"
            f"• **Số tiền rút:** **+{amount:,.0f}đ**\n"
            f"• **Số tiền còn lại trong hũ:** **{matched_goal.so_tien_hien_tai:,.0f}đ** / {matched_goal.so_tien_muc_tieu:,.0f}đ ({pct}%)\n"
            f"• 💳 **Số dư ví chính khả dụng:** **{so_du_vi:,.0f}đ**\n\n"
            f"Số tiền đã sẵn sàng trong ví chính để bạn sử dụng!"
        )

    @staticmethod
    def _xu_ly_tao_hu_tiet_kiem(db: Session, ma_nd: int, t: str, amount: float, raw: str) -> Optional[str]:
        deadline = None
        deadline_str = "Không giới hạn"
        m_date = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', raw)
        if m_date:
            try:
                d, m, y = int(m_date.group(1)), int(m_date.group(2)), int(m_date.group(3))
                deadline = date(y, m, d)
                deadline_str = f"{d:02d}/{m:02d}/{y}"
            except Exception:
                pass

        clean = raw
        clean = re.sub(r'^(hãy\s+)?(tạo|thêm|lập|đặt)\s+(hũ|mục tiêu|quỹ)\s*(tiết kiệm)?\s*', '', clean, flags=re.IGNORECASE)
        clean = re.sub(r'(?:hạn\s*chót|hạn|trước\s*ngày|đến\s*ngày)?\s*\d{1,2}[/-]\d{1,2}[/-]\d{4}', '', clean, flags=re.IGNORECASE)
        clean = re.sub(r'\d+\s*(?:tr|triệu|củ|k|nghìn|ngàn|đ|vnd|lít)', '', clean, flags=re.IGNORECASE)
        clean = re.sub(r'\b\d{4,}\b', '', clean)
        clean = re.sub(r'[^\w\s\u00C0-\u1EF9]', '', clean).strip()

        if not clean or len(clean) < 2:
            clean = "Mục tiêu tài chính"
        else:
            clean = clean[0].upper() + clean[1:]

        if amount <= 0:
            amount = 5_000_000.0

        new_goal = MucTieuTietKiem(
            ma_nd=ma_nd,
            ten_muc_tieu=clean,
            so_tien_muc_tieu=amount,
            so_tien_hien_tai=0.0,
            han_chot=deadline,
            trang_thai="dang_thuc_hien"
        )
        db.add(new_goal)
        db.commit()
        db.refresh(new_goal)

        return (
            f"Đã tạo hũ tiết kiệm mới thành công! 🎯\n\n"
            f"📋 **Thông tin mục tiêu:**\n"
            f"• **Tên hũ:** {new_goal.ten_muc_tieu}\n"
            f"• **Số tiền mục tiêu:** **{new_goal.so_tien_muc_tieu:,.0f}đ**\n"
            f"• **Đã tích lũy:** **0đ** (0%)\n"
            f"• **Hạn chót:** {deadline_str}\n\n"
            f"Hũ đã sẵn sàng! Bạn có thể bắt đầu tích lũy bằng cách nói: *'nộp 500k vào hũ {new_goal.ten_muc_tieu}'* bất kỳ lúc nào nhé! ✨"
        )

    @staticmethod
    def _xu_ly_xoa_danh_muc(db: Session, ma_nd: int, t: str) -> Optional[str]:
        user_cats = db.query(DanhMuc).filter(DanhMuc.ma_nd == ma_nd).all()
        if not user_cats:
            return "Hiện tại bạn chưa có danh mục nào để xóa."

        matched_cat = None
        for c in user_cats:
            if c.ten_dm.lower() in t:
                matched_cat = c
                break
        if not matched_cat:
            ds = ", ".join([f"\"{c.ten_dm}\"" for c in user_cats])
            return f"Bạn muốn xóa danh mục nào? Hiện có các danh mục: {ds}. Hãy nói rõ tên danh mục nhé!"

        cat_name = matched_cat.ten_dm
        cat_type = matched_cat.loai_dm
        cat_limit = float(matched_cat.han_muc or 0.0)

        spent = 0.0
        if cat_type == "chi":
            txs = db.query(GiaoDich).filter(GiaoDich.ma_dm == matched_cat.ma_dm, GiaoDich.loai_gd == "chi").all()
            spent = sum(item.so_tien for item in txs)
        remaining = max(0.0, cat_limit - spent)

        db.query(GiaoDich).filter(GiaoDich.ma_dm == matched_cat.ma_dm).delete()
        db.query(NganSach).filter(NganSach.ma_dm == matched_cat.ma_dm).delete()
        db.delete(matched_cat)
        db.commit()

        refund_msg = ""
        if cat_type == "chi" and remaining > 0:
            tb = ThongBao(
                ma_nd=ma_nd,
                tieu_de="💰 Hoàn Trả Hạn Mức Về Ví Chính",
                noi_dung=f"Đã xóa danh mục '{cat_name}'. Số tiền hạn mức còn lại {remaining:,.0f} đ đã được hoàn trả về ví chính."
            )
            db.add(tb)
            db.commit()
            refund_msg = f"• **Hạn mức khả dụng đã thu hồi:** **{remaining:,.0f}đ**\n"

        so_du_vi = NganSachService.tinh_so_du_vi_chinh(db, ma_nd)
        return (
            f"Đã xóa danh mục **\"{cat_name}\"** thành công! 🗑️\n\n"
            f"• **Loại:** {'Chi tiêu' if cat_type == 'chi' else 'Thu nhập'}\n"
            f"{refund_msg}"
            f"• 💳 **Số dư ví chính khả dụng:** **{so_du_vi:,.0f}đ**\n\n"
            f"Hệ thống đã cập nhật lại danh mục và hạn mức ngân sách của bạn."
        )

    @staticmethod
    def _xu_ly_doi_ten_danh_muc(db: Session, ma_nd: int, t: str, raw: str) -> Optional[str]:
        user_cats = db.query(DanhMuc).filter(DanhMuc.ma_nd == ma_nd).all()
        m = re.search(r'(?:đổi|sửa)\s+tên\s+(?:danh mục|hũ)?\s*["\']?([^"\']+)["\']?\s+thành\s+["\']?([^"\']+)["\']?', raw, re.IGNORECASE)
        if not m:
            return "Bạn hãy nói theo cú pháp: *'đổi tên danh mục [Tên cũ] thành [Tên mới]'* nhé! 😊"

        old_target = m.group(1).strip().lower()
        new_name = m.group(2).strip()

        matched_cat = None
        for c in user_cats:
            if c.ten_dm.lower() == old_target or c.ten_dm.lower() in old_target or old_target in c.ten_dm.lower():
                matched_cat = c
                break

        if not matched_cat:
            ds = ", ".join([f"\"{c.ten_dm}\"" for c in user_cats])
            return f"Không tìm thấy danh mục \"{m.group(1).strip()}\". Các danh mục hiện có: {ds}."

        old_display = matched_cat.ten_dm
        matched_cat.ten_dm = new_name[0].upper() + new_name[1:] if new_name else new_name
        db.commit()
        db.refresh(matched_cat)

        return (
            f"Đã đổi tên danh mục thành công! 🏷️\n\n"
            f"• **Tên cũ:** {old_display}\n"
            f"• **Tên mới:** **{matched_cat.ten_dm}**\n\n"
            f"Toàn bộ giao dịch và hạn mức liên quan đã được liên kết với tên danh mục mới."
        )

    @staticmethod
    def _xu_ly_tao_danh_muc(db: Session, ma_nd: int, t: str, amount: float, raw: str) -> Optional[str]:
        clean = re.sub(r'^(hãy\s+)?(tạo|thêm|lập)\s+(danh mục|hũ chi tiêu)\s*', '', raw, flags=re.IGNORECASE)
        clean = re.sub(r'(?:hạn\s*mức|ngân\s*sách)?\s*\d+\s*(?:tr|triệu|củ|k|nghìn|ngàn|đ|vnd|lít).*$', '', clean, flags=re.IGNORECASE)
        clean = clean.strip()
        if not clean:
            clean = "Danh mục mới"
        else:
            clean = clean[0].upper() + clean[1:]

        existing = db.query(DanhMuc).filter(DanhMuc.ma_nd == ma_nd, DanhMuc.ten_dm.ilike(clean)).first()
        if existing:
            return f"Danh mục **\"{clean}\"** đã tồn tại trong hệ thống rồi nhé! Bạn có thể đặt hạn mức hoặc ghi nhận giao dịch trực tiếp vào danh mục này."

        loai_dm = "thu" if "thu nhập" in t or "thu" in clean.lower() else "chi"
        new_cat = DanhMuc(
            ten_dm=clean,
            loai_dm=loai_dm,
            han_muc=amount,
            icon="tag",
            mau_sac="#6366f1",
            ma_nd=ma_nd
        )
        db.add(new_cat)
        db.commit()
        db.refresh(new_cat)

        if loai_dm == "chi" and amount > 0:
            thang_nam = datetime.now().strftime("%Y-%m")
            ns = NganSach(
                ma_nd=ma_nd,
                ma_dm=new_cat.ma_dm,
                thang_nam=thang_nam,
                han_muc=amount,
                so_tien_da_chi=0.0
            )
            db.add(ns)
            db.commit()

        limit_info = f"• **Hạn mức ban đầu:** **{amount:,.0f}đ**\n" if amount > 0 else "• **Hạn mức ban đầu:** Chưa thiết lập (0đ)\n"

        return (
            f"Đã tạo danh mục mới thành công! 📁\n\n"
            f"• **Tên danh mục:** {new_cat.ten_dm}\n"
            f"• **Phân loại:** {'Chi tiêu' if loai_dm == 'chi' else 'Thu nhập'}\n"
            f"{limit_info}\n"
            f"Danh mục đã sẵn sàng để ghi nhận các khoản thu chi của bạn!"
        )

    @staticmethod
    def _xu_ly_xoa_giao_dich(db: Session, ma_nd: int, t: str) -> Optional[str]:
        tx = None
        if any(w in t for w in ["gần nhất", "vừa rồi", "vừa thêm", "mới nhất", "vừa tạo", "vừa nhập"]):
            tx = db.query(GiaoDich).filter(GiaoDich.ma_nd == ma_nd).order_by(GiaoDich.ma_gd.desc()).first()
        else:
            recent_txs = db.query(GiaoDich).filter(GiaoDich.ma_nd == ma_nd).order_by(GiaoDich.ma_gd.desc()).limit(30).all()
            amt = AIService._parse_vietnamese_amount(t)
            for item in recent_txs:
                if amt > 0 and item.so_tien == amt:
                    tx = item
                    break
                gc = (item.ghi_chu or "").lower()
                words = [w for w in gc.split() if len(w) > 2]
                if words and any(w in t for w in words):
                    tx = item
                    break
            if not tx and recent_txs:
                tx = recent_txs[0]

        if not tx:
            return "Không tìm thấy giao dịch phù hợp để xóa."

        info_note = tx.ghi_chu or "Không có ghi chú"
        info_amt = tx.so_tien
        info_loai = tx.loai_gd
        ma_dm = tx.ma_dm
        ngay_gd = tx.ngay_gd

        db.delete(tx)
        db.commit()

        if info_loai == "chi" and ma_dm:
            NganSachService.kiem_tra_ngan_sach(db=db, ma_nd=ma_nd, ma_dm=ma_dm, ngay_gd=ngay_gd)

        so_du_vi = NganSachService.tinh_so_du_vi_chinh(db, ma_nd)

        return (
            f"Đã xóa giao dịch thành công! 🗑️\n\n"
            f"📋 **Giao dịch đã xóa:**\n"
            f"• **Nội dung:** {info_note}\n"
            f"• **Số tiền:** **{info_amt:,.0f}đ** ({'Chi tiêu' if info_loai == 'chi' else 'Thu nhập'})\n"
            f"• 💳 **Số dư ví chính khả dụng:** **{so_du_vi:,.0f}đ**\n\n"
            f"Dữ liệu lịch sử giao dịch và số dư ví của bạn đã được cập nhật lại chuẩn xác."
        )

    @staticmethod
    def _xu_ly_sua_giao_dich(db: Session, ma_nd: int, t: str, raw: str) -> Optional[str]:
        tx = None
        if any(w in t for w in ["gần nhất", "vừa rồi", "vừa thêm", "mới nhất"]):
            tx = db.query(GiaoDich).filter(GiaoDich.ma_nd == ma_nd).order_by(GiaoDich.ma_gd.desc()).first()
        else:
            recent_txs = db.query(GiaoDich).filter(GiaoDich.ma_nd == ma_nd).order_by(GiaoDich.ma_gd.desc()).limit(30).all()
            for item in recent_txs:
                gc = (item.ghi_chu or "").lower()
                words = [w for w in gc.split() if len(w) > 2]
                if words and any(w in t for w in words):
                    tx = item
                    break
            if not tx and recent_txs:
                tx = recent_txs[0]

        if not tx:
            return "Không tìm thấy giao dịch bạn muốn chỉnh sửa."

        old_note = tx.ghi_chu or ""
        old_amt = tx.so_tien
        changed = []

        new_amt = AIService._parse_vietnamese_amount(t)
        if new_amt > 0 and new_amt != old_amt:
            tx.so_tien = new_amt
            changed.append(f"Số tiền: **{old_amt:,.0f}đ** ➔ **{new_amt:,.0f}đ**")

        m_note = re.search(r'(?:đổi|sửa)\s+ghi\s*chú\s+(?:giao dịch\s+)?(?:gần nhất\s+)?thành\s+["\']?([^"\']+)["\']?', raw, re.IGNORECASE)
        if m_note:
            new_note = m_note.group(1).strip()
            if new_note and new_note != old_note:
                tx.ghi_chu = new_note[0].upper() + new_note[1:]
                changed.append(f"Ghi chú: *\"{old_note}\"* ➔ *\"{tx.ghi_chu}\"*")

        if not changed:
            return (
                f"Giao dịch gần nhất của bạn là **{old_note}** (**{old_amt:,.0f}đ**). "
                f"Bạn có thể nói: *'sửa giao dịch gần nhất thành 50k'* hoặc *'đổi ghi chú thành ăn trưa'* để mình cập nhật nhé!"
            )

        db.commit()
        db.refresh(tx)

        if tx.loai_gd == "chi" and tx.ma_dm:
            NganSachService.kiem_tra_ngan_sach(db=db, ma_nd=ma_nd, ma_dm=tx.ma_dm, ngay_gd=tx.ngay_gd)

        so_du_vi = NganSachService.tinh_so_du_vi_chinh(db, ma_nd)

        return (
            f"Đã cập nhật giao dịch thành công! ✏️\n\n"
            f"📋 **Các thay đổi:**\n" +
            "\n".join([f"• {c}" for c in changed]) +
            f"\n\n• 💳 **Số dư ví chính khả dụng:** **{so_du_vi:,.0f}đ**"
        )

    @staticmethod
    def _xu_ly_tra_cuu_giao_dich(db: Session, ma_nd: int, t: str, raw: str) -> Optional[str]:
        now = datetime.now()
        q = db.query(GiaoDich).filter(GiaoDich.ma_nd == ma_nd)

        title_suffix = ""
        if "hôm nay" in t:
            start_d = datetime(now.year, now.month, now.day)
            q = q.filter(GiaoDich.ngay_gd >= start_d)
            title_suffix = "hôm nay"
        elif "hôm qua" in t:
            start_d = datetime(now.year, now.month, now.day) - timedelta(days=1)
            end_d = datetime(now.year, now.month, now.day)
            q = q.filter(GiaoDich.ngay_gd >= start_d, GiaoDich.ngay_gd < end_d)
            title_suffix = "hôm qua"
        elif "tháng này" in t:
            start_d = datetime(now.year, now.month, 1)
            q = q.filter(GiaoDich.ngay_gd >= start_d)
            title_suffix = f"tháng {now.month}/{now.year}"

        user_cats = db.query(DanhMuc).filter(DanhMuc.ma_nd == ma_nd).all()
        cat_map = {c.ma_dm: c for c in user_cats}
        matched_c = next((c for c in user_cats if c.ten_dm.lower() in t), None)
        if matched_c:
            q = q.filter(GiaoDich.ma_dm == matched_c.ma_dm)
            title_suffix += f" danh mục '{matched_c.ten_dm}'"

        if any(w in t for w in ["trên", "lớn hơn", "cao hơn"]):
            amt = AIService._parse_vietnamese_amount(t)
            if amt > 0:
                q = q.filter(GiaoDich.so_tien >= amt)
                title_suffix += f" trên {amt:,.0f}đ"
        elif any(w in t for w in ["dưới", "nhỏ hơn", "thấp hơn"]):
            amt = AIService._parse_vietnamese_amount(t)
            if amt > 0:
                q = q.filter(GiaoDich.so_tien <= amt)
                title_suffix += f" dưới {amt:,.0f}đ"

        limit = 6
        m_num = re.search(r'(\d+)\s+giao dịch', t)
        if m_num:
            limit = min(20, max(1, int(m_num.group(1))))

        txs = q.order_by(GiaoDich.ngay_gd.desc(), GiaoDich.ma_gd.desc()).limit(limit).all()

        if not txs:
            return f"Không tìm thấy giao dịch nào phù hợp với yêu cầu tra cứu ({title_suffix.strip() or 'gần đây'})."

        total_amt = sum(item.so_tien for item in txs)
        lines = []
        for item in txs:
            c = cat_map.get(item.ma_dm)
            c_name = c.ten_dm if c else "Khác"
            sign = "💸 -" if item.loai_gd == "chi" else "💰 +"
            d_str = item.ngay_gd.strftime("%d/%m %H:%M") if item.ngay_gd else ""
            lines.append(f"• **{d_str}**: {item.ghi_chu or c_name} ➔ **{sign}{item.so_tien:,.0f}đ** ({c_name})")

        header = f"🔍 **Kết quả tra cứu giao dịch ({title_suffix.strip() or 'gần nhất'}):**"
        return (
            f"{header}\n\n" +
            "\n".join(lines) +
            f"\n\n📊 **Tổng cộng ({len(txs)} giao dịch):** **{total_amt:,.0f}đ**\n"
            f"Bạn có muốn lọc chi tiết hơn theo danh mục hoặc khoảng thời gian nào không?"
        )

    @staticmethod
    def _xu_ly_suc_khoe_tai_chinh(db: Session, ma_nd: int, t: str) -> Optional[str]:
        ctx = AIService._get_spending_context(db, ma_nd)
        tong_thu = ctx["thu_nhap"]["thang_nay"]
        tong_chi = ctx["chi_tieu"]["thang_nay"]
        so_du = ctx["so_du"]
        so_du_vi = ctx.get("so_du_vi_chinh", 0.0)
        thang = ctx["thang_hien_tai"]

        base_income = tong_thu if tong_thu > 0 else (tong_chi + 2_000_000 if tong_chi > 0 else 10_000_000)
        nec = base_income * 0.55
        ffa = base_income * 0.10
        ltss = base_income * 0.10
        edu = base_income * 0.10
        play = base_income * 0.10
        give = base_income * 0.05

        score = 70
        factors = []
        if tong_thu > 0:
            sav_rate = max(0.0, (tong_thu - tong_chi) / tong_thu)
            if sav_rate >= 0.20:
                score += 20
                factors.append("✅ Tỷ lệ tiết kiệm đạt chuẩn vàng (≥ 20% thu nhập)")
            elif sav_rate > 0:
                score += 10
                factors.append("✅ Dòng tiền dương, có khoản tích lũy dôi ra")
            else:
                score -= 25
                factors.append("⚠️ Chi tiêu vượt quá thu nhập tháng này")
        else:
            factors.append("💡 Chưa ghi nhận thu nhập tháng này để tính tỷ lệ chính xác")

        if so_du_vi > 0:
            score += 10
            factors.append(f"✅ Ví chính khả dụng an toàn ({so_du_vi:,.0f}đ)")
        else:
            score -= 10
            factors.append("⚠️ Số dư ví chính đang ở mức thấp")

        score = max(30, min(100, score))
        rank = "Xuất sắc 🌟" if score >= 85 else ("Tốt & Ổn định 👍" if score >= 70 else "Cần thắt chặt & Tối ưu ⚠️")

        return (
            f"🏥 **Đánh Giá Sức Khỏe Tài Chính Tháng {thang}**\n\n"
            f"🎯 **Điểm số sức khỏe:** **{score}/100** — Đánh giá: **{rank}**\n\n"
            f"📊 **Các chỉ số cốt lõi:**\n" +
            "\n".join([f"• {f}" for f in factors]) +
            f"\n\n🏺 **Đề Xuất Phân Bổ Theo Phương Pháp 6 Chiếc Hũ (T. Harv Eker)**\n"
            f"*(Tính trên thu nhập cơ sở **{base_income:,.0f}đ**)*:\n"
            f"1. **NEC - Hũ Thiết Yếu (55%):** **{nec:,.0f}đ** *(Ăn uống, thuê nhà, xăng xe, hóa đơn)*\n"
            f"2. **FFA - Tự Do Tài Chính (10%):** **{ffa:,.0f}đ** *(Đầu tư sinh lời, tạo dòng tiền thụ động)*\n"
            f"3. **LTSS - Tiết Kiệm Dài Hạn (10%):** **{ltss:,.0f}đ** *(Quỹ khẩn cấp, mua sắm lớn, du lịch)*\n"
            f"4. **EDU - Học Tập & Phát Triển (10%):** **{edu:,.0f}đ** *(Sách, khóa học, nâng cao kỹ năng)*\n"
            f"5. **PLAY - Hưởng Thụ Cá Nhân (10%):** **{play:,.0f}đ** *(Xem phim, cafe, giải trí tự thưởng)*\n"
            f"6. **GIVE - Cho Đi (5%):** **{give:,.0f}đ** *(Từ thiện, hiếu hỉ, giúp đỡ người thân)*\n\n"
            f"💡 Bạn có thể nhờ mình tạo hũ hoặc điều chỉnh hạn mức bất kỳ lúc nào nhé!"
        )

    @staticmethod
    def xu_ly_giao_dich_tu_nhien(db: Session, ma_nd: int, cau_hoi: str, lich_su_chat: Optional[List[Dict[str, str]]] = None) -> Optional[str]:
        """
        AI Financial Autonomous Agent:
        Tự động phân tích ngôn ngữ tự nhiên từ mọi yêu cầu giao tiếp của người dùng
        để thao tác toàn diện trên hệ thống: Thêm / Sửa / Xóa / Tra cứu giao dịch,
        Quản lý Hũ tiết kiệm (Tạo, Nộp, Rút, Đổi mục tiêu, Xóa),
        Quản lý Danh mục & Ngân sách hũ (Tạo, Đổi tên, Đổi hạn mức, Xóa),
        và Phân tích Sức khỏe tài chính 6 Hũ.
        Hỗ trợ hội thoại đa lượt (Multi-turn Context Resolution) thông minh khi người dùng
        bổ sung số tiền hoặc câu trả lời ngắn cho câu hỏi trước của AI.
        """
        raw = cau_hoi.strip()
        t = raw.lower()
        amount = AIService._parse_vietnamese_amount(t)

        # Xử lý hội thoại đa lượt (Multi-turn Context):
        # Khi người dùng chỉ gửi số tiền (vd: '30k', 'hết 30k', '50.000', '20 ngàn'...)
        # sau khi đã nói về một hành động hoặc AI vừa hỏi xin số tiền
        if lich_su_chat and amount > 0 and len(t.split()) <= 4:
            prev_user_msgs = [m.get("content", "").strip() for m in lich_su_chat if m.get("role") in ["user", "nguoi_dung"] and m.get("content", "").strip()]
            prev_ai_msgs = [m.get("content", "").strip() for m in lich_su_chat if m.get("role") in ["assistant", "ai", "ai_tro_ly"] and m.get("content", "").strip()]

            last_user = prev_user_msgs[-1] if prev_user_msgs else ""
            last_ai = prev_ai_msgs[-1] if prev_ai_msgs else ""

            # 1. Thử kết hợp câu nói trước đó của người dùng với số tiền mới
            if last_user and AIService._parse_vietnamese_amount(last_user.lower()) <= 0:
                combined_cand = f"{last_user} {raw}"
                res_comb = AIService.xu_ly_giao_dich_tu_nhien(db, ma_nd, combined_cand, lich_su_chat=None)
                if res_comb:
                    return res_comb

            # 2. Nếu câu trước đó của AI có nhắc đến danh mục cụ thể hoặc hành động
            for cname in ["Ăn uống", "Đi lại", "Mua sắm", "Hóa đơn", "Giải trí", "Sức khỏe", "Tiết kiệm", "Tiền lương"]:
                if cname.lower() in last_ai.lower() or cname.lower() in last_user.lower():
                    action_type = "chi" if cname != "Tiền lương" else "thu"
                    note_cand = AIService._lam_sach_mo_ta_giao_dich(last_user, cname) if last_user else cname
                    combined_cand = f"ghi nhận {action_type} {raw} {cname} {note_cand}"
                    res_comb = AIService.xu_ly_giao_dich_tu_nhien(db, ma_nd, combined_cand, lich_su_chat=None)
                    if res_comb:
                        return res_comb

        # 1. HỦY / XOÁ HŨ TIẾT KIỆM (DELETE SAVINGS GOAL)
        if any(w in t for w in ["xóa hũ", "xoá hũ", "hủy hũ", "huỷ hũ", "xóa mục tiêu", "xoá mục tiêu", "hủy mục tiêu", "huỷ mục tiêu", "bỏ hũ", "bỏ mục tiêu"]):
            return AIService._xu_ly_xoa_hu_tiet_kiem(db, ma_nd, t)

        # 2. RÚT TIỀN TỪ HŨ TIẾT KIỆM VỀ VÍ CHÍNH (WITHDRAW FROM SAVINGS GOAL)
        if any(w in t for w in ["rút", "hoàn lại", "lấy lại"]) and any(w in t for w in ["hũ", "mục tiêu", "tiết kiệm"]):
            return AIService._xu_ly_rut_tien_hu(db, ma_nd, t, amount)

        # 3. TẠO HŨ TIẾT KIỆM MỚI (CREATE SAVINGS GOAL)
        if any(w in t for w in ["tạo hũ tiết kiệm", "thêm hũ tiết kiệm", "lập hũ tiết kiệm", "tạo mục tiêu", "thêm mục tiêu", "lập mục tiêu", "đặt mục tiêu tiết kiệm", "tạo hũ", "thêm hũ"]):
            if not any(w in t for w in ["nâng", "tăng", "đổi", "sửa", "giảm", "hạ", "chỉnh", "nộp", "trích", "rút", "xóa", "hủy"]):
                return AIService._xu_ly_tao_hu_tiet_kiem(db, ma_nd, t, amount, raw)

        # 4. NÂNG / GIẢM / ĐỔI MỤC TIÊU TIẾT KIỆM (UPDATE SAVINGS GOAL TARGET)
        goals = db.query(MucTieuTietKiem).filter(MucTieuTietKiem.ma_nd == ma_nd).all()
        sorted_goals = sorted(goals, key=lambda g: len(g.ten_muc_tieu), reverse=True)
        matched_goal = None
        for g in sorted_goals:
            g_name = g.ten_muc_tieu.lower()
            if g_name in t or any(w in t for w in g_name.split() if len(w) > 2):
                matched_goal = g
                break

        update_goal_cues = [
            "nâng mục tiêu", "tăng mục tiêu", "đổi mục tiêu", "sửa mục tiêu", "hạ mục tiêu", "giảm mục tiêu",
            "đặt mục tiêu", "chỉnh mục tiêu", "mục tiêu tiết kiệm lên", "mục tiêu lên", "mục tiêu thành",
            "mục tiêu là", "nâng hũ", "tăng hũ", "đổi hũ", "sửa hũ", "nâng quỹ", "tăng quỹ", "đổi quỹ", "sửa quỹ",
            "nâng giúp tôi quỹ", "tăng giúp tôi quỹ", "nâng giúp tôi mục tiêu", "tăng giúp tôi mục tiêu"
        ]
        has_goal_term = any(w in t for w in ["mục tiêu", "hũ", "quỹ", "tiết kiệm", "heo", "lợn"])
        has_update_verb = any(w in t for w in ["nâng", "tăng", "đổi", "sửa", "chỉnh", "đặt lại", "thành", "giảm", "hạ", "lên mức", "lên"])
        not_deposit = not any(w in t for w in ["nộp", "trích", "nạp", "bỏ", "chuyển", "gửi", "giao dịch", "hạn mức"])

        is_update_goal = any(c in t for c in update_goal_cues) or (
            (has_goal_term or matched_goal) and has_update_verb and not_deposit
        )
        if is_update_goal and amount > 0:
            if not matched_goal and goals:
                matched_goal = next((g for g in goals if g.trang_thai != "hoan_thanh"), goals[0])

            if not matched_goal:
                goal_name = "Mục tiêu tài chính"
                for kw in ["du lịch", "mua xe", "mua nhà", "học tập", "cưới hỏi", "khẩn cấp"]:
                    if kw in t:
                        goal_name = kw.capitalize()
                        break
                matched_goal = MucTieuTietKiem(
                    ten_muc_tieu=goal_name,
                    so_tien_muc_tieu=amount,
                    so_tien_hien_tai=0.0,
                    ma_nd=ma_nd,
                    trang_thai="dang_thuc_hien"
                )
                db.add(matched_goal)
                db.commit()
                db.refresh(matched_goal)
            else:
                curr_amt = float(matched_goal.so_tien_hien_tai or 0.0)
                if amount < curr_amt:
                    return (
                        f"Dạ số tiền mục tiêu mới (**{amount:,.0f}đ**) không thể nhỏ hơn số tiền bạn đã tích lũy "
                        f"trong hũ **'{matched_goal.ten_muc_tieu}'** (**{curr_amt:,.0f}đ**) nhé! 😊\n\n"
                        f"Bạn có thể đặt mục tiêu lớn hơn hoặc giữ nguyên để tiếp tục tích lũy ạ."
                    )
                matched_goal.so_tien_muc_tieu = amount
                if matched_goal.so_tien_hien_tai >= matched_goal.so_tien_muc_tieu:
                    matched_goal.trang_thai = "hoan_thanh"
                else:
                    matched_goal.trang_thai = "dang_thuc_hien"
                db.commit()
                db.refresh(matched_goal)

            pct = round((matched_goal.so_tien_hien_tai / matched_goal.so_tien_muc_tieu) * 100) if matched_goal.so_tien_muc_tieu > 0 else 0
            con_thieu = max(0.0, matched_goal.so_tien_muc_tieu - matched_goal.so_tien_hien_tai)

            return (
                f"Đã cập nhật mục tiêu tiết kiệm thành công! 🎯\n\n"
                f"📋 **Thông tin mục tiêu sau điều chỉnh:**\n"
                f"• **Tên mục tiêu:** {matched_goal.ten_muc_tieu}\n"
                f"• **Mục tiêu mới:** **{matched_goal.so_tien_muc_tieu:,.0f}đ**\n"
                f"• **Đã tích lũy:** **{matched_goal.so_tien_hien_tai:,.0f}đ** ({pct}%)\n"
                f"• **Cần tiết kiệm thêm:** **{con_thieu:,.0f}đ**\n\n"
                f"Hệ thống đã cập nhật cột mốc mới trên giao diện. Chúc bạn sớm đạt được mục tiêu này nhé! ✨"
            )

        # 5. NỘP TIỀN / TRÍCH VÀO HŨ TIẾT KIỆM (DEPOSIT TO GOAL)
        deposit_cues = ["nộp vào", "trích vào", "nạp vào", "tiết kiệm vào", "bỏ heo", "bỏ lợn", "chuyển vào hũ", "gửi vào hũ", "chuyển vào mục tiêu", "nộp hũ"]
        is_deposit_goal = any(c in t for c in deposit_cues) or (
            any(w in t for w in ["nộp", "trích", "nạp", "chuyển"]) and any(w in t for w in ["hũ", "mục tiêu", "tiết kiệm", "heo", "lợn"])
        )
        if is_deposit_goal and amount > 0:
            goals = db.query(MucTieuTietKiem).filter(MucTieuTietKiem.ma_nd == ma_nd).all()
            matched_goal = None
            for g in goals:
                g_name = g.ten_muc_tieu.lower()
                if g_name in t or any(w in t for w in g_name.split() if len(w) > 2):
                    matched_goal = g
                    break
            if not matched_goal and goals:
                matched_goal = next((g for g in goals if g.trang_thai != "hoan_thanh"), goals[0])

            if matched_goal:
                current_balance = NganSachService.tinh_so_du_vi_chinh(db, ma_nd)
                if amount > current_balance:
                    return (
                        f"Dạ số dư ví chính khả dụng hiện tại (**{max(0.0, current_balance):,.0f}đ**) không đủ "
                        f"để trích **{amount:,.0f}đ** vào hũ **'{matched_goal.ten_muc_tieu}'** ạ! 💳\n\n"
                        f"Bạn hãy nạp thêm tiền hoặc điều chỉnh số tiền trích hợp lý hơn nhé! 😊"
                    )

                if matched_goal.so_tien_hien_tai >= matched_goal.so_tien_muc_tieu:
                    return (
                        f"🎉 Hũ tiết kiệm **'{matched_goal.ten_muc_tieu}'** của bạn đã hoàn thành 100% rồi! "
                        f"Bạn có thể tạo thêm mục tiêu tài chính mới để tiếp tục tích lũy nhé! ✨"
                    )

                max_can_nop = matched_goal.so_tien_muc_tieu - matched_goal.so_tien_hien_tai
                actual_deposit = min(amount, max_can_nop)

                dm_sav = db.query(DanhMuc).filter(DanhMuc.ma_nd == ma_nd, DanhMuc.ten_dm == "Tiết kiệm").first()
                if not dm_sav:
                    dm_sav = DanhMuc(ten_dm="Tiết kiệm", loai_dm="chi", han_muc=0.0, icon="piggy-bank", mau_sac="#10b981", ma_nd=ma_nd)
                    db.add(dm_sav)
                    db.commit()
                    db.refresh(dm_sav)

                now = datetime.now()
                tx = GiaoDich(
                    ma_nd=ma_nd,
                    ma_dm=dm_sav.ma_dm,
                    so_tien=actual_deposit,
                    loai_gd="chi",
                    ghi_chu=f"Mục tiêu: {matched_goal.ten_muc_tieu}",
                    ngay_gd=now,
                    ngay_tao=datetime.utcnow()
                )
                db.add(tx)
                matched_goal.so_tien_hien_tai += actual_deposit
                db.commit()
                db.refresh(matched_goal)

                pct = round((matched_goal.so_tien_hien_tai / matched_goal.so_tien_muc_tieu) * 100)
                so_du_moi = NganSachService.tinh_so_du_vi_chinh(db, ma_nd)

                con_lai_msg = ""
                if amount > actual_deposit:
                    con_lai_msg = f"\n*(Mục tiêu chỉ cần thêm {actual_deposit:,.0f}đ để đạt 100%, số tiền thừa {amount - actual_deposit:,.0f}đ vẫn ở ví chính của bạn)*"

                if pct >= 100:
                    celebration = f"🥳 **ĐÃ HOÀN THÀNH 100% MỤC TIÊU!** Chúc mừng bạn đã cán đích thành công!"
                    title_tb = f"🎉 Chúc Mừng Hoàn Thành Mục Tiêu '{matched_goal.ten_muc_tieu}'!"
                    msg_tb = f"Tuyệt vời! Bạn đã hoàn thành 100% mục tiêu '{matched_goal.ten_muc_tieu}' ({matched_goal.so_tien_hien_tai:,.0f}đ / {matched_goal.so_tien_muc_tieu:,.0f}đ)!"
                    db.add(ThongBao(ma_nd=ma_nd, tieu_de=title_tb, noi_dung=msg_tb, da_xem=False, ngay_tao=now))
                    db.commit()
                elif pct >= 80:
                    celebration = f"📈 **Tiến độ:** Đạt **{pct}%** (còn thiếu {matched_goal.so_tien_muc_tieu - matched_goal.so_tien_hien_tai:,.0f}đ nữa là chạm đích)"
                    title_tb = f"🌟 Động Viên: Sắp Đạt Mục Tiêu '{matched_goal.ten_muc_tieu}' ({pct}%)!"
                    msg_tb = f"Cố lên! Hũ '{matched_goal.ten_muc_tieu}' đã đạt {pct}%. Bạn sắp chạm đích rồi!"
                    db.add(ThongBao(ma_nd=ma_nd, tieu_de=title_tb, noi_dung=msg_tb, da_xem=False, ngay_tao=now))
                    db.commit()
                else:
                    celebration = f"📈 **Tiến độ:** Đạt **{pct}%** ({matched_goal.so_tien_hien_tai:,.0f}đ / {matched_goal.so_tien_muc_tieu:,.0f}đ)"

                return (
                    f"Tuyệt vời! Mình đã ghi nhận trích **{actual_deposit:,.0f}đ** từ ví chính vào hũ tiết kiệm **\"{matched_goal.ten_muc_tieu}\"** cho bạn rồi nhé! 🎉{con_lai_msg}\n\n"
                    f"🎯 **Cập nhật hũ \"{matched_goal.ten_muc_tieu}\":**\n"
                    f"• **Tích lũy:** **{matched_goal.so_tien_hien_tai:,.0f}đ** / {matched_goal.so_tien_muc_tieu:,.0f}đ\n"
                    f"• {celebration}\n"
                    f"• 💳 **Số dư ví chính khả dụng:** **{so_du_moi:,.0f}đ**\n\n"
                    f"Kiên trì tiết kiệm kỷ luật mỗi ngày là chìa khóa vững chắc cho tự do tài chính! ✨"
                )

        # 6. XOÁ DANH MỤC (DELETE CATEGORY)
        if any(w in t for w in ["xóa danh mục", "xoá danh mục", "hủy danh mục", "huỷ danh mục", "xóa hũ ngân sách", "xoá hũ ngân sách"]):
            return AIService._xu_ly_xoa_danh_muc(db, ma_nd, t)

        # 7. ĐỔI TÊN DANH MỤC (RENAME CATEGORY)
        if any(w in t for w in ["đổi tên danh mục", "sửa tên danh mục", "đổi tên hũ", "sửa tên hũ"]):
            return AIService._xu_ly_doi_ten_danh_muc(db, ma_nd, t, raw)

        # 8. TẠO DANH MỤC MỚI (CREATE CATEGORY)
        if any(w in t for w in ["tạo danh mục", "thêm danh mục", "lập danh mục"]):
            return AIService._xu_ly_tao_danh_muc(db, ma_nd, t, amount, raw)

        # 9. ĐIỀU CHỈNH HẠN MỨC NGÂN SÁCH HŨ (UPDATE BUDGET LIMIT)
        update_limit_cues = [
            "nâng hạn mức", "tăng hạn mức", "đổi hạn mức", "sửa hạn mức", "giảm hạn mức", "chỉnh hạn mức",
            "đặt hạn mức", "hạn mức lên", "hạn mức thành", "hạn mức hũ"
        ]
        is_update_limit = any(c in t for c in update_limit_cues) or (
            "hạn mức" in t and any(w in t for w in ["nâng", "tăng", "đổi", "sửa", "chỉnh", "đặt", "thành", "lên", "giảm"])
        )
        if is_update_limit and amount > 0:
            user_dms = db.query(DanhMuc).filter(DanhMuc.ma_nd == ma_nd, DanhMuc.loai_dm == "chi").all()
            target_dm = None
            for dm in user_dms:
                if dm.ten_dm.lower() in t:
                    target_dm = dm
                    break
            if not target_dm:
                for dm in user_dms:
                    for kw in ["ăn uống", "đi chơi", "mua sắm", "đi lại", "hóa đơn", "giải trí"]:
                        if kw in t and kw in dm.ten_dm.lower():
                            target_dm = dm
                            break
                    if target_dm:
                        break
            if not target_dm and user_dms:
                target_dm = user_dms[0]

            if target_dm:
                now_chk = datetime.now()
                start_this = datetime(now_chk.year, now_chk.month, 1)
                end_this = datetime(now_chk.year + 1, 1, 1) if now_chk.month == 12 else datetime(now_chk.year, now_chk.month + 1, 1)
                txs = db.query(GiaoDich).filter(
                    GiaoDich.ma_dm == target_dm.ma_dm,
                    GiaoDich.loai_gd == "chi",
                    GiaoDich.ngay_gd >= start_this,
                    GiaoDich.ngay_gd < end_this
                ).all()
                spent = sum(item.so_tien for item in txs)
                if amount < spent:
                    return (
                        f"Dạ hạn mức mới (**{amount:,.0f}đ**) không thể nhỏ hơn số tiền bạn đã chi tiêu tháng này "
                        f"trong hũ **'{target_dm.ten_dm}'** (**{spent:,.0f}đ**) nhé! 😊\n\n"
                        f"Bạn vui lòng đặt hạn mức tối thiểu bằng {spent:,.0f}đ ạ."
                    )

                target_dm.han_muc = amount
                thang_nam = datetime.now().strftime("%Y-%m")
                ns = db.query(NganSach).filter(
                    NganSach.ma_nd == ma_nd,
                    NganSach.ma_dm == target_dm.ma_dm,
                    NganSach.thang_nam == thang_nam
                ).first()
                if ns:
                    ns.han_muc = amount
                db.commit()
                db.refresh(target_dm)

                pct = round((spent / amount) * 100) if amount > 0 else 0
                con_lai = max(0.0, amount - spent)

                return (
                    f"Đã điều chỉnh hạn mức ngân sách thành công! 🏺\n\n"
                    f"📋 **Thông tin hũ chi tiêu sau điều chỉnh:**\n"
                    f"• **Hũ ngân sách:** {target_dm.ten_dm}\n"
                    f"• **Hạn mức mới:** **{amount:,.0f}đ**\n"
                    f"• **Đã chi tiêu tháng này:** **{spent:,.0f}đ** ({pct}%)\n"
                    f"• **Hạn mức còn lại:** **{con_lai:,.0f}đ**\n\n"
                    f"Hạn mức mới đã được áp dụng trực tiếp vào hệ thống quản lý ngân sách tháng này! 💡"
                )

        # 10. XOÁ / HỦY GIAO DỊCH (DELETE TRANSACTION)
        if any(w in t for w in ["xóa giao dịch", "xoá giao dịch", "hủy giao dịch", "huỷ giao dịch", "xóa khoản chi", "hủy khoản chi", "xóa giao dịch vừa", "hủy giao dịch gần"]):
            return AIService._xu_ly_xoa_giao_dich(db, ma_nd, t)

        # 11. SỬA / CẬP NHẬT GIAO DỊCH (EDIT TRANSACTION)
        if any(w in t for w in ["sửa giao dịch", "đổi giao dịch", "chỉnh giao dịch", "sửa khoản chi", "đổi khoản chi", "sửa số tiền", "đổi số tiền", "sửa ghi chú", "đổi ghi chú"]):
            return AIService._xu_ly_sua_giao_dich(db, ma_nd, t, raw)

        # 12. TRA CỨU / LỌC GIAO DỊCH (QUERY TRANSACTIONS)
        if any(w in t for w in ["tìm giao dịch", "tra cứu giao dịch", "xem giao dịch", "liệt kê giao dịch", "các giao dịch", "các khoản chi trên", "khoản chi lớn", "hôm nay tôi đã tiêu những gì", "hôm nay đã chi gì", "hôm nay đã tiêu gì", "hôm qua đã tiêu"]):
            return AIService._xu_ly_tra_cuu_giao_dich(db, ma_nd, t, raw)

        # 13. ĐÁNH GIÁ SỨC KHỎE TÀI CHÍNH & PHÂN BỔ 6 HŨ (FINANCIAL HEALTH & 6 JARS)
        if any(w in t for w in ["sức khỏe tài chính", "chấm điểm tài chính", "đánh giá tài chính", "phân bổ 6 hũ", "tư vấn 6 hũ", "chia 6 hũ"]):
            return AIService._xu_ly_suc_khoe_tai_chinh(db, ma_nd, t)

        # 14. THÊM GIAO DỊCH THU / CHI THÔNG THƯỜNG (ADD TRANSACTION)
        question_markers = [
            "bao nhiêu", "bao nhiu", "mấy", "thế nào", "sao", "gì", "không?", "ko?", "chưa?",
            "đâu", "ở đâu", "khi nào", "tại sao", "vì sao", "liệu", "có nên", "tư vấn", "gợi ý",
            "báo cáo", "thống kê", "phân tích", "xem lại", "kiểm tra", "cho tôi biết", "hỏi",
            "như thế nào", "giúp tôi biết", "liệt kê"
        ]
        command_markers = [
            "hãy ghi nhận", "ghi nhận giúp", "thêm giao dịch", "ghi sổ", "lưu giao dịch",
            "tạo giao dịch", "ghi vào", "nhập giúp", "thêm giúp", "ghi giúp", "hãy thêm"
        ]
        has_command = any(m in t for m in command_markers)
        has_question = any(m in t for m in question_markers) or t.endswith("?")

        if has_question and not has_command:
            return None

        loai_gd = "chi"
        suggested_cat = None
        extracted_note = None

        if amount <= 0 and any(kw in t for kw in ["triệu", "nghìn", "ngàn", "trăm", "củ", "lít"]) and any(kw in t for kw in ["ăn", "mua", "uống", "chi", "tiêu", "hết", "lương", "thưởng", "nộp"]):
            try:
                cat_names = [dm.ten_dm for dm in db.query(DanhMuc).filter(DanhMuc.ma_nd == ma_nd).all()]
                ext_prompt = (
                    "Bạn là bộ trích xuất dữ liệu tài chính cho MoneyMind. Hãy phân tích câu sau: "
                    f"'{raw}'.\n"
                    f"Danh mục người dùng: {', '.join(cat_names)}.\n"
                    "Nếu câu này là yêu cầu/thông báo chi tiêu hoặc thu nhập, hãy trả về DUY NHẤT một chuỗi JSON hợp lệ dạng:\n"
                    '{"la_giao_dich": true, "so_tien": 20000, "loai_gd": "chi", "ten_danh_muc": "Ăn uống", "ghi_chu": "Ăn bánh mì"}\n'
                    "Nếu không phải (hoặc là câu hỏi tư vấn), trả về: {\"la_giao_dich\": false}"
                )
                ai_raw = AIService._call_gemini_with_timeout(ext_prompt, timeout=8.0)
                json_match = re.search(r'\{.*\}', ai_raw, re.DOTALL)
                if json_match:
                    ai_data = json.loads(json_match.group(0))
                    if ai_data.get("la_giao_dich") and ai_data.get("so_tien", 0) > 0:
                        amount = float(ai_data["so_tien"])
                        loai_gd = ai_data.get("loai_gd", "chi")
                        suggested_cat = ai_data.get("ten_danh_muc")
                        extracted_note = ai_data.get("ghi_chu")
            except Exception:
                pass

        if amount <= 0:
            return None

        if "mục tiêu" in t or "hạn mức" in t:
            return None

        thu_cues = ["nhận lương", "tiền lương", "thưởng", "được thưởng", "được cho", "được tặng", "thu nhập", "bán được", "hoàn tiền", "kiếm được", "vừa nhận", "cộng tiền"]
        chi_cues = ["đi ăn", "ăn", "uống", "mua", "đổ xăng", "chi tiêu", "chi ", "tốn", "tiêu", "trả tiền", "thanh toán", "đóng tiền", "gửi xe", "vé", "phí", "tiền điện", "tiền nước"]

        is_thu = any(AIService._match_keyword(w, t) for w in thu_cues)
        is_chi = any(AIService._match_keyword(w, t) for w in chi_cues)

        if not (is_thu or is_chi or has_command):
            return None

        if is_thu and not any(AIService._match_keyword(w, t) for w in ["trả lương", "chi thưởng", "tiền điện", "tiền nhà"]):
            loai_gd = "thu"
        else:
            loai_gd = "chi"

        category_defs = [
            ("Đi lại", ["đổ xăng", "xăng xe", "xăng", "grab", "be", "gojek", "taxi", "xe ôm", "vé xe", "vé tàu", "vé máy bay", "gửi xe", "sửa xe", "rửa xe", "bảo dưỡng", "thay nhớt", "xăm lốp", "xe buýt", "bus"], "car", "#f59e0b"),
            ("Ăn uống", ["bánh mì", "cơm", "phở", "bún", "mỳ", "miến", "hủ tiếu", "cafe", "cà phê", "trà sữa", "trà", "nước ngọt", "nhậu", "lẩu", "nướng", "bbq", "pizza", "kfc", "bánh", "kẹo", "ăn vặt", "hoa quả", "trái cây", "chợ", "siêu thị", "ăn trưa", "ăn sáng", "ăn tối", "đồ ăn", "nấu ăn", "quán ăn", "ăn uống", "ăn", "uống"], "utensils", "#ef4444"),
            ("Mua sắm", ["quần áo", "áo sơ mi", "áo khoác", "áo thun", "áo", "quần", "giày", "dép", "túi xách", "túi", "ví", "mỹ phẩm", "son", "shopee", "lazada", "tiki", "tiktok shop", "đồng hồ", "điện thoại", "tai nghe", "laptop", "mua"], "shopping-bag", "#8b5cf6"),
            ("Hóa đơn", ["tiền điện", "tiền nước", "tiền mạng", "tiền internet", "wifi", "tiền nhà", "tiền phòng", "phí chung cư", "nạp điện thoại", "tiền điện thoại", "điện", "nước"], "file-text", "#06b6d4"),
            ("Giải trí", ["xem phim", "rạp chiếu phim", "cinema", "nạp game", "game", "karaoke", "du lịch", "dã ngoại", "camping", "bar", "pub", "bida", "bowling", "đi chơi"], "film", "#ec4899"),
            ("Sức khỏe", ["khám bệnh", "thuốc", "bệnh viện", "bác sĩ", "nha khoa", "răng", "tập gym", "gym", "yoga", "fitness"], "heart", "#10b981"),
            ("Tiết kiệm", ["hũ tiết kiệm", "tiết kiệm", "tích lũy", "bỏ lợn", "bỏ heo", "vào hũ"], "piggy-bank", "#10b981"),
            ("Tiền lương", ["nhận lương", "tiền lương", "tiền thưởng", "hoa hồng", "lương", "thưởng", "thu nhập"], "dollar-sign", "#22c55e")
        ]

        matched_cat_tuple = None
        if loai_gd == "thu":
            matched_cat_tuple = category_defs[7]
        elif suggested_cat:
            for cat_def in category_defs:
                if cat_def[0].lower() in suggested_cat.lower() or suggested_cat.lower() in cat_def[0].lower():
                    matched_cat_tuple = cat_def
                    break

        if not matched_cat_tuple and loai_gd == "chi":
            for cat_def in category_defs:
                cname, kw_list, icon, col = cat_def
                sorted_kws = sorted(kw_list, key=len, reverse=True)
                for kw in sorted_kws:
                    if AIService._match_keyword(kw, t):
                        matched_cat_tuple = cat_def
                        break
                if matched_cat_tuple:
                    break

        user_dms = db.query(DanhMuc).filter(DanhMuc.ma_nd == ma_nd).all()
        target_dm = None

        if matched_cat_tuple:
            cname, _, icon, col = matched_cat_tuple
            for dm in user_dms:
                if cname.lower() in dm.ten_dm.lower() or dm.ten_dm.lower() in cname.lower():
                    if dm.loai_dm == loai_gd:
                        target_dm = dm
                        break

            if not target_dm:
                target_dm = DanhMuc(
                    ten_dm=cname,
                    loai_dm=loai_gd,
                    han_muc=0.0,
                    icon=icon,
                    mau_sac=col,
                    ma_nd=ma_nd
                )
                db.add(target_dm)
                db.commit()
                db.refresh(target_dm)

        if not target_dm:
            for dm in user_dms:
                if dm.loai_dm == loai_gd:
                    target_dm = dm
                    break

        if not target_dm:
            default_name = "Chi tiêu khác" if loai_gd == "chi" else "Thu nhập khác"
            target_dm = DanhMuc(ten_dm=default_name, loai_dm=loai_gd, han_muc=0.0, ma_nd=ma_nd)
            db.add(target_dm)
            db.commit()
            db.refresh(target_dm)

        note_source = extracted_note if extracted_note else raw
        clean_note = AIService._lam_sach_mo_ta_giao_dich(note_source, target_dm.ten_dm)

        now = datetime.now()
        tx = GiaoDich(
            ma_nd=ma_nd,
            ma_dm=target_dm.ma_dm,
            so_tien=amount,
            loai_gd=loai_gd,
            ghi_chu=clean_note,
            ngay_gd=now,
            ngay_tao=datetime.utcnow()
        )
        db.add(tx)
        db.commit()
        db.refresh(tx)

        canh_bao_str = ""
        if loai_gd == "chi":
            cb = NganSachService.kiem_tra_ngan_sach(db, ma_nd, target_dm.ma_dm, now)
            if cb.vuot_ngan_sach:
                pct_chi = round(cb.ty_le * 100)
                canh_bao_str = (
                    f"\n\n🚨 **CẢNH BÁO:** Hũ **\"{target_dm.ten_dm}\"** đã vượt hạn mức tháng! "
                    f"(Đã chi **{cb.so_tien_da_chi:,.0f}đ** / Hạn mức **{cb.han_muc:,.0f}đ** - đạt {pct_chi}%). "
                    f"Bạn nhớ thắt chặt chi tiêu danh mục này nhé!"
                )
            elif cb.co_canh_bao:
                pct_chi = round(cb.ty_le * 100)
                canh_bao_str = (
                    f"\n\n⚠️ **LƯU Ý:** Hũ **\"{target_dm.ten_dm}\"** đã chạm ngưỡng an toàn "
                    f"(Đã chi **{cb.so_tien_da_chi:,.0f}đ** / Hạn mức **{cb.han_muc:,.0f}đ** - đạt {pct_chi}%). "
                    f"Hãy cân đối các bữa ăn/khoản chi tiếp theo nhé!"
                )
            elif cb.han_muc > 0:
                canh_bao_str = f"\n\n✨ Hũ **\"{target_dm.ten_dm}\"** vẫn trong hạn mức an toàn ({cb.so_tien_da_chi:,.0f}đ / {cb.han_muc:,.0f}đ)."

        so_du_vi = NganSachService.tinh_so_du_vi_chinh(db, ma_nd)
        type_label = "Chi tiêu" if loai_gd == "chi" else "Thu nhập"
        icon_sign = "💸 -" if loai_gd == "chi" else "💰 +"

        return (
            f"Đã ghi nhận giao dịch thành công cho bạn rồi nhé! ✅\n\n"
            f"📋 **Chi tiết giao dịch:**\n"
            f"• **Nội dung:** {clean_note}\n"
            f"• **Số tiền:** **{icon_sign}{amount:,.0f}đ**\n"
            f"• **Danh mục:** {target_dm.ten_dm}\n"
            f"• **Hình thức:** {type_label}\n"
            f"• **Thời gian:** {now.strftime('%H:%M - %d/%m/%Y')}\n\n"
            f"💳 **Số dư ví chính khả dụng:** **{so_du_vi:,.0f}đ**"
            f"{canh_bao_str}"
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

        # Tự động nhận diện lệnh giao tiếp tự nhiên và thêm giao dịch vào hệ thống (hỗ trợ đa lượt)
        thao_tac_res = AIService.xu_ly_giao_dich_tu_nhien(db, ma_nd, cau_hoi_clean, lich_su_chat=lich_su_chat)
        if thao_tac_res:
            return thao_tac_res

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
            "   - Nếu hỏi 'liệt kê chi tiết', 'danh sách danh mục': Hãy liệt kê ĐẦY ĐỦ tất cả các danh mục với số tiền và tỷ lệ % theo gạch đầu dòng rõ ràng, TUYỆT ĐỐI KHÔNG dùng thẻ HTML (<...>) và KHÔNG ĐƯỢC ngắt câu dở dang!\n"
            "   - Nếu hỏi về số dư / ví tiền: Nêu rõ số dư ví chính khả dụng và số tiền còn dư trong tháng.\n"
            "   - Nếu hỏi xin lời khuyên / có nên mua món gì: Dựa vào số dư ví chính, số tiền còn dư và mục tiêu tiết kiệm để tính toán và tư vấn thực tế, có căn cứ.\n"
            "   - QUY TẮC TỪ NGỮ GẦN GŨI: TUYỆT ĐỐI KHÔNG dùng từ ngữ học thuật sách vở, cứng nhắc như 'thặng dư', 'thặng dư tháng'. Hãy luôn dùng các từ ngữ tự nhiên, đời thường, gần gũi như 'tiền còn dư', 'tiền dư dả', 'khoản tiền dôi ra', 'tiết kiệm tích lũy được'!\n\n"
            "3. ĐỊNH DẠNG & PHONG CÁCH:\n"
            "   - Tiếng Việt tự nhiên, ấm áp, thông minh, tinh tế. Định dạng markdown rõ ràng (in đậm số liệu, emoji hợp lý, gạch đầu dòng gọn gàng).\n\n"
            "4. XỬ LÝ HỘI THOẠI ĐA LƯỢT & CÂU HỎI / TRẢ LỜI NGẮN (CỰC KỲ QUAN TRỌNG):\n"
            "   - Khi người dùng gửi câu ngắn như 'có', 'ok', 'được', 'ừ', 'đồng ý', 'yes', 'giúp mình', 'hỗ trợ mình', 'tiếp tục'...\n"
            "   - Tuyệt đối KHÔNG coi đây là tin nhắn gửi nhầm hoặc câu nói chưa hoàn chỉnh!\n"
            "   - Hãy đọc câu hỏi/gợi ý gần nhất của AI trong 'LỊCH SỬ TRÒ CHUYỆN GẦN ĐÂY' để thực hiện ngay hành động tiếp theo.\n"
            "   - Ví dụ: Nếu câu trước AI vừa hỏi 'Bạn có muốn mình hỗ trợ lập kế hoạch chi tiêu cho tháng 10 không?' và người dùng trả lời 'có' / 'ok' -> Hãy lập ngay một bản kế hoạch chi tiêu cụ thể, thông minh, chi tiết cho tháng 10 dựa trên dữ liệu thu chi thực tế của họ!\n\n"
            "5. QUY TẮC BẢO TOÀN DỮ LIỆU & TRÁNH NHẬN VƠ THỰC THI GIAO DỊCH:\n"
            "   - Mọi thao tác thêm/sửa/xóa giao dịch hoặc trích tiền đều do hệ thống backend tự động xử lý trực tiếp vào cơ sở dữ liệu.\n"
            "   - Bạn là Trí tuệ Nhân tạo tư vấn, TUYỆT ĐỐI KHÔNG tự nhận là 'mình đã ghi nhận', 'mình đã lưu giao dịch' nếu người dùng chưa cung cấp đủ số tiền hoặc câu hỏi mang tính trò chuyện.\n"
            "   - Nếu người dùng kể về một khoản chi tiêu nhưng chưa có số tiền (ví dụ: 'trưa nay tôi đi ăn cơm', 'vừa đi đổ xăng'), hãy hỏi lại họ số tiền một cách ngắn gọn, tự nhiên để hệ thống tiến hành ghi nhận.\n\n"
            f"DỮ LIỆU TÀI CHÍNH THỰC TẾ (Tháng {ctx['thang_hien_tai']}):\n"
            f"• Thu nhập: {tong_thu:,.0f}đ\n"
            f"• Tổng chi tiêu: {tong_chi:,.0f}đ\n"
            f"• Tiền còn dư trong tháng: {so_du:,.0f}đ | Số dư ví chính khả dụng: {so_du_vi_chinh:,.0f}đ\n"
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
