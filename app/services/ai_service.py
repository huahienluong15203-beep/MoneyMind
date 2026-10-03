import re
import json
import time
import httpx
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
from app.models.lich_su_ai import LichSuAI
from app.services.privacy_service import PrivacyService
from app.services.ngan_sach_service import NganSachService

# Danh sách các mô hình Gemini của Google siêu tốc và hoạt động ổn định nhất (< 1.5s)
AVAILABLE_GEMINI_MODELS = [
    "gemini-3.5-flash-lite",      # Bản thế hệ mới siêu nhẹ, phản hồi 0.8s - 1.2s, ổn định
    "gemini-flash-lite-latest",  # Alias chính thức của bản Flash-Lite mới nhất
    "gemini-3.5-flash",          # Bản Flash tiêu chuẩn, thông minh cao (~1.5s)
    "gemini-3.1-flash-lite",      # Dự phòng nhanh
]

# Client HTTP Keep-Alive dùng chung tái sử dụng kết nối SSL/TLS để triệt tiêu độ trễ bắt tay mạng
_ai_http_client: Optional[httpx.Client] = None

def _get_ai_http_client() -> httpx.Client:
    global _ai_http_client
    if _ai_http_client is None or _ai_http_client.is_closed:
        _ai_http_client = httpx.Client(
            timeout=httpx.Timeout(connect=2.5, read=7.0, write=2.5, pool=2.5),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20, keepalive_expiry=60.0),
            http2=False
        )
    return _ai_http_client


class AIService:
    @staticmethod
    def _call_gemini_with_timeout(prompt: str, timeout: float = 10.0) -> str:
        """
        Gọi Gemini REST API với mô hình thế hệ mới siêu tốc (Flash-Lite / Flash 3.5),
        kết hợp HTTP Keep-Alive Connection Pooling và chuyển đổi dự phòng tức thì.
        Tốc độ phản hồi đạt mức tối ưu (< 1.5 giây).
        """
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Dịch vụ AI Engine chưa được cấu hình API key. Vui lòng liên hệ quản trị viên."
            )

        start_time = time.time()
        client = _get_ai_http_client()
        last_exception = None

        # Mỗi model tối đa 3.5 giây để tránh treo lâu khi mạng nghẽn
        per_model_timeout = max(1.8, min(3.5, timeout / 2.0))

        for model_name in AVAILABLE_GEMINI_MODELS:
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                break

            rem_timeout = min(per_model_timeout, timeout - elapsed)
            if rem_timeout <= 0.5:
                break

            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.35,
                    "maxOutputTokens": 1024
                }
            }

            try:
                resp = client.post(url, json=payload, timeout=rem_timeout)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        if parts and "text" in parts[0]:
                            return parts[0]["text"]
                elif resp.status_code in (429, 503, 404, 500):
                    last_exception = Exception(f"HTTP {resp.status_code} on {model_name}")
                    continue
                else:
                    last_exception = Exception(f"HTTP {resp.status_code}: {resp.text[:100]}")
                    continue
            except httpx.TimeoutException as e:
                last_exception = e
                continue
            except Exception as e:
                last_exception = e
                continue

        # Nếu tất cả các model đều thất bại hoặc quá thời gian
        err_msg = str(last_exception) if last_exception else "timeout"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI Engine phản hồi quá thời gian cho phép. Chi tiết: {err_msg[:120]}"
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
    def _parse_vietnamese_datetime(t: str) -> datetime:
        """
        Trích xuất thời gian giao dịch thực tế từ ngôn ngữ tự nhiên:
        hôm qua, hôm kia, sáng nay, trưa nay, chiều nay, tối nay, tối qua...
        """
        now = datetime.now()
        target_date = now.date()
        if "hôm kia" in t:
            target_date = (now - timedelta(days=2)).date()
        elif any(w in t for w in ["hôm qua", "tối qua", "sáng qua", "trưa qua", "chiều qua"]):
            target_date = (now - timedelta(days=1)).date()
        elif "tuần trước" in t:
            target_date = (now - timedelta(days=7)).date()

        target_time = now.time()
        if any(w in t for w in ["sáng nay", "lúc sáng", "hồi sáng", "sáng qua", "ban sáng"]):
            target_time = datetime.strptime("08:30", "%H:%M").time()
        elif any(w in t for w in ["trưa nay", "lúc trưa", "hồi trưa", "trưa qua", "ban trưa"]):
            target_time = datetime.strptime("12:15", "%H:%M").time()
        elif any(w in t for w in ["chiều nay", "lúc chiều", "hồi chiều", "chiều qua", "ban chiều"]):
            target_time = datetime.strptime("15:30", "%H:%M").time()
        elif any(w in t for w in ["tối nay", "lúc tối", "hồi tối", "tối qua", "đêm qua", "ban tối"]):
            target_time = datetime.strptime("19:30", "%H:%M").time()

        return datetime.combine(target_date, target_time)

    @staticmethod
    def _lam_sach_mo_ta_giao_dich(raw: str, default_name: str = "Chi tiêu") -> str:
        """
        Làm sạch mô tả giao dịch thông minh:
        - Bóc tách triệt để các tiền tố thời gian ('lúc trưa', 'trưa nay', 'hôm qua', 'hồi sáng'...)
        - Loại bỏ chủ ngữ, từ đệm ('tôi', 'mình', 'vừa đi', 'mới đi'...)
        - Bóc tách đơn vị/lượng từ ('ăn xuất cơm gà' -> 'Cơm gà', 'uống ly trà chanh' -> 'Trà chanh', 'ăn suất cơm tấm' -> 'Cơm tấm')
        - Loại bỏ cụm số tiền ở giữa câu ('đổ 50k xăng' -> 'Đổ xăng') hoặc cuối câu ('hết 150k mới đúng' -> loại bỏ)
        - Dọn sạch ngoặc đơn, ngoặc kép, dấu câu và viết hoa chuẩn mực.
        """
        s = raw.strip()

        # Dọn dẹp dấu mở/đóng ngoặc, nháy, dấu câu ở hai đầu
        s = re.sub(r'^[(\[\{\"\',:\-\s]+', '', s)
        s = re.sub(r'[)\]\}\"\',:\-\s]+$', '', s)

        # 1. Hậu tố đính chính/cảm thán cuối câu
        s = re.sub(r'\s*(?:mới\s*đúng|mới\s*chuẩn|mới\s*phải|chứ|nhé|nha|ạ|nè|đó|đấy|nhá|ha)\s*$', '', s, flags=re.IGNORECASE)

        # 2. Xóa số tiền cuối câu: 'hết 150k', '150k', 'chi 150.000đ', 'giá 150k'...
        s = re.sub(r'\s*(?:hết|mất|tốn|chi\s*hết|tiêu\s*hết|giá|trả)?\s*[\d.,]+\s*(?:triệu|nghìn|ngàn|trăm|củ|lít|vnd|đồng|dong|chục|tr|k|đ)(?:\s*đồng|\s*đ)?\s*$', '', s, flags=re.IGNORECASE)
        s = re.sub(r'\s*(?:hết|mất|tốn|chi\s*hết|tiêu\s*hết|giá|trả)\s*$', '', s, flags=re.IGNORECASE)

        # 3. Xóa số tiền ở giữa câu (không nuốt chữ tiền điện/tiền nước/tiền nhà...)
        s = re.sub(r'\b[\d.,]+\s*(?:triệu|nghìn|ngàn|trăm|củ|lít|vnd|đồng|dong|chục|tr|k|đ)\s*(?:tiền\s+(?!(?:điện|nước|mạng|nhà|phòng|xăng|học|thuốc|ăn|xe)\b))?', '', s, flags=re.IGNORECASE)

        # 4. Tiền tố hội thoại, thời gian, chủ ngữ (lặp lại và dọn dấu ngoặc ở mỗi vòng)
        for _ in range(8):
            s = re.sub(r'^[(\[\{\"\',:\-\s]+', '', s)
            s = re.sub(r'[)\]\}\"\',:\-\s]+$', '', s)
            s = re.sub(r'^(?:à|ơ|ủa|ơ\s*kìa|ấy|thôi\s*chết|ôi|ui)\s+[,:\-]?\s*', '', s, flags=re.IGNORECASE)
            s = re.sub(r'^(?:tôi\s+nhầm|mình\s+nhầm|em\s+nhầm|anh\s+nhầm|lộn(?:\s*rồi|\s*nè|\s*nhé|\s*quá)?|nhầm(?:\s*rồi|\s*nè|\s*nhé|\s*quá)?|quên(?:\s*mất)?)\s*[,:\-]?\s*', '', s, flags=re.IGNORECASE)
            s = re.sub(r'^(?:nói\s*lộn|nói\s*nhầm|ghi\s*lộn|ghi\s*nhầm|đính\s*chính(?:\s*lại)?|sửa\s*lại|sửa|đổi\s*lại|đổi|chỉnh\s*lại|chỉnh)(?:\s+rồi)?(?:\s+thành|\s+sang|\s+về)?\s*[,:\-]?\s*', '', s, flags=re.IGNORECASE)
            s = re.sub(r'^(?:không\s*phải\s+[^,;]+?(?:mà\s*là|là))\s*[,:\-]?\s*', '', s, flags=re.IGNORECASE)
            s = re.sub(r'^(?:thực\s*ra|thật\s*ra|đúng\s*ra|đúng\s*hơn\s*là|ý\s*là|ý\s*tôi\s*là|ý\s*mình\s*là|không\s*phải|chứ\s*không\s*phải)(?:\s+là)?\s*[,:\-]?\s*', '', s, flags=re.IGNORECASE)
            s = re.sub(r'^(?:hãy\s+)?(?:báo(?:\s*cáo)?|ghi\s*nhận(?:\s*giúp)?|thêm\s*(?:giao\s*dịch)?|ghi\s*sổ|lưu\s*(?:giao\s*dịch)?|tạo\s*(?:giao\s*dịch)?|nhập\s*(?:giúp)?|lưu|thêm|ghi|nhập|note)\s+', '', s, flags=re.IGNORECASE)
            s = re.sub(r'^(?:tôi|mình|em|anh|chị|bạn|chúng\s*tôi|hai\s*đứa|tụi\s*mình)\s+', '', s, flags=re.IGNORECASE)
            s = re.sub(r'^(?:hôm\s*nay|hôm\s*qua|hôm\s*kia|tuần\s*này|tuần\s*trước|tháng\s*này)\s+[,:\-]?\s*', '', s, flags=re.IGNORECASE)
            s = re.sub(r'^(?:sáng\s*nay|trưa\s*nay|chiều\s*nay|tối\s*nay|tối\s*qua|đêm\s*qua|sáng\s*qua|trưa\s*qua|chiều\s*qua)\s+[,:\-]?\s*', '', s, flags=re.IGNORECASE)
            s = re.sub(r'^(?:lúc\s*sáng|lúc\s*trưa|lúc\s*chiều|lúc\s*tối|hồi\s*sáng|hồi\s*trưa|hồi\s*chiều|hồi\s*tối|ban\s*sáng|ban\s*trưa|ban\s*chiều|ban\s*tối)\s+[,:\-]?\s*', '', s, flags=re.IGNORECASE)
            s = re.sub(r'^(?:khi\s*nãy|lúc\s*nãy|vừa\s*nãy|mới\s*nãy|ban\s*nãy|vừa\s*rồi|mới\s*rồi)\s+[,:\-]?\s*', '', s, flags=re.IGNORECASE)
            s = re.sub(r'^(?:rồi|sau\s*đó|xong|rồi\s*thì|tiện\s*thể|nhân\s*tiện|tiện\s*đường|ghé\s*qua|tạt\s*qua|tạt\s*vào|ghé|tạt)\s+', '', s, flags=re.IGNORECASE)
            s = re.sub(r'^(?:vừa\s*mới|vừa\s*đi|mới\s*đi|vừa|mới|có|đã|lại|cũng)\s+', '', s, flags=re.IGNORECASE)
            s = re.sub(r'^(?:thành|sang|về|là)\s+', '', s, flags=re.IGNORECASE)

            # Rút gọn ăn/uống/mua kèm lượng từ/đơn vị: suất/xuất/phần/đĩa/ly/cốc/bát/tô...
            s = re.sub(r'^(?:đi\s+)?(?:ăn|uống|mua|gọi|dùng)\s+(?:(?:1|2|3|4|5|một|hai|ba|bốn|năm|mấy|vài)\s+)?(?:suất|xuất|phần|đĩa|dĩa|bát|tô|chén|ly|cốc|chai|lon|bịch|gói|hộp|ổ|que)\s+', '', s, flags=re.IGNORECASE)
            s = re.sub(r'^(?:(?:1|2|3|4|5|một|hai|ba|bốn|năm|mấy|vài)\s+)?(?:suất|xuất|phần|đĩa|dĩa|bát|tô|chén|ly|cốc|chai|lon|bịch|gói|hộp|ổ|que)\s+', '', s, flags=re.IGNORECASE)
            s = re.sub(r'^đi\s+(ăn|uống|mua|nhậu|chơi)\b', r'\1', s, flags=re.IGNORECASE)
            s = re.sub(r'^(?:mua|uống)\s+(trà\s*chanh|trà\s*sữa|cafe|cà\s*phê|nước\s*ngọt|nước\s*suối|bánh\s*mì|bánh|kẹo|thuốc)\b', r'\1', s, flags=re.IGNORECASE)

        # 5. Dọn dẹp tiền tố chi tiền
        s = re.sub(r'^(?:chi|tiêu|trả|nộp|chuyển)\s+(?:cho|để|vào)?\s*', '', s, flags=re.IGNORECASE)
        s = re.sub(r'^tiền\s+(?!(?:điện|nước|mạng|nhà|phòng|xăng|học|thuốc|ăn|xe)\b)', '', s, flags=re.IGNORECASE)
        s = re.sub(r'^nhận\s+(lương|thưởng)\b', r'\1', s, flags=re.IGNORECASE)

        s = re.sub(r'^[(\[\{\"\',:\-\s]+', '', s)
        s = re.sub(r'[)\]\}\"\',:\-\s]+$', '', s).strip()

        if not s or len(s) < 2:
            return default_name
        return s[0].upper() + s[1:]

    @staticmethod
    def _xac_dinh_danh_muc(db: Session, ma_nd: int, text: str, loai_gd: str) -> DanhMuc:
        """
        Nhận diện danh mục tương ứng dựa trên từ khóa ngữ nghĩa và đối chiếu với danh mục người dùng.
        Tự động tạo mới nếu danh mục chuẩn chưa có trong tài khoản người dùng.
        """
        category_defs = [
            ("Đi lại", ["đổ xăng", "xăng xe", "xăng", "grab", "be", "gojek", "taxi", "xe ôm", "vé xe", "vé tàu", "vé máy bay", "gửi xe", "sửa xe", "rửa xe", "bảo dưỡng", "thay nhớt", "xăm lốp", "xe buýt", "bus", "vé cầu đường"], "car", "#f59e0b"),
            ("Ăn uống", ["bánh mì", "cơm gà", "cơm tấm", "cơm", "phở", "bún", "mỳ", "miến", "hủ tiếu", "cafe", "cà phê", "trà sữa", "trà chanh", "trà đá", "nước mía", "sinh tố", "trà", "nước ngọt", "nhậu", "lẩu", "nướng", "bbq", "pizza", "kfc", "bánh", "kẹo", "ăn vặt", "hoa quả", "trái cây", "chợ", "siêu thị", "ăn trưa", "ăn sáng", "ăn tối", "đồ ăn", "nấu ăn", "quán ăn", "ăn uống", "buffet", "kem", "chè", "xôi", "bò kho", "hải sản", "ăn ốc", "ốc", "ăn", "uống"], "utensils", "#ef4444"),
            ("Mua sắm", ["quần áo", "áo sơ mi", "áo khoác", "áo thun", "áo", "quần", "giày", "dép", "túi xách", "túi", "ví", "mỹ phẩm", "son", "shopee", "lazada", "tiki", "tiktok shop", "đồng hồ", "điện thoại", "tai nghe", "laptop", "bàn phím", "chuột", "sách", "vở", "bút", "mua"], "shopping-bag", "#8b5cf6"),
            ("Hóa đơn", ["tiền điện", "tiền nước", "tiền mạng", "tiền internet", "wifi", "tiền nhà", "tiền phòng", "tiền trọ", "tiền cọc", "phí chung cư", "nạp điện thoại", "tiền điện thoại", "điện", "nước", "tiền rác", "hóa đơn"], "file-text", "#06b6d4"),
            ("Giải trí", ["xem phim", "rạp chiếu phim", "cinema", "nạp game", "game", "karaoke", "du lịch", "dã ngoại", "camping", "bar", "pub", "bida", "bowling", "đi chơi", "netflix", "spotify", "uống bia"], "film", "#ec4899"),
            ("Sức khỏe", ["khám bệnh", "thuốc men", "thuốc", "bệnh viện", "bác sĩ", "nha khoa", "răng", "tập gym", "gym", "yoga", "fitness", "tiền thuốc"], "heart", "#10b981"),
            ("Tiết kiệm", ["hũ tiết kiệm", "tiết kiệm", "tích lũy", "bỏ lợn", "bỏ heo", "vào hũ"], "piggy-bank", "#10b981"),
            ("Tiền lương", ["nhận lương", "tiền lương", "tiền thưởng", "hoa hồng", "lương", "thưởng", "thu nhập"], "dollar-sign", "#22c55e")
        ]

        t_clean = text.lower()
        matched_tuple = None
        if loai_gd == "thu":
            matched_tuple = category_defs[7]  # Tiền lương
        else:
            for cat_def in category_defs:
                cname, kw_list, icon, col = cat_def
                sorted_kws = sorted(kw_list, key=len, reverse=True)
                for kw in sorted_kws:
                    if AIService._match_keyword(kw, t_clean):
                        matched_tuple = cat_def
                        break
                if matched_tuple:
                    break

        user_dms = db.query(DanhMuc).filter(DanhMuc.ma_nd == ma_nd).all()
        target_dm = None

        if matched_tuple:
            cname, _, icon, col = matched_tuple
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

        return target_dm

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

        return (
            f"⚠️ **XÁC NHẬN XÓA HŨ TIẾT KIỆM**\n\n"
            f"Bạn có chắc chắn muốn xóa hũ tiết kiệm này không?\n"
            f"• **Tên hũ:** {goal_title}\n"
            f"• **Mục tiêu:** **{matched_goal.so_tien_muc_tieu:,.0f}đ**\n"
            f"• **Đã tích lũy:** **{refund_amt:,.0f}đ** *(khoản này sẽ hoàn lại vào ví chính)*\n"
            f"*(Mã hũ: #{matched_goal.ma_mt})*\n\n"
            f"👉 Hãy trả lời **'Đồng ý'** (hoặc **'Xác nhận'**, **'Có'**) để tiến hành xóa, hoặc **'Hủy'** để giữ lại nhé!"
        )

    @staticmethod
    def _thuc_thi_xoa_hu_tiet_kiem(db: Session, ma_nd: int, matched_goal: MucTieuTietKiem) -> str:
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
        else:
            m_month = re.search(r'trong\s+(\d+)\s+tháng', raw, re.IGNORECASE)
            if m_month:
                try:
                    num_m = int(m_month.group(1))
                    calc_d = datetime.now() + timedelta(days=num_m * 30)
                    deadline = calc_d.date()
                    deadline_str = f"{deadline.day:02d}/{deadline.month:02d}/{deadline.year}"
                except Exception:
                    pass

        clean = raw
        clean = re.sub(r'^(?:tôi\s+|mình\s+)?(?:muốn|cần|định|dự định|lập kế hoạch|kế hoạch)?\s*(?:tiết kiệm|dành dụm|tích lũy|tạo hũ|lập hũ|thêm hũ|đặt mục tiêu|tạo mục tiêu|lập mục tiêu)?\s*(?:tiết kiệm)?\s*', '', clean, flags=re.IGNORECASE)
        clean = re.sub(r'trong\s+\d+\s+tháng(?:\s+tới)?', '', clean, flags=re.IGNORECASE)
        clean = re.sub(r'(?:hạn\s*chót|hạn|trước\s*ngày|đến\s*ngày)?\s*\d{1,2}[/-]\d{1,2}[/-]\d{4}', '', clean, flags=re.IGNORECASE)
        clean = re.sub(r'\d+[\.,]?\d*\s*(?:triệu|nghìn|ngàn|trăm|củ|lít|vnd|tr|k|đ)', '', clean, flags=re.IGNORECASE)
        clean = re.sub(r'\b\d{4,}\b', '', clean)
        clean = re.sub(r'^(?:để|cho việc)\s+', '', clean, flags=re.IGNORECASE)
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

        return (
            f"⚠️ **XÁC NHẬN XÓA DANH MỤC**\n\n"
            f"Bạn có chắc chắn muốn xóa danh mục này không?\n"
            f"• **Tên danh mục:** {cat_name}\n"
            f"• **Loại:** {'Chi tiêu' if cat_type == 'chi' else 'Thu nhập'}\n"
            f"• **Hạn mức hiện tại:** **{cat_limit:,.0f}đ**\n"
            f"*(Mã danh mục: #{matched_cat.ma_dm})*\n\n"
            f"👉 Hãy trả lời **'Đồng ý'** (hoặc **'Xác nhận'**, **'Có'**) để tiến hành xóa, hoặc **'Hủy'** để giữ lại nhé!"
        )

    @staticmethod
    def _thuc_thi_xoa_danh_muc(db: Session, ma_nd: int, matched_cat: DanhMuc) -> str:
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
    def _xu_ly_xem_hu_tiet_kiem(db: Session, ma_nd: int, t: str) -> Optional[str]:
        goals = db.query(MucTieuTietKiem).filter(MucTieuTietKiem.ma_nd == ma_nd).all()
        if not goals:
            return (
                "Hiện tại bạn chưa tạo hũ tiết kiệm nào. 🏺\n\n"
                "Bạn có thể bắt đầu tích lũy cho ước mơ bằng cách nói: "
                "*'Tạo hũ tiết kiệm du lịch Đà Nẵng 5 triệu'* hoặc *'Tạo mục tiêu mua laptop 20 triệu'* nhé! ✨"
            )

        so_du_vi = NganSachService.tinh_so_du_vi_chinh(db, ma_nd)
        lines = []
        for g in goals:
            pct = round((g.so_tien_hien_tai / g.so_tien_muc_tieu) * 100) if g.so_tien_muc_tieu > 0 else 0
            con_thieu = max(0.0, g.so_tien_muc_tieu - g.so_tien_hien_tai)
            status_badge = "✅ Đã hoàn thành" if pct >= 100 else f"⏳ Đạt {pct}%"
            lines.append(
                f"• 🎯 **{g.ten_muc_tieu}**: **{g.so_tien_hien_tai:,.0f}đ** / {g.so_tien_muc_tieu:,.0f}đ "
                f"({status_badge}) — Còn thiếu **{con_thieu:,.0f}đ**"
            )

        return (
            f"🏺 **Danh Sách & Tiến Độ Hũ Tiết Kiệm Của Bạn:**\n\n" +
            "\n".join(lines) +
            f"\n\n💳 **Số dư ví chính khả dụng:** **{so_du_vi:,.0f}đ**\n"
            f"💡 Bạn có thể nộp tiền vào hũ bằng cách nói: *'Nộp 500k vào hũ {goals[0].ten_muc_tieu}'* bất kỳ lúc nào nhé!"
        )

    @staticmethod
    def _xu_ly_xem_ngan_sach_danh_muc(db: Session, ma_nd: int, t: str) -> Optional[str]:
        now = datetime.now()
        start_this = datetime(now.year, now.month, 1)
        end_this = datetime(now.year + 1, 1, 1) if now.month == 12 else datetime(now.year, now.month + 1, 1)

        dms = db.query(DanhMuc).filter(DanhMuc.ma_nd == ma_nd, DanhMuc.loai_dm == "chi").all()
        if not dms:
            return "Bạn chưa có danh mục chi tiêu nào trong hệ thống."

        txs = db.query(GiaoDich).filter(
            GiaoDich.ma_nd == ma_nd,
            GiaoDich.loai_gd == "chi",
            GiaoDich.ngay_gd >= start_this,
            GiaoDich.ngay_gd < end_this
        ).all()

        spent_map = {}
        for tx in txs:
            if tx.ma_dm and not AIService._is_excluded_chi(tx):
                spent_map[tx.ma_dm] = spent_map.get(tx.ma_dm, 0.0) + tx.so_tien

        lines = []
        for dm in dms:
            spent = spent_map.get(dm.ma_dm, 0.0)
            limit = dm.han_muc or 0.0
            if limit > 0:
                pct = round((spent / limit) * 100)
                status = "🚨 Vượt mức" if spent > limit else ("⚠️ Chạm ngưỡng" if pct >= 80 else "✅ An toàn")
                lines.append(f"• **{dm.ten_dm}**: Đã chi **{spent:,.0f}đ** / Hạn mức **{limit:,.0f}đ** ({pct}% - {status})")
            else:
                lines.append(f"• **{dm.ten_dm}**: Đã chi **{spent:,.0f}đ** *(Chưa đặt hạn mức)*")

        return (
            f"📊 **Ngân Sách & Chi Tiêu Các Hũ Tháng {now.month}/{now.year}:**\n\n" +
            "\n".join(lines) +
            f"\n\n💡 Bạn có thể đặt hoặc điều chỉnh hạn mức hũ bằng cách nói: *'Đặt hạn mức ăn uống là 3 triệu'* nhé!"
        )

    @staticmethod
    def _xu_ly_xoa_giao_dich(db: Session, ma_nd: int, t: str) -> Optional[str]:
        tx = None
        # Ưu tiên tìm giao dịch gần nhất nếu người dùng dùng từ ngữ chỉ ngữ cảnh gần
        if any(w in t for w in ["gần nhất", "vừa rồi", "vừa thêm", "mới nhất", "vừa tạo", "vừa nhập", "vừa ghi", "cái vừa", "vừa xong", "nó đi", "bỏ đi", "hủy đi"]):
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
        date_str = tx.ngay_gd.strftime('%H:%M - %d/%m/%Y') if tx.ngay_gd else "N/A"

        return (
            f"⚠️ **XÁC NHẬN XÓA GIAO DỊCH**\n\n"
            f"Bạn có chắc chắn muốn xóa giao dịch này không?\n"
            f"• **Nội dung:** {info_note}\n"
            f"• **Số tiền:** **{info_amt:,.0f}đ** ({'Chi tiêu' if info_loai == 'chi' else 'Thu nhập'})\n"
            f"• **Thời gian:** {date_str}\n"
            f"*(Mã giao dịch: #{tx.ma_gd})*\n\n"
            f"👉 Hãy trả lời **'Đồng ý'** (hoặc **'Xác nhận'**, **'Có'**) để tiến hành xóa, hoặc **'Hủy'** để giữ lại nhé!"
        )

    @staticmethod
    def _thuc_thi_xoa_giao_dich(db: Session, ma_nd: int, tx: GiaoDich) -> str:
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
        recent_txs = db.query(GiaoDich).filter(GiaoDich.ma_nd == ma_nd).order_by(GiaoDich.ma_gd.desc()).limit(30).all()
        if not recent_txs:
            return "Không tìm thấy giao dịch nào gần đây để chỉnh sửa."

        # 1. Tìm giao dịch mà người dùng nhắc tới để sửa (ví dụ: 'không phải cơm gà...', 'khoản cơm gà...')
        for item in recent_txs:
            gc = (item.ghi_chu or "").lower()
            words = [w for w in gc.split() if len(w) > 2]
            if words and any(w in t for w in words):
                tx = item
                break

        # Nếu không nêu đích danh món cũ, lấy giao dịch gần nhất vừa thao tác
        if not tx:
            tx = recent_txs[0]

        old_note = tx.ghi_chu or ""
        old_amt = tx.so_tien
        old_dm = db.query(DanhMuc).filter(DanhMuc.ma_dm == tx.ma_dm).first()
        old_cname = old_dm.ten_dm if old_dm else "Khác"
        changed = []

        # Trích xuất số tiền mới
        new_amt = AIService._parse_vietnamese_amount(t)
        if new_amt > 0 and new_amt != old_amt:
            tx.so_tien = new_amt
            changed.append(f"Số tiền: **{old_amt:,.0f}đ** ➔ **{new_amt:,.0f}đ**")
        elif new_amt > 0 and new_amt == old_amt:
            # Số tiền được nhắc lại để xác nhận (vd: 'ăn lẩu hết 150k mới đúng')
            pass

        # Trích xuất nội dung mới (làm sạch thông minh)
        cand_note = AIService._lam_sach_mo_ta_giao_dich(raw, "")
        ignore_notes = ["chi tiêu", "thu nhập", "giao dịch", "khoản chi", "gần nhất", "vừa rồi", "vừa thêm"]
        if cand_note and cand_note.lower() not in ignore_notes and cand_note.lower() != old_note.lower():
            tx.ghi_chu = cand_note
            changed.append(f"Nội dung: *\"{old_note}\"* ➔ **\"{cand_note}\"**")

            # Tự động cập nhật lại danh mục phù hợp với món mới nếu thay đổi tính chất
            new_dm = AIService._xac_dinh_danh_muc(db, ma_nd, cand_note, tx.loai_gd)
            if new_dm and new_dm.ma_dm != tx.ma_dm:
                tx.ma_dm = new_dm.ma_dm
                changed.append(f"Danh mục: {old_cname} ➔ **{new_dm.ten_dm}**")

        # Cập nhật thời gian nếu có từ khóa thời điểm (vd: 'trưa nay', 'sáng nay', 'hôm qua'...)
        if any(w in t for w in ["trưa nay", "lúc trưa", "hồi trưa", "sáng nay", "lúc sáng", "hồi sáng", "chiều nay", "tối nay", "hôm qua", "tối qua"]):
            tx.ngay_gd = AIService._parse_vietnamese_datetime(t)

        if not changed:
            if new_amt > 0:
                tx.so_tien = new_amt
                changed.append(f"Số tiền: **{old_amt:,.0f}đ** ➔ **{new_amt:,.0f}đ**")
            else:
                return (
                    f"Giao dịch gần nhất của bạn là **{old_note}** (**{old_amt:,.0f}đ**). "
                    f"Bạn có thể nói: *'sửa giao dịch thành 50k'* hoặc *'đổi thành ăn lẩu 150k'* để mình cập nhật nhé!"
                )

        db.commit()
        db.refresh(tx)

        if tx.loai_gd == "chi" and tx.ma_dm:
            NganSachService.kiem_tra_ngan_sach(db=db, ma_nd=ma_nd, ma_dm=tx.ma_dm, ngay_gd=tx.ngay_gd)

        so_du_vi = NganSachService.tinh_so_du_vi_chinh(db, ma_nd)
        cur_dm = db.query(DanhMuc).filter(DanhMuc.ma_dm == tx.ma_dm).first()
        cur_cname = cur_dm.ten_dm if cur_dm else "Chi tiêu"
        icon_sign = "💸 -" if tx.loai_gd == "chi" else "💰 +"

        return (
            f"Dạ mình hiểu rồi, không sao cả! Đã cập nhật giao dịch thành công! Mình đã sửa lại ngay giao dịch cho bạn rồi nhé: ✏️\n\n"
            f"📋 **Giao dịch sau khi đính chính:**\n"
            f"• **Nội dung:** {tx.ghi_chu}\n"
            f"• **Số tiền:** **{icon_sign}{tx.so_tien:,.0f}đ**\n"
            f"• **Danh mục:** {cur_cname}\n"
            f"• **Thời gian:** {tx.ngay_gd.strftime('%H:%M - %d/%m/%Y')}\n\n"
            f"💳 **Số dư ví chính khả dụng:** **{so_du_vi:,.0f}đ**\n\n"
            f"*(Chi tiết thay đổi: {', '.join(changed)})*"
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

        # Tra cứu theo tên món / từ khóa cụ thể trong ghi chú (ví dụ: 'tìm trà chanh', 'khoản cơm gà', 'lẩu')
        keywords_ignore = {
            "tìm", "tra", "cứu", "tra cứu", "xem", "giao", "dịch", "giao dịch", "khoản", "chi",
            "tiêu", "khoản chi", "các", "hôm", "nay", "hôm nay", "qua", "hôm qua", "tháng", "này",
            "tháng này", "nhiều", "nhất", "lớn", "bé", "nhỏ", "tôi", "mình", "ta", "đã", "những",
            "gì", "nào", "sao", "thế", "hết", "bao", "nhiêu", "bao nhiêu", "vừa", "rồi", "lại",
            "cho", "biết", "danh", "sách", "lịch", "sử", "lịch sử", "nhật", "ký", "tiền"
        }
        search_kw = None
        m_find = re.search(r'(?:tìm|tra cứu|khoản|món)\s+([a-zA-Z0-9_à-ỹÀ-Ỹ\s]{2,20})', t)
        if m_find:
            cand = m_find.group(1).strip()
            cand_words = [w for w in cand.split() if w not in keywords_ignore]
            if cand_words:
                search_kw = " ".join(cand_words[:3])

        if search_kw and not matched_c:
            q = q.filter(GiaoDich.ghi_chu.ilike(f"%{search_kw}%"))
            title_suffix += f" từ khóa '{search_kw}'"

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
    def _thuc_thi_thiet_lap_ngan_sach(db: Session, ma_nd: int, category_allocations: List[Tuple[Any, float]]) -> str:
        """
        Thực thi thiết lập / cập nhật hạn mức ngân sách trực tiếp vào cơ sở dữ liệu
        cho một hoặc nhiều danh mục chi tiêu trong tháng hiện tại.
        Kiểm tra số dư ví chính, kiểm tra số tiền đã chi thực tế, tạo bản ghi NganSach
        và thông báo hệ thống thời gian thực.
        """
        if not category_allocations:
            return "Không tìm thấy danh mục chi tiêu phù hợp để thiết lập hạn mức."

        now_dt = datetime.now()
        now_ym = now_dt.strftime("%Y-%m")
        start_this = datetime(now_dt.year, now_dt.month, 1)
        end_this = datetime(now_dt.year + 1, 1, 1) if now_dt.month == 12 else datetime(now_dt.year, now_dt.month + 1, 1)

        # 1. Kiểm tra từng danh mục xem hạn mức mới có nhỏ hơn số tiền đã chi tháng này không
        for cat, new_limit in category_allocations:
            txs = db.query(GiaoDich).filter(
                GiaoDich.ma_nd == ma_nd,
                GiaoDich.ma_dm == cat.ma_dm,
                GiaoDich.loai_gd == "chi",
                GiaoDich.ngay_gd >= start_this,
                GiaoDich.ngay_gd < end_this
            ).all()
            spent = sum(float(item.so_tien or 0.0) for item in txs)
            if new_limit < spent:
                return (
                    f"Dạ hạn mức mới (**{new_limit:,.0f}đ**) cho hũ **'{cat.ten_dm}'** không thể nhỏ hơn "
                    f"số tiền bạn đã chi tiêu tháng này trong hũ này (**{spent:,.0f}đ**) nhé! 😊\n\n"
                    f"Bạn vui lòng đặt hạn mức tối thiểu bằng {spent:,.0f}đ ạ."
                )

        # 2. Tính toán số tiền cấp mới và kiểm tra số dư ví chính khả dụng
        total_diff = 0.0
        diff_map = {}
        for cat, new_limit in category_allocations:
            ns = db.query(NganSach).filter(
                NganSach.ma_nd == ma_nd,
                NganSach.ma_dm == cat.ma_dm,
                NganSach.thang_nam == now_ym
            ).first()
            old_limit = float(ns.han_muc) if (ns and ns.han_muc is not None) else 0.0
            so_du = float(ns.so_du_chuyen_sang or 0.0) if ns else 0.0
            old_allocated = max(0.0, old_limit - so_du)
            new_allocated = max(0.0, new_limit - so_du)
            diff = new_allocated - old_allocated
            diff_map[cat.ma_dm] = (diff, new_allocated)
            if diff > 0:
                total_diff += diff

        current_balance = NganSachService.tinh_so_du_vi_chinh(db, ma_nd)
        if current_balance > 0 and total_diff > current_balance:
            return (
                f"Dạ số dư ví chính khả dụng hiện tại (**{max(0.0, current_balance):,.0f}đ**) không đủ để trích cấp thêm "
                f"tổng cộng **{total_diff:,.0f}đ** cho các hũ ngân sách này ạ! 💳\n\n"
                f"Bạn có thể nạp thêm thu nhập hoặc cân đối lại mức ngân sách vừa phải hơn nhé! 😊"
            )

        # 3. Thực thi cập nhật cơ sở dữ liệu
        lines = []
        total_budget = 0.0
        for cat, new_limit in category_allocations:
            txs = db.query(GiaoDich).filter(
                GiaoDich.ma_nd == ma_nd,
                GiaoDich.ma_dm == cat.ma_dm,
                GiaoDich.loai_gd == "chi",
                GiaoDich.ngay_gd >= start_this,
                GiaoDich.ngay_gd < end_this
            ).all()
            spent = sum(float(item.so_tien or 0.0) for item in txs)

            diff, new_allocated = diff_map[cat.ma_dm]
            cat.han_muc = new_limit

            ns = db.query(NganSach).filter(
                NganSach.ma_nd == ma_nd,
                NganSach.ma_dm == cat.ma_dm,
                NganSach.thang_nam == now_ym
            ).first()

            if ns:
                ns.han_muc = new_limit
                ns.han_muc_cap_moi = new_allocated
                ns.so_tien_da_chi = spent
            else:
                ns = NganSach(
                    ma_nd=ma_nd,
                    ma_dm=cat.ma_dm,
                    thang_nam=now_ym,
                    han_muc=new_limit,
                    han_muc_cap_moi=new_allocated,
                    so_du_chuyen_sang=0.0,
                    so_tien_da_chi=spent
                )
                db.add(ns)

            con_lai = max(0.0, new_limit - spent)
            icon = "🍲" if "ăn" in cat.ten_dm.lower() else ("🏍️" if "đi" in cat.ten_dm.lower() else ("🛍️" if "mua" in cat.ten_dm.lower() else "🏺"))
            lines.append(f"• {icon} **{cat.ten_dm}:** **{new_limit:,.0f}đ** *(Còn lại: {con_lai:,.0f}đ)*")
            total_budget += new_limit

        db.commit()

        for cat, _ in category_allocations:
            db.refresh(cat)

        new_wallet_bal = NganSachService.tinh_so_du_vi_chinh(db, ma_nd)

        # Tạo thông báo hệ thống (tránh tạo trùng lặp liên tục)
        title_tb = f"🏺 Đã Thiết Lập Hạn Mức Ngân Sách Tháng {now_dt.month}/{now_dt.year}"
        existing_tb = db.query(ThongBao).filter(
            ThongBao.ma_nd == ma_nd,
            ThongBao.tieu_de == title_tb,
            ThongBao.ngay_tao >= datetime(now_dt.year, now_dt.month, now_dt.day, 0, 0, 0)
        ).first()
        if existing_tb:
            existing_tb.noi_dung = f"Bạn đã thiết lập hạn mức cho {len(category_allocations)} hũ chi tiêu với tổng ngân sách {total_budget:,.0f}đ."
            existing_tb.ngay_tao = now_dt
            existing_tb.da_xem = False
        else:
            db.add(ThongBao(
                ma_nd=ma_nd,
                tieu_de=title_tb,
                noi_dung=f"Bạn đã thiết lập hạn mức cho {len(category_allocations)} hũ chi tiêu với tổng ngân sách {total_budget:,.0f}đ.",
                da_xem=False,
                ngay_tao=now_dt
            ))
        db.commit()

        if len(category_allocations) == 1:
            cat, new_limit = category_allocations[0]
            txs = db.query(GiaoDich).filter(
                GiaoDich.ma_nd == ma_nd,
                GiaoDich.ma_dm == cat.ma_dm,
                GiaoDich.loai_gd == "chi",
                GiaoDich.ngay_gd >= start_this,
                GiaoDich.ngay_gd < end_this
            ).all()
            spent = sum(float(item.so_tien or 0.0) for item in txs)
            pct = round((spent / new_limit) * 100) if new_limit > 0 else 0
            con_lai = max(0.0, new_limit - spent)
            return (
                f"Đã điều chỉnh hạn mức ngân sách thành công! 🏺\n\n"
                f"📋 **Thông tin hũ chi tiêu sau điều chỉnh:**\n"
                f"• **Hũ ngân sách:** {cat.ten_dm}\n"
                f"• **Hạn mức mới:** **{new_limit:,.0f}đ**\n"
                f"• **Đã chi tiêu tháng này:** **{spent:,.0f}đ** ({pct}%)\n"
                f"• **Hạn mức còn lại:** **{con_lai:,.0f}đ**\n\n"
                f"Hạn mức mới đã được áp dụng trực tiếp vào hệ thống quản lý ngân sách tháng này! 💡"
            )

        details_str = "\n".join(lines)
        return (
            f"Tuyệt vời luôn! 🎯 Mình đã thiết lập ngay hạn mức ngân sách trực tiếp vào hệ thống cho bạn rồi nhé:\n\n"
            f"{details_str}\n\n"
            f"📊 **Tổng ngân sách đã cấp:** **{total_budget:,.0f}đ**\n"
            f"💳 **Số dư ví chính khả dụng:** **{new_wallet_bal:,.0f}đ**\n\n"
            f"✨ Hạn mức mới đã hiển thị trực tiếp trên giao diện Dashboard. Mình sẽ đồng hành theo dõi và cảnh báo chi tiêu thông minh cùng bạn nhé! 🚀"
        )

    @staticmethod
    def _xu_ly_phan_bo_ngan_sach_tu_nhien(db: Session, ma_nd: int, t: str, default_amount: float, context_msg: str = "") -> Optional[str]:
        """
        Tự động phân bổ ngân sách / hạn mức chi tiêu cho các danh mục (hũ) từ ngôn ngữ tự nhiên.
        Hỗ trợ:
        - Phân bổ đều cho các danh mục phổ biến / tất cả danh mục chi tiêu (vd: 'cấp cho mỗi danh mục 1tr5').
        - Phân bổ cụ thể từng danh mục (vd: 'ăn uống 2tr, đi lại 1tr5, mua sắm 1tr').
        - Hội thoại đa lượt: xác nhận sau khi AI gợi ý phân bổ ngân sách.
        - Tự động tạo danh mục nếu người dùng yêu cầu hũ phổ biến chưa có (vd: Giải trí).
        """
        combined_text = f"{context_msg} {t}".lower()

        # Danh sách danh mục chi tiêu hiện có của người dùng (loại trừ Tiết kiệm)
        user_dms = db.query(DanhMuc).filter(
            DanhMuc.ma_nd == ma_nd,
            DanhMuc.loai_dm == "chi",
            DanhMuc.ten_dm != "Tiết kiệm"
        ).all()
        dm_map = {dm.ten_dm.lower(): dm for dm in user_dms}

        popular_defs = [
            ("Ăn uống", "utensils", "#f97316"),
            ("Đi lại", "car", "#0ea5e9"),
            ("Mua sắm", "shopping-bag", "#ec4899"),
            ("Giải trí", "film", "#8b5cf6"),
            ("Hóa đơn", "file-text", "#6366f1"),
            ("Sức khỏe", "heart-pulse", "#ef4444")
        ]

        # Kiểm tra xem người dùng có chỉ định số tiền riêng cho từng danh mục hay không
        specific_allocations = []
        for name, icon, color in popular_defs:
            nl = name.lower()
            if nl in t:
                m = re.search(rf"{nl}[^\d]{{0,15}}?(\d+(?:[\.,]\d+)?\s*(?:triệu|tr|nghìn|ngàn|k|củ|đ)?)", t)
                if m:
                    parsed_amt = AIService._parse_vietnamese_amount(m.group(1))
                    if parsed_amt > 0:
                        dm = dm_map.get(nl)
                        if not dm:
                            dm = DanhMuc(ma_nd=ma_nd, ten_dm=name, loai_dm="chi", icon=icon, mau_sac=color, han_muc=0.0)
                            db.add(dm)
                            db.flush()
                            dm_map[nl] = dm
                        specific_allocations.append((dm, parsed_amt))

        if specific_allocations:
            return AIService._thuc_thi_thiet_lap_ngan_sach(db, ma_nd, specific_allocations)

        if default_amount <= 0:
            return None

        # Xác định các danh mục cần phân bổ
        target_cats = []
        if any(w in combined_text for w in ["phổ biến", "giải trí", "ăn uống", "đi lại", "mua sắm"]):
            for name, icon, color in [("Ăn uống", "utensils", "#f97316"), ("Đi lại", "car", "#0ea5e9"), ("Mua sắm", "shopping-bag", "#ec4899"), ("Giải trí", "film", "#8b5cf6")]:
                dm = dm_map.get(name.lower())
                if not dm:
                    dm = DanhMuc(ma_nd=ma_nd, ten_dm=name, loai_dm="chi", icon=icon, mau_sac=color, han_muc=0.0)
                    db.add(dm)
                    db.flush()
                    dm_map[name.lower()] = dm
                target_cats.append(dm)
        else:
            target_cats = list(user_dms)
            if not target_cats:
                for name, icon, color in popular_defs[:4]:
                    dm = DanhMuc(ma_nd=ma_nd, ten_dm=name, loai_dm="chi", icon=icon, mau_sac=color, han_muc=0.0)
                    db.add(dm)
                    db.flush()
                    target_cats.append(dm)

        if not target_cats:
            return "Chưa có danh mục chi tiêu nào để thiết lập hạn mức bạn nhé!"

        category_allocations = [(cat, default_amount) for cat in target_cats]
        return AIService._thuc_thi_thiet_lap_ngan_sach(db, ma_nd, category_allocations)

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

        # 0. Multi-turn Confirmation Resolver (Xác nhận an toàn trước khi xóa):
        # Nếu AI lượt trước đang chờ người dùng xác nhận xóa (Giao dịch, Hũ tiết kiệm, Danh mục)
        last_ai_msg = ""
        if lich_su_chat:
            prev_ai_msgs = [m.get("content", "").strip() for m in lich_su_chat if m.get("role") in ["assistant", "ai", "ai_tro_ly"] and m.get("content", "").strip()]
            if prev_ai_msgs:
                last_ai_msg = prev_ai_msgs[-1]

        if not last_ai_msg:
            try:
                last_log = db.query(LichSuAI).filter(LichSuAI.ma_nd == ma_nd).order_by(LichSuAI.ma_log.desc()).first()
                if last_log and last_log.tra_loi:
                    if last_log.ngay_tao and (datetime.now() - last_log.ngay_tao).total_seconds() < 1800:
                        last_ai_msg = last_log.tra_loi
            except Exception:
                pass

        if last_ai_msg and "XÁC NHẬN XÓA" in last_ai_msg:
            cancel_cues = ["hủy", "huỷ", "thôi", "đừng", "giữ lại", "không xóa", "ko xóa", "dừng", "bỏ qua", "cancel", "khỏi xóa", "không nhé", "ko nha"]
            is_cancel = any(w in t for w in cancel_cues) or t in ["không", "ko", "k", "no", "n", "không cần", "thôi không"]
            if is_cancel:
                return "Dạ vâng! Mình đã hủy thao tác xóa rồi nhé. Mọi dữ liệu của bạn vẫn được giữ nguyên vẹn an toàn! 😊"

            confirm_phrases = [
                "đồng ý", "xác nhận", "chắc chắn", "tiến hành", "tiến hành xóa",
                "xóa đi", "xóa luôn", "xóa nó", "xóa đi nhé", "xóa giúp", "xóa hộ",
                "chuẩn rồi", "đúng rồi", "ok xóa", "đồng ý xóa"
            ]
            t_words = set(re.findall(r'\b\w+\b', t))
            confirm_single_words = {"ok", "oke", "okay", "yes", "có", "ừ", "uh", "ừm", "yep", "xóa", "xoá"}
            is_confirm = any(p in t for p in confirm_phrases) or (len(t.split()) <= 3 and bool(t_words.intersection(confirm_single_words)))
            if is_confirm:
                # 1. Giao dịch
                m_gd = re.search(r'Mã giao dịch:\s*#(\d+)', last_ai_msg)
                if m_gd:
                    ma_gd = int(m_gd.group(1))
                    tx = db.query(GiaoDich).filter(GiaoDich.ma_gd == ma_gd, GiaoDich.ma_nd == ma_nd).first()
                    if tx:
                        return AIService._thuc_thi_xoa_giao_dich(db, ma_nd, tx)
                    else:
                        return "Giao dịch này không còn tồn tại hoặc đã được xử lý trước đó rồi bạn nhé!"

                # 2. Hũ tiết kiệm
                m_hu = re.search(r'Mã hũ:\s*#(\d+)', last_ai_msg)
                if m_hu:
                    ma_mt = int(m_hu.group(1))
                    goal = db.query(MucTieuTietKiem).filter(MucTieuTietKiem.ma_mt == ma_mt, MucTieuTietKiem.ma_nd == ma_nd).first()
                    if goal:
                        return AIService._thuc_thi_xoa_hu_tiet_kiem(db, ma_nd, goal)
                    else:
                        return "Hũ tiết kiệm này không còn tồn tại hoặc đã được xóa trước đó rồi bạn nhé!"

                # 3. Danh mục
                m_dm = re.search(r'Mã danh mục:\s*#(\d+)', last_ai_msg)
                if m_dm:
                    ma_dm = int(m_dm.group(1))
                    cat = db.query(DanhMuc).filter(DanhMuc.ma_dm == ma_dm, DanhMuc.ma_nd == ma_nd).first()
                    if cat:
                        return AIService._thuc_thi_xoa_danh_muc(db, ma_nd, cat)
                    else:
                        return "Danh mục này không còn tồn tại hoặc đã được xóa trước đó rồi bạn nhé!"

        # 0.1. Multi-turn Confirmation Resolver (Xác nhận phân bổ ngân sách / hạn mức):
        # Chỉ kích hoạt khi lượt AI trước thực sự đưa ra lời đề xuất / câu hỏi phân bổ ngân sách
        is_asking_alloc = any(kw in last_ai_msg.lower() for kw in [
            "bạn có muốn mình hỗ trợ phân bổ", "bạn có muốn mình áp dụng mức này", "để mình lên kế hoạch ngân sách luôn",
            "bạn có đồng ý với đề xuất phân bổ", "áp dụng mức này cho các danh mục", "phân bổ thêm hạn mức cho các danh mục khác"
        ])
        if last_ai_msg and is_asking_alloc:
            t_norm = t.replace("dnah", "danh")
            # Nếu người dùng đang thực hiện một lệnh độc lập khác (rút, nộp, tạo, sửa, xóa...), không chặn lại
            action_interrupt = any(w in t_norm for w in ["rút", "nộp", "tạo", "sửa", "xoá", "xóa", "hủy", "huỷ", "đổi", "chi tiêu", "đã chi"])
            if not action_interrupt:
                cancel_cues = ["hủy", "huỷ", "thôi", "đừng", "không cần", "ko cần", "bỏ qua", "cancel"]
                is_cancel = any(w in t_norm for w in cancel_cues) or t_norm in ["không", "ko", "k", "no", "thôi"]
                if is_cancel:
                    return "Dạ vâng! Mình đã hủy kế hoạch phân bổ hạn mức rồi nhé. Mọi số liệu của bạn vẫn giữ nguyên an toàn! 😊"

                confirm_phrases = [
                    "đúng rồi", "chuẩn rồi", "chính xác", "đồng ý", "tiến hành",
                    "cấp đi", "làm đi", "thiết lập đi", "áp dụng", "cấp cho", "cấp luôn", "áp dụng đi"
                ]
                t_words = set(re.findall(r'\b\w+\b', t_norm))
                confirm_single_words = {"ok", "oke", "okay", "yes", "có", "ừ", "uh", "ừm", "yep", "chuẩn", "cấp"}
                is_confirm = any(p in t_norm for p in confirm_phrases) or (len(t_norm.split()) <= 4 and bool(t_words.intersection(confirm_single_words)))
                if is_confirm:
                    alloc_amount = amount if amount > 0 else AIService._parse_vietnamese_amount(last_ai_msg.lower())
                    if alloc_amount <= 0:
                        m_amt = re.search(r'(\d[\d\.,]*)\s*(?:đ|k|triệu|tr)?', last_ai_msg)
                        if m_amt:
                            alloc_amount = AIService._parse_vietnamese_amount(m_amt.group(1))
                    if alloc_amount > 0:
                        return AIService._xu_ly_phan_bo_ngan_sach_tu_nhien(db, ma_nd, t_norm, alloc_amount, last_ai_msg)

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
        create_goal_cues = [
            "tạo hũ tiết kiệm", "thêm hũ tiết kiệm", "lập hũ tiết kiệm", "tạo mục tiêu",
            "thêm mục tiêu", "lập mục tiêu", "đặt mục tiêu tiết kiệm", "tạo hũ", "thêm hũ",
            "muốn tiết kiệm", "cần tiết kiệm", "định tiết kiệm", "dự định tiết kiệm",
            "kế hoạch tiết kiệm", "lập quỹ", "tạo quỹ", "mục tiêu mua", "tiết kiệm mua", "tiết kiệm để"
        ]
        is_create_goal = any(w in t for w in create_goal_cues) or (
            "tiết kiệm" in t and any(w in t for w in ["muốn", "cần", "dự định", "kế hoạch", "lập mục tiêu", "đặt mục tiêu"]) and not any(w in t for w in ["nộp", "trích", "nạp", "bỏ", "gửi", "rút", "xóa"])
        )
        if is_create_goal and not any(w in t for w in ["nâng", "tăng", "đổi", "sửa", "giảm", "hạ", "chỉnh", "nộp", "trích", "rút", "xóa", "hủy", "xem"]):
            return AIService._xu_ly_tao_hu_tiet_kiem(db, ma_nd, t, amount, raw)

        # 4. NÂNG / GIẢM / ĐỔI MỤC TIÊU TIẾT KIỆM (UPDATE SAVINGS GOAL TARGET)
        goals = db.query(MucTieuTietKiem).filter(MucTieuTietKiem.ma_nd == ma_nd).all()
        sorted_goals = sorted(goals, key=lambda g: len(g.ten_muc_tieu), reverse=True)
        matched_goal = None
        for g in sorted_goals:
            g_name = g.ten_muc_tieu.lower()
            if g_name in t or any(w in t for w in g_name.split() if len(w) > 3 and w not in ["tiết", "kiệm", "mua", "tiền", "quỹ"]):
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
        not_deposit = not any(w in t for w in ["nộp", "trích", "nạp", "bỏ", "chuyển", "gửi", "giao dịch", "hạn mức", "ngân sách", "danh mục"])

        is_update_goal = any(c in t for c in update_goal_cues) or (
            (has_goal_term or matched_goal) and has_update_verb and not_deposit and not any(w in t for w in ["ngân sách", "hạn mức", "danh mục"])
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

        # 8.5. PHÂN BỔ / CẤP HẠN MỨC NGÂN SÁCH ĐA HŨ HOẶC MỖI DANH MỤC
        t_norm = t.replace("dnah", "danh")
        multi_budget_cues = [
            "cấp cho mỗi", "mỗi danh mục", "mỗi hũ", "các danh mục", "các hũ",
            "chia đều", "phân bổ mỗi", "phân bổ cho mỗi", "phân bổ đều", "chia ngân sách",
            "cấp ngân sách", "phân bổ ngân sách", "cho mỗi danh mục", "cho từng danh mục",
            "cho từng hũ", "cho mỗi hũ", "cấp cho các", "thiết lập cho mỗi", "đặt cho mỗi",
            "cấp cho cả", "cấp mỗi danh mục", "cấp mỗi hũ", "cấp hạn mức các hũ", "cấp hạn mức mỗi hũ",
            "phân bổ 6 hũ"
        ]
        is_multi_budget = any(c in t_norm for c in multi_budget_cues) or (
            any(w in t_norm for w in ["cấp", "phân bổ", "chia", "đặt", "thiết lập"]) and any(w in t_norm for w in ["hạn mức", "ngân sách"]) and any(w in t_norm for w in ["mỗi", "các", "tất cả", "đều", "cho", "hũ"])
        )
        if is_multi_budget and amount > 0:
            return AIService._xu_ly_phan_bo_ngan_sach_tu_nhien(db, ma_nd, t_norm, amount, last_ai_msg)

        # 9. ĐIỀU CHỈNH HẠN MỨC NGÂN SÁCH HŨ (UPDATE BUDGET LIMIT)
        user_dms = db.query(DanhMuc).filter(DanhMuc.ma_nd == ma_nd, DanhMuc.loai_dm == "chi").all()
        target_dm = None
        for dm in user_dms:
            if dm.ten_dm.lower() in t:
                target_dm = dm
                break
        if not target_dm:
            for dm in user_dms:
                for kw in ["ăn uống", "đi chơi", "mua sắm", "đi lại", "hóa đơn", "giải trí", "học tập", "sức khỏe"]:
                    if kw in t and kw in dm.ten_dm.lower():
                        target_dm = dm
                        break
                if target_dm:
                    break

        update_limit_verbs = ["nâng", "tăng", "đổi", "sửa", "chỉnh", "đặt", "giảm", "hạ", "cập nhật", "cấp", "thiết lập"]
        level_preps = ["xuống", "thành", "lên", "còn", "về"]
        explicit_budget_terms = ["hạn mức", "ngân sách", "danh mục", "hũ"]

        is_tx_indicator = any(m in t for m in ["đã chi", "đã tiêu", "vừa chi", "vừa ăn", "vừa mua", "hết", "thanh toán", "trả tiền", "giao dịch vừa", "khoản chi"])

        has_explicit_term = any(term in t for term in explicit_budget_terms)
        has_verb = any(v in t for v in update_limit_verbs)
        has_level = any(lp in t for lp in level_preps)

        update_limit_cues = [
            "nâng hạn mức", "tăng hạn mức", "đổi hạn mức", "sửa hạn mức", "giảm hạn mức", "chỉnh hạn mức",
            "đặt hạn mức", "hạn mức lên", "hạn mức thành", "hạn mức hũ", "cấp hạn mức", "cấp ngân sách",
            "sửa danh mục", "giảm danh mục", "tăng danh mục", "chỉnh danh mục", "đổi danh mục", "hạ danh mục",
            "sửa hũ", "giảm hũ", "tăng hũ", "chỉnh hũ", "hạ hũ", "đổi hũ", "đặt hũ", "cập nhật hũ",
            "ngân sách hũ", "ngân sách danh mục"
        ]

        is_update_limit = False
        if amount > 0 and not is_tx_indicator:
            # 1. Khớp từ khóa cụ thể
            if any(c in t for c in update_limit_cues):
                is_update_limit = True
            # 2. Có từ hạn mức/ngân sách kết hợp danh mục hoặc hành động
            elif any(term in t for term in ["hạn mức", "ngân sách"]):
                if target_dm or has_verb or has_level or any(c in t for c in ["cho", "của", "mỗi", "các", "là", "thành"]):
                    is_update_limit = True
            # 3. Có từ "danh mục" hoặc "hũ" kết hợp hành động điều chỉnh hoặc cấp tiền
            elif any(term in t for term in ["danh mục", "hũ"]) and (has_verb or has_level or "cho" in t):
                is_update_limit = True
            # 4. Có danh mục cụ thể và có hướng điều chỉnh mức tiền
            elif target_dm and (
                (has_verb and (has_level or "thành" in t or "là" in t)) or
                has_level or
                (has_verb and not any(w in t for w in ["chi", "tiêu", "ăn", "uống", "mua"]))
            ):
                is_update_limit = True

        if is_update_limit and amount > 0:
            if not target_dm and user_dms:
                target_dm = user_dms[0]

            if target_dm:
                return AIService._thuc_thi_thiet_lap_ngan_sach(db, ma_nd, [(target_dm, amount)])

        # 10. XOÁ / HỦY GIAO DỊCH (DELETE TRANSACTION)
        delete_cues = [
            "xóa giao dịch", "xoá giao dịch", "hủy giao dịch", "huỷ giao dịch", "xóa khoản chi",
            "hủy khoản chi", "xóa giao dịch vừa", "hủy giao dịch gần", "xóa cái vừa", "hủy cái vừa",
            "bỏ cái vừa", "xóa cái vừa ghi", "hủy cái vừa ghi", "xóa nó đi", "hủy nó đi", "bỏ nó đi",
            "xóa đi", "hủy đi", "bỏ giao dịch", "xóa khoản", "hủy khoản"
        ]
        if any(w in t for w in delete_cues):
            return AIService._xu_ly_xoa_giao_dich(db, ma_nd, t)

        # 11. SỬA / CẬP NHẬT / ĐÍNH CHÍNH GIAO DỊCH (EDIT / CORRECTION)
        edit_cues = [
            "sửa giao dịch", "đổi giao dịch", "chỉnh giao dịch", "sửa khoản chi", "đổi khoản chi",
            "sửa số tiền", "đổi số tiền", "sửa ghi chú", "đổi ghi chú", "sửa lại", "đổi lại",
            "chỉnh lại", "sửa thành", "đổi thành", "tôi nhầm", "mình nhầm", "em nhầm", "anh nhầm",
            "nhầm rồi", "bị nhầm", "nói nhầm", "ghi nhầm", "nói lộn", "ghi lộn", "lộn rồi", "bị lộn",
            "đính chính", "đúng ra là", "thực ra là", "thật ra là", "không phải", "mới đúng", "mới chuẩn", "mới phải"
        ]
        is_edit = any(c in t for c in edit_cues) or (
            t.startswith("(") and any(w in t for w in ["nhầm", "mới đúng", "lẩu", "cơm", "đúng", "không phải", "k"])
        )
        if is_edit:
            return AIService._xu_ly_sua_giao_dich(db, ma_nd, t, raw)

        # 12. TRA CỨU / LỌC GIAO DỊCH (QUERY TRANSACTIONS)
        query_cues = [
            "tìm giao dịch", "tra cứu giao dịch", "xem giao dịch", "liệt kê giao dịch", "các giao dịch",
            "các khoản chi trên", "khoản chi lớn", "hôm nay tôi đã tiêu những gì", "hôm nay đã chi gì",
            "hôm nay đã tiêu gì", "hôm qua đã tiêu", "hôm nay tiêu", "hôm qua tiêu", "tháng này đã chi",
            "tháng này tiêu", "xem các khoản", "tìm khoản"
        ]
        if any(w in t for w in query_cues):
            return AIService._xu_ly_tra_cuu_giao_dich(db, ma_nd, t, raw)

        # 13. XEM TIẾN ĐỘ HŨ TIẾT KIỆM (VIEW SAVINGS GOALS)
        is_view_goals = any(w in t for w in [
            "tiến độ hũ", "tiến độ tiết kiệm", "tiến độ mục tiêu", "các hũ tiết kiệm", "danh sách hũ",
            "hũ tiết kiệm hiện có", "mục tiêu tiết kiệm hiện có", "danh sách mục tiêu", "xem các hũ",
            "xem hũ tiết kiệm", "xem mục tiêu tiết kiệm", "xem các mục tiêu", "mục tiêu tiết kiệm hiện tại",
            "các mục tiêu tiết kiệm", "danh sách hũ tiết kiệm", "xem hũ", "các hũ hiện tại", "hũ hiện có"
        ]) or (
            any(w in t for w in ["xem", "danh sách", "kiểm tra", "tiến độ"]) and any(w in t for w in ["mục tiêu", "hũ tiết kiệm", "quỹ tiết kiệm"])
        )
        if is_view_goals:
            return AIService._xu_ly_xem_hu_tiet_kiem(db, ma_nd, t)

        # 14. XEM NGÂN SÁCH & HẠN MỨC CÁC HŨ (VIEW BUDGETS)
        is_view_budget = any(w in t for w in [
            "ngân sách các hũ", "ngân sách tháng này", "hạn mức các hũ", "hạn mức tháng này",
            "xem danh mục chi tiêu", "danh mục chi tiêu", "các hũ ngân sách", "danh sách danh mục",
            "xem hạn mức", "hạn mức danh mục", "hạn mức các danh mục", "hạn mức hiện tại", "ngân sách hiện tại"
        ]) or (
            any(w in t for w in ["xem", "danh sách", "kiểm tra"]) and any(w in t for w in ["hạn mức", "ngân sách"])
        )
        if is_view_budget:
            return AIService._xu_ly_xem_ngan_sach_danh_muc(db, ma_nd, t)

        # 15. ĐÁNH GIÁ SỨC KHỎE TÀI CHÍNH & PHÂN BỔ 6 HŨ (FINANCIAL HEALTH & 6 JARS)
        if any(w in t for w in ["sức khỏe tài chính", "chấm điểm tài chính", "đánh giá tài chính", "phân bổ 6 hũ", "tư vấn 6 hũ", "chia 6 hũ"]):
            return AIService._xu_ly_suc_khoe_tai_chinh(db, ma_nd, t)

        # 16. THÊM GIAO DỊCH THU / CHI THÔNG THƯỜNG (ADD TRANSACTION)
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

        note_source = extracted_note if extracted_note else raw
        clean_note = AIService._lam_sach_mo_ta_giao_dich(note_source, "Chi tiêu" if loai_gd == "chi" else "Thu nhập")
        target_dm = AIService._xac_dinh_danh_muc(db, ma_nd, suggested_cat if suggested_cat else clean_note, loai_gd)
        tx_time = AIService._parse_vietnamese_datetime(t)

        tx = GiaoDich(
            ma_nd=ma_nd,
            ma_dm=target_dm.ma_dm,
            so_tien=amount,
            loai_gd=loai_gd,
            ghi_chu=clean_note,
            ngay_gd=tx_time,
            ngay_tao=datetime.utcnow()
        )
        db.add(tx)
        db.commit()
        db.refresh(tx)

        canh_bao_str = ""
        if loai_gd == "chi":
            cb = NganSachService.kiem_tra_ngan_sach(db, ma_nd, target_dm.ma_dm, tx_time)
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
            f"• **Thời gian:** {tx_time.strftime('%H:%M - %d/%m/%Y')}\n\n"
            f"💳 **Số dư ví chính khả dụng:** **{so_du_vi:,.0f}đ**"
            f"{canh_bao_str}"
        )

    @staticmethod
    def hoi_dap_ai(
        db: Session,
        ma_nd: int,
        cau_hoi: str,
        lich_su_chat: Optional[List[Dict[str, str]]] = None,
        ma_phien: Optional[str] = None
    ) -> str:
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
            tra_loi_refuse = (
                "Xin lỗi bạn! 🙏 Tôi là Trợ lý Quản lý Tài chính Cá nhân MoneyMind, "
                "không có thẩm quyền tư vấn đầu tư chứng khoán rủi ro hay các chủ đề ngoài phạm vi quản lý thu chi, ngân sách và tiết kiệm. "
                "Bạn có thắc mắc nào về thu chi, số dư hay ngân sách tháng này không? 💰"
            )
            AIService.luu_nhat_ky_ai(db, ma_nd, cau_hoi_clean, tra_loi_refuse, loai_hanh_dong="tu_van", ma_phien=ma_phien)
            return tra_loi_refuse

        # Tự động nhận diện lệnh giao tiếp tự nhiên và thêm giao dịch vào hệ thống (hỗ trợ đa lượt)
        thao_tac_res = AIService.xu_ly_giao_dich_tu_nhien(db, ma_nd, cau_hoi_clean, lich_su_chat=lich_su_chat)
        if thao_tac_res:
            AIService.luu_nhat_ky_ai(db, ma_nd, cau_hoi_clean, thao_tac_res, ma_phien=ma_phien)
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
            "5. QUY TẮC BẢO TOÀN DỮ LIỆU & TRÁNH NHẬN VƠ THỰC THI GIAO DỊCH / NGÂN SÁCH:\n"
            "   - Mọi thao tác thêm/sửa/xóa giao dịch, phân bổ ngân sách, thiết lập hạn mức hoặc trích tiền đều do hệ thống backend tự động xử lý trực tiếp vào cơ sở dữ liệu.\n"
            "   - Bạn là Trí tuệ Nhân tạo tư vấn, TUYỆT ĐỐI KHÔNG tự nhận là 'mình đã ghi nhận', 'mình đã lưu giao dịch', 'mình đã thiết lập hạn mức', 'mình đã phân bổ ngân sách' nếu bạn chỉ đang đưa ra lời khuyên hoặc trò chuyện!\n"
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

        # Thử gọi Gemini AI qua REST đa mô hình hoặc cục bộ
        tra_loi_ai = None
        try:
            tra_loi_ai = AIService._call_gemini_with_timeout(full_prompt, timeout=settings.AI_TIMEOUT_SECONDS)
        except Exception:
            tra_loi_ai = AIService._tra_loi_cuc_bo_thong_minh(cau_hoi_clean, ctx, lich_su_chat)

        if tra_loi_ai:
            AIService.luu_nhat_ky_ai(db, ma_nd, cau_hoi_clean, tra_loi_ai, ma_phien=ma_phien)

        return tra_loi_ai

    @staticmethod
    def xac_dinh_loai_hanh_dong(tra_loi: str) -> str:
        """Tự động phân loại bản chất tương tác dựa trên kết quả phản hồi của AI."""
        tl = tra_loi.lower()
        if "xác nhận xóa" in tl or "xác nhận xoá" in tl:
            return "xac_nhan_xoa"
        if "hủy thao tác xóa" in tl or "huỷ thao tác xoá" in tl:
            return "huy_xoa"
        if "sau khi đính chính" in tl or "sửa lại ngay" in tl:
            return "sua_giao_dich"
        if "đã xóa giao dịch" in tl or "đã xoá giao dịch" in tl:
            return "xoa_giao_dich"
        if "đã xóa danh mục" in tl or "đã xoá danh mục" in tl:
            return "xoa_danh_muc"
        if "đã xóa hũ" in tl or "đã xoá hũ" in tl or "đã xóa mục tiêu" in tl:
            return "xoa_hu"
        if "kết quả tra cứu" in tl:
            return "tra_cuu"
        if "đã tạo hũ tiết kiệm" in tl or "đã tạo mục tiêu" in tl:
            return "tao_hu"
        if "trích tiền từ hũ" in tl or "rút tiền từ hũ" in tl:
            return "rut_hu"
        if "trích" in tl and "vào hũ tiết kiệm" in tl:
            return "nop_hu"
        if "mục tiêu tiết kiệm sau điều chỉnh" in tl:
            return "doi_muc_tieu"
        if "hạn mức mới" in tl or "hạn mức ngân sách" in tl or "chi tiêu các hũ" in tl:
            return "ngan_sach"
        if "sức khỏe tài chính" in tl or "6 chiếc hũ" in tl:
            return "suc_khoe"
        if "đã ghi nhận giao dịch" in tl or "chi tiết giao dịch" in tl:
            return "them_giao_dich"
        return "tu_van"

    @staticmethod
    def lay_nhan_hanh_dong(loai: str) -> Dict[str, str]:
        """Trả về nhãn hiển thị, icon và màu sắc tương ứng với từng loại tương tác."""
        labels = {
            "xac_nhan_xoa": {"ten": "Hỏi xác nhận xóa", "icon": "⚠️", "mau": "amber"},
            "huy_xoa": {"ten": "Hủy thao tác xóa", "icon": "🛡️", "mau": "slate"},
            "them_giao_dich": {"ten": "Thêm giao dịch", "icon": "💸", "mau": "emerald"},
            "sua_giao_dich": {"ten": "Đính chính giao dịch", "icon": "✏️", "mau": "amber"},
            "xoa_giao_dich": {"ten": "Xóa giao dịch", "icon": "🗑️", "mau": "rose"},
            "xoa_hu": {"ten": "Xóa hũ tiết kiệm", "icon": "🗑️", "mau": "rose"},
            "xoa_danh_muc": {"ten": "Xóa danh mục", "icon": "🗑️", "mau": "rose"},
            "tra_cuu": {"ten": "Tra cứu chi tiêu", "icon": "🔍", "mau": "sky"},
            "tao_hu": {"ten": "Tạo hũ tiết kiệm", "icon": "🎯", "mau": "teal"},
            "nop_hu": {"ten": "Nộp tiền tích lũy", "icon": "💰", "mau": "emerald"},
            "rut_hu": {"ten": "Rút tiền về ví", "icon": "📤", "mau": "indigo"},
            "doi_muc_tieu": {"ten": "Đổi mục tiêu", "icon": "🔄", "mau": "purple"},
            "ngan_sach": {"ten": "Hạn mức ngân sách", "icon": "🏺", "mau": "cyan"},
            "suc_khoe": {"ten": "Sức khỏe 6 Hũ", "icon": "🏥", "mau": "teal"},
            "tu_van": {"ten": "Tư vấn tài chính", "icon": "💬", "mau": "slate"},
        }
        return labels.get(loai, {"ten": "Hỏi đáp AI", "icon": "🤖", "mau": "teal"})

    @staticmethod
    def luu_nhat_ky_ai(
        db: Session,
        ma_nd: int,
        cau_hoi: str,
        tra_loi: str,
        loai_hanh_dong: Optional[str] = None,
        ma_phien: Optional[str] = None
    ):
        """Ghi nhận nhật ký tương tác người dùng - AI vào cơ sở dữ liệu theo phiên."""
        try:
            if not loai_hanh_dong:
                loai_hanh_dong = AIService.xac_dinh_loai_hanh_dong(tra_loi)
            log = LichSuAI(
                ma_nd=ma_nd,
                ma_phien=ma_phien,
                cau_hoi=cau_hoi,
                tra_loi=tra_loi,
                loai_hanh_dong=loai_hanh_dong,
                ngay_tao=datetime.now()
            )
            db.add(log)
            db.commit()
            db.refresh(log)
            return log
        except Exception:
            db.rollback()
            return None

    @staticmethod
    def lay_lich_su_ai_theo_ngay(
        db: Session,
        ma_nd: int,
        ngay: Optional[str] = None,
        ma_phien: Optional[str] = None,
        tu_khoa: Optional[str] = None,
        limit: int = 200
    ) -> Dict:
        """
        Truy xuất nhật ký tương tác với AI, gom nhóm theo từng phiên trò chuyện và theo ngày.
        Hỗ trợ lọc theo mã phiên, ngày cụ thể (YYYY-MM-DD) và tìm kiếm từ khóa.
        """
        from collections import OrderedDict
        q = db.query(LichSuAI).filter(LichSuAI.ma_nd == ma_nd)

        if ma_phien:
            q = q.filter(LichSuAI.ma_phien == ma_phien)

        if ngay:
            try:
                dt_start = datetime.strptime(ngay, "%Y-%m-%d")
                dt_end = dt_start + timedelta(days=1)
                q = q.filter(LichSuAI.ngay_tao >= dt_start, LichSuAI.ngay_tao < dt_end)
            except Exception:
                pass

        if tu_khoa:
            tk = tu_khoa.strip()
            if tk:
                q = q.filter((LichSuAI.cau_hoi.ilike(f"%{tk}%")) | (LichSuAI.tra_loi.ilike(f"%{tk}%")))

        logs = q.order_by(LichSuAI.ngay_tao.desc(), LichSuAI.ma_log.desc()).limit(limit).all()

        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        yesterday_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        thu_names = {0: "Thứ Hai", 1: "Thứ Ba", 2: "Thứ Tư", 3: "Thứ Năm", 4: "Thứ Sáu", 5: "Thứ Bảy", 6: "Chủ Nhật"}

        # 1. Gom nhóm theo từng phiên trò chuyện (Sessions)
        session_groups = OrderedDict()
        # 2. Đồng thời gom nhóm theo ngày để đảm bảo tương thích ngược 100%
        day_groups = OrderedDict()

        for item in logs:
            day_str = item.ngay_tao.strftime("%Y-%m-%d") if item.ngay_tao else today_str
            if day_str not in day_groups:
                day_groups[day_str] = []

            # Xác định khóa phiên trò chuyện
            s_key = item.ma_phien if item.ma_phien else (f"legacy_{item.ngay_tao.strftime('%Y%m%d_%H')}" if item.ngay_tao else "legacy_phien")
            if s_key not in session_groups:
                session_groups[s_key] = {
                    "ma_phien": s_key,
                    "thoi_gian_bat_dau": item.ngay_tao,
                    "items": []
                }

            badge_info = AIService.lay_nhan_hanh_dong(item.loai_hanh_dong or "tu_van")
            log_item = {
                "ma_log": item.ma_log,
                "ma_phien": s_key,
                "cau_hoi": item.cau_hoi,
                "tra_loi": item.tra_loi,
                "loai_hanh_dong": item.loai_hanh_dong or "tu_van",
                "ten_hanh_dong": badge_info["ten"],
                "icon": badge_info["icon"],
                "mau": badge_info["mau"],
                "thoi_gian": item.ngay_tao.strftime("%H:%M") if item.ngay_tao else "",
                "ngay_tao": item.ngay_tao.strftime("%Y-%m-%d %H:%M:%S") if item.ngay_tao else ""
            }
            session_groups[s_key]["items"].append(log_item)
            day_groups[day_str].append(log_item)

        cac_phien = []
        for s_key, s_data in session_groups.items():
            dt = s_data["thoi_gian_bat_dau"] or now
            dt_str = dt.strftime("%Y-%m-%d")
            d_format = dt.strftime("%d/%m/%Y")
            time_str = dt.strftime("%H:%M")
            if dt_str == today_str:
                label = f"Hôm nay, {time_str}"
            elif dt_str == yesterday_str:
                label = f"Hôm qua, {time_str}"
            else:
                label = f"{time_str} - {d_format}"

            items = s_data["items"]
            # Sắp xếp các tin trong phiên theo thứ tự thời gian tăng dần để dễ đọc mạch hội thoại
            items_sorted = sorted(items, key=lambda x: x["ma_log"])
            first_q = items_sorted[0]["cau_hoi"] if items_sorted else "Trò chuyện"
            summary_title = first_q if len(first_q) <= 45 else (first_q[:42] + "...")

            cac_phien.append({
                "ma_phien": s_key,
                "tieu_de_phien": summary_title,
                "thoi_gian_hien_thi": label,
                "ngay_gio": dt.strftime("%Y-%m-%d %H:%M:%S"),
                "so_luong": len(items),
                "nhat_ky": items_sorted
            })

        cac_ngay = []
        for day_str, items in day_groups.items():
            d_obj = datetime.strptime(day_str, "%Y-%m-%d")
            d_format = d_obj.strftime("%d/%m/%Y")
            if day_str == today_str:
                label = f"Hôm nay ({d_format})"
            elif day_str == yesterday_str:
                label = f"Hôm qua ({d_format})"
            else:
                label = f"{thu_names.get(d_obj.weekday(), 'Ngày')} ({d_format})"

            cac_ngay.append({
                "ngay": day_str,
                "ngay_hien_thi": label,
                "so_luong": len(items),
                "nhat_ky": items
            })

        return {
            "tong_so": len(logs),
            "tong_so_phien": len(cac_phien),
            "cac_phien": cac_phien,
            "tong_so_ngay": len(cac_ngay),
            "cac_ngay": cac_ngay
        }

    @staticmethod
    def xoa_lich_su_ai(
        db: Session,
        ma_nd: int,
        ma_log: Optional[int] = None,
        ngay: Optional[str] = None,
        ma_phien: Optional[str] = None
    ) -> int:
        """Xóa nhật ký tương tác AI theo ID cụ thể, theo phiên, theo ngày hoặc toàn bộ."""
        q = db.query(LichSuAI).filter(LichSuAI.ma_nd == ma_nd)
        if ma_log:
            q = q.filter(LichSuAI.ma_log == ma_log)
        elif ma_phien:
            q = q.filter(LichSuAI.ma_phien == ma_phien)
        elif ngay:
            try:
                dt_start = datetime.strptime(ngay, "%Y-%m-%d")
                dt_end = dt_start + timedelta(days=1)
                q = q.filter(LichSuAI.ngay_tao >= dt_start, LichSuAI.ngay_tao < dt_end)
            except Exception:
                pass
        count = q.delete(synchronize_session=False)
        db.commit()
        return count
