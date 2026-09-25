"""
Điểm khởi chạy ứng dụng MoneyMind
Kết nối kiến trúc MVC app/ và phục vụ giao diện Web Frontend
"""
import os
import random
import urllib.request
import json
import asyncio
from datetime import datetime
from typing import List, Optional
from fastapi import Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.main import app
from app.core.database import get_db, SessionLocal
from app.core.security import (
    get_current_user,
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token
)
from app.models import (
    NguoiDung,
    DanhMuc,
    GiaoDich,
    NganSach,
    MucTieuTietKiem,
    ThongBao,
    User,
    Category,
    Transaction,
    SavingsGoal,
    Notification
)
from app.schemas import UserCreate, Token
from app.services.ngan_sach_service import NganSachService
from app.services.ai_service import AIService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/dang-nhap")
ACTIVE_SESSIONS = {}

def get_current_active_user(user: NguoiDung = Depends(get_current_user)):
    return user

def _format_notif(n: Notification):
    created = n.ngay_tao.isoformat() if n.ngay_tao else datetime.now().isoformat()
    is_read = bool(n.da_xem) if n.da_xem is not None else False
    return {
        "id": n.id,
        "user_id": n.ma_nd,
        "ma_nd": n.ma_nd,
        "title": n.tieu_de or "",
        "tieu_de": n.tieu_de or "",
        "message": n.noi_dung or "",
        "noi_dung": n.noi_dung or "",
        "da_xem": is_read,
        "is_read": is_read,
        "created_at": created,
        "ngay_tao": created
    }

def save_notification(db: Session, user_id: int, title: str, message: str):
    new_notif = Notification(ma_nd=user_id, tieu_de=title, noi_dung=message, da_xem=False, ngay_tao=datetime.now())
    db.add(new_notif)
    db.commit()


def check_and_generate_daily_7am_notifications(db: Session, user: NguoiDung):
    """
    Tự động kiểm tra và tạo thông báo định kỳ vào lúc 7h00 sáng mỗi ngày:
    1. Cảnh báo các hũ chi tiêu vượt quá hạn mức cho phép (> 100%).
    2. Động viên các mục tiêu tiết kiệm sắp hoàn thành (>= 80% và < 100%) để cố gắng hoàn thành sớm hơn dự kiến.
    Thông báo được lưu với trạng thái chưa xem (da_xem=False) để hiển thị cờ đỏ trên chuông thông báo,
    không mở popup làm phiền khi người dùng vừa vào giao diện.
    """
    now = datetime.now()
    today_start = datetime(now.year, now.month, now.day, 0, 0, 0)
    today_7am = datetime(now.year, now.month, now.day, 7, 0, 0)

    # 1. Hũ dùng quá hạn mức (Chi tiêu > Hạn mức)
    chi_categories = db.query(DanhMuc).filter(
        DanhMuc.ma_nd == user.ma_nd,
        DanhMuc.loai_dm == "chi",
        DanhMuc.han_muc > 0
    ).all()

    over_jars = []
    approaching_jars = []
    for c in chi_categories:
        txs = db.query(GiaoDich).filter(
            GiaoDich.ma_nd == user.ma_nd,
            GiaoDich.ma_dm == c.ma_dm,
            GiaoDich.loai_gd == "chi"
        ).all()
        spent = sum(t.so_tien for t in txs if t.so_tien)
        if spent > c.han_muc:
            pct = round((spent / c.han_muc) * 100)
            over_jars.append({
                "name": c.ten_dm,
                "spent": spent,
                "limit": c.han_muc,
                "pct": pct
            })
        elif spent >= c.han_muc * 0.9:
            pct = round((spent / c.han_muc) * 100)
            approaching_jars.append({
                "name": c.ten_dm,
                "spent": spent,
                "limit": c.han_muc,
                "pct": pct
            })

    today_notifs = db.query(Notification).filter(
        Notification.ma_nd == user.ma_nd,
        Notification.ngay_tao >= today_start
    ).all()
    today_titles_lower = [(n.tieu_de or "").lower() for n in today_notifs]
    today_contents_lower = [(n.noi_dung or "").lower() for n in today_notifs]

    if over_jars:
        has_over_alert = any("vượt" in t for t in today_titles_lower)
        if not has_over_alert:
            jar_details = "\n".join([f"• Hũ \"{j['name']}\": đã chi {j['spent']:,.0f} đ / {j['limit']:,.0f} đ ({j['pct']}%)" for j in over_jars])
            title = "🚨 CẢNH BÁO: CHI TIÊU VƯỢT HẠN MỨC!"
            msg = f"Chào buổi sáng! Hệ thống ghi nhận tài khoản của bạn đang có hũ chi tiêu vượt quá hạn mức cho phép:\n\n{jar_details}\n\n⚠️ Vui lòng chi tiêu tiết kiệm lại và kiểm soát các khoản chi hôm nay!"
            notif_time = today_7am if now >= today_7am else now
            new_notif = Notification(ma_nd=user.ma_nd, tieu_de=title, noi_dung=msg, da_xem=False, ngay_tao=notif_time)
            db.add(new_notif)
            db.commit()

    if approaching_jars:
        has_near_alert = any("sắp chạm" in t or "sắp hết" in t for t in today_titles_lower)
        if not has_near_alert:
            jar_details = "\n".join([f"• Hũ \"{j['name']}\": đã chi {j['spent']:,.0f} đ / {j['limit']:,.0f} đ ({j['pct']}%)" for j in approaching_jars])
            title = "⚠️ CẢNH BÁO: CHI TIÊU SẮP CHẠM HẠN MỨC (≥90%)!"
            msg = f"Hệ thống ghi nhận tài khoản của bạn có hũ chi tiêu sắp chạm trần hạn mức:\n\n{jar_details}\n\n⚠️ Vui lòng cân nhắc chi tiêu tiết kiệm để không bị vượt quá ngân sách!"
            notif_time = today_7am if now >= today_7am else now
            new_notif = Notification(ma_nd=user.ma_nd, tieu_de=title, noi_dung=msg, da_xem=False, ngay_tao=notif_time)
            db.add(new_notif)
            db.commit()

    # 2. Mục tiêu tiết kiệm sắp hoàn thành (>= 80% và < 100%)
    goals = db.query(MucTieuTietKiem).filter(
        MucTieuTietKiem.ma_nd == user.ma_nd,
        MucTieuTietKiem.trang_thai != "hoan_thanh",
        MucTieuTietKiem.so_tien_muc_tieu > 0
    ).all()

    for g in goals:
        curr = g.so_tien_hien_tai or 0
        tgt = g.so_tien_muc_tieu or 1
        pct = round((curr / tgt) * 100)
        if 80 <= pct < 100:
            has_goal_alert = any(g.ten_muc_tieu.lower() in c for c in today_contents_lower)
            if not has_goal_alert:
                title = "🌟 ĐỘNG VIÊN: SẮP ĐẠT MỤC TIÊU TIẾT KIỆM!"
                msg = f"Chào ngày mới! Mục tiêu \"{g.ten_muc_tieu}\" của bạn đã đạt {pct}% tiến độ ({curr:,.0f} đ / {tgt:,.0f} đ)!\n\nBạn sắp cán đích rồi, hãy tiếp tục duy trì và cố gắng hoàn thành mục tiêu sớm hơn dự kiến nhé! 💪🎯"
                notif_time = today_7am if now >= today_7am else now
                new_notif = Notification(ma_nd=user.ma_nd, tieu_de=title, noi_dung=msg, da_xem=False, ngay_tao=notif_time)
                db.add(new_notif)
                db.commit()


async def daily_7am_scheduler_worker():
    """
    Background worker định kỳ: CHỈ chạy đúng 1 lần vào lúc 7h00 sáng mỗi ngày cho tất cả người dùng
    """
    last_run_day = None
    while True:
        try:
            await asyncio.sleep(30)
            now = datetime.now()
            today_str = now.strftime("%Y-%m-%d")
            if now.hour == 7 and now.minute == 0 and last_run_day != today_str:
                last_run_day = today_str
                db = SessionLocal()
                try:
                    all_users = db.query(NguoiDung).all()
                    for u in all_users:
                        check_and_generate_daily_7am_notifications(db, u)
                finally:
                    db.close()
            elif now.hour != 7 and last_run_day != today_str and now.hour > 7:
                last_run_day = today_str
        except Exception:
            await asyncio.sleep(5)


@app.on_event("startup")
async def start_daily_7am_scheduler():
    asyncio.create_task(daily_7am_scheduler_worker())


# --- CÁC ENDPOINT TƯƠNG THÍCH NGƯỢC (LEGACY COMPATIBILITY) ---

@app.get("/api/notifications")
def get_notifications(db: Session = Depends(get_db), current_user: NguoiDung = Depends(get_current_active_user)):
    # Chỉ đọc danh sách thông báo từ CSDL, KHÔNG tự ý sinh thông báo khi người dùng tải lại trang hay đăng nhập
    notifs = db.query(Notification).filter(Notification.ma_nd == current_user.ma_nd).order_by(desc(Notification.ngay_tao)).all()
    return [_format_notif(n) for n in notifs]

@app.post("/api/notifications")
def create_notification(payload: dict, db: Session = Depends(get_db), current_user: NguoiDung = Depends(get_current_active_user)):
    title = payload.get("title") or payload.get("tieu_de") or "Thông báo hệ thống"
    message = payload.get("message") or payload.get("noi_dung") or ""
    save_notification(db, current_user.ma_nd, title, message)
    return {"status": "ok", "message": "Đã lưu thông báo thành công"}

@app.put("/api/notifications/read-all")
@app.post("/api/notifications/read-all")
def mark_all_notifications_as_read(db: Session = Depends(get_db), current_user: NguoiDung = Depends(get_current_active_user)):
    db.query(Notification).filter(Notification.ma_nd == current_user.ma_nd).update({Notification.da_xem: True})
    db.commit()
    return {"status": "ok", "message": "Đã đánh dấu tất cả thông báo là đã đọc"}

@app.put("/api/notifications/{notification_id}/read")
@app.post("/api/notifications/{notification_id}/read")
def mark_notification_as_read(notification_id: int, db: Session = Depends(get_db), current_user: NguoiDung = Depends(get_current_active_user)):
    notif = db.query(Notification).filter(Notification.id == notification_id, Notification.ma_nd == current_user.ma_nd).first()
    if notif:
        notif.da_xem = True
        db.commit()
    return {"status": "ok", "message": "Đã đánh dấu thông báo là đã đọc"}

@app.post("/google-login")
def google_login(payload: dict, db: Session = Depends(get_db)):
    token = payload.get("credential")
    if not token:
        raise HTTPException(status_code=400, detail="Missing Google credential")
    
    url = f"https://oauth2.googleapis.com/tokeninfo?id_token={token}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            email = data.get("email")
            if not email:
                raise HTTPException(status_code=400, detail="Invalid Google token")
    except Exception:
        raise HTTPException(status_code=400, detail="Google token verification failed")

    user = db.query(NguoiDung).filter(NguoiDung.email == email).first()
    if not user:
        new_u = NguoiDung(
            email=email,
            ho_ten=data.get("name") or email.split("@")[0],
            mat_khau_hash=get_password_hash(random.randbytes(16).hex())
        )
        db.add(new_u)
        db.commit()
        db.refresh(new_u)
        user = new_u

    access_token = create_access_token(data={"sub": user.email, "user_id": user.ma_nd})
    ACTIVE_SESSIONS[user.email] = access_token
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/gui-otp")
def legacy_gui_otp(payload: dict, db: Session = Depends(get_db)):
    from app.controllers.auth_controller import gui_otp
    return gui_otp(payload, db)

@app.post("/xac-nhan-otp")
def legacy_xac_nhan_otp(payload: dict, db: Session = Depends(get_db)):
    from app.controllers.auth_controller import xac_nhan_otp
    return xac_nhan_otp(payload, db)

@app.post("/gui-otp-dang-ky")
def legacy_gui_otp_dang_ky(payload: dict, db: Session = Depends(get_db)):
    from app.controllers.auth_controller import gui_otp_dang_ky
    return gui_otp_dang_ky(payload, db)

@app.post("/xac-nhan-dang-ky")
def legacy_xac_nhan_dang_ky(payload: dict, db: Session = Depends(get_db)):
    from app.controllers.auth_controller import xac_nhan_dang_ky
    return xac_nhan_dang_ky(payload, db)

@app.post("/dang-ky", status_code=status.HTTP_201_CREATED)
def legacy_dang_ky(user: dict, db: Session = Depends(get_db)):
    username = user.get("username") or user.get("email")
    if not username:
        raise HTTPException(status_code=400, detail="Thiếu tên đăng nhập hoặc email")
    if db.query(NguoiDung).filter(NguoiDung.email == username).first():
        raise HTTPException(status_code=400, detail="Email hoặc tài khoản đã tồn tại")
    new_u = NguoiDung(
        email=username,
        ho_ten=user.get("full_name") or username.split("@")[0],
        mat_khau_hash=get_password_hash(user.get("password", "123"))
    )
    db.add(new_u)
    db.commit()
    db.refresh(new_u)
    return {"thong_bao": "OK"}

@app.post("/dang-nhap", response_model=Token)
def legacy_dang_nhap(user: UserCreate, db: Session = Depends(get_db)):
    db_u = db.query(NguoiDung).filter(NguoiDung.email == user.username).first()
    if not db_u or not verify_password(user.password, db_u.mat_khau_hash):
        raise HTTPException(status_code=401, detail="Sai tài khoản hoặc mật khẩu")
    token = create_access_token(data={"sub": db_u.email, "user_id": db_u.ma_nd})
    ACTIVE_SESSIONS[db_u.email] = token
    # Khi đăng nhập vào: kiểm tra cảnh báo hạn mức (>=90%) và đưa 1 thông báo vào phần thông báo
    NganSachService.check_and_generate_login_budget_notifications(db, db_u)
    return {"access_token": token, "token_type": "bearer"}

@app.post("/cap-nhat-ho-so")
def cap_nhat_ho_so(data: dict, db: Session = Depends(get_db), current_user: NguoiDung = Depends(get_current_active_user)):
    current_user.ho_ten = data.get("full_name", current_user.ho_ten)
    current_user.dob = data.get("dob", current_user.dob)
    current_user.occupation = data.get("occupation", current_user.occupation)
    current_user.goals = data.get("goals", current_user.goals)
    db.commit()
    return {"thong_bao": "OK"}

@app.get("/check-session")
def api_check_session(db: Session = Depends(get_db), current_user: NguoiDung = Depends(get_current_active_user)):
    NganSachService.check_and_generate_login_budget_notifications(db, current_user)
    return {"status": "valid", "user": current_user.email}

@app.get("/tai-khoan")
def lay_thong_tin_tai_khoan(current_user: NguoiDung = Depends(get_current_active_user)):
    return {
        "full_name": current_user.ho_ten,
        "email": current_user.email,
        "dob": current_user.dob,
        "occupation": current_user.occupation,
        "goals": current_user.goals
    }

@app.put("/tai-khoan")
def cap_nhat_tai_khoan_legacy(payload: dict, db: Session = Depends(get_db), current_user: NguoiDung = Depends(get_current_active_user)):
    if "full_name" in payload or "ho_ten" in payload:
        current_user.ho_ten = (payload.get("full_name") or payload.get("ho_ten") or "").strip()
    if "dob" in payload or "ngay_sinh" in payload:
        current_user.dob = payload.get("dob") or payload.get("ngay_sinh")
    if "occupation" in payload or "nghe_nghiep" in payload:
        current_user.occupation = payload.get("occupation") or payload.get("nghe_nghiep")
    if "goals" in payload or "muc_tieu" in payload:
        current_user.goals = payload.get("goals") or payload.get("muc_tieu")
    db.commit()
    db.refresh(current_user)
    return {
        "full_name": current_user.ho_ten,
        "email": current_user.email,
        "dob": current_user.dob,
        "occupation": current_user.occupation,
        "goals": current_user.goals
    }

@app.post("/doi-mat-khau")
def doi_mat_khau(payload: dict, db: Session = Depends(get_db), current_user: NguoiDung = Depends(get_current_active_user)):
    if not verify_password(payload.get("old_pass", ""), current_user.mat_khau_hash):
        raise HTTPException(status_code=400, detail="Mật khẩu cũ không chính xác")
    current_user.mat_khau_hash = get_password_hash(payload.get("new_pass"))
    db.commit()
    return {"thong_bao": "OK"}

def _format_dm(c: DanhMuc):
    return {
        "id": c.ma_dm,
        "ma_dm": c.ma_dm,
        "name": c.ten_dm,
        "ten_dm": c.ten_dm,
        "type": c.loai_dm,
        "loai_dm": c.loai_dm,
        "budget_limit": c.han_muc or 0.0,
        "han_muc": c.han_muc or 0.0,
        "icon": c.icon or "tag",
        "mau_sac": c.mau_sac or "#0ea5e9",
        "ma_nd": c.ma_nd,
        "user_id": c.ma_nd
    }

def _get_wallet_balance(db: Session, ma_nd: int) -> float:
    return NganSachService.tinh_so_du_vi_chinh(db, ma_nd)

@app.post("/danh-muc", status_code=status.HTTP_201_CREATED)
def tao_danh_muc_legacy(cat: dict, db: Session = Depends(get_db), current_user: NguoiDung = Depends(get_current_active_user)):
    ctype = cat.get("type") or cat.get("loai_dm") or "chi"
    amount = float(cat.get("budget_limit") or cat.get("han_muc") or cat.get("amount") or cat.get("so_tien") or 0.0)
    cname = (cat.get("name") or cat.get("ten_dm") or "").strip()

    if not cname:
        raise HTTPException(status_code=400, detail="Vui lòng nhập tên danh mục")

    if ctype == 'chi':
        limit = amount
        if limit > 0:
            current_balance = _get_wallet_balance(db, current_user.ma_nd)
            if limit > current_balance:
                raise HTTPException(
                    status_code=400,
                    detail=f"Số dư ví chính không đủ để trích cấp cho hũ '{cname}'! Số dư hiện tại: {max(0.0, current_balance):,.0f} đ, cần cấp: {limit:,.0f} đ."
                )
        new_c = DanhMuc(ten_dm=cname, loai_dm=ctype, han_muc=limit, ma_nd=current_user.ma_nd)
        db.add(new_c)
        db.commit()
        db.refresh(new_c)
        return _format_dm(new_c)
    else:  # ctype == 'thu'
        new_c = DanhMuc(ten_dm=cname, loai_dm=ctype, han_muc=0.0, ma_nd=current_user.ma_nd)
        db.add(new_c)
        db.commit()
        db.refresh(new_c)

        # Khi thêm danh mục thu kèm số tiền, tạo giao dịch thu để cộng ngay vào ví chính
        if amount > 0:
            tx = GiaoDich(
                so_tien=amount,
                loai_gd="thu",
                ghi_chu=f"Khoản thu danh mục: {cname}",
                ma_dm=new_c.ma_dm,
                ma_nd=current_user.ma_nd,
                ngay_gd=datetime.now()
            )
            db.add(tx)
            db.commit()

        return _format_dm(new_c)

@app.put("/danh-muc/{cat_id}")
def sua_danh_muc_legacy(cat_id: int, cat: dict, db: Session = Depends(get_db), current_user: NguoiDung = Depends(get_current_active_user)):
    c = db.query(DanhMuc).filter(DanhMuc.ma_dm == cat_id, DanhMuc.ma_nd == current_user.ma_nd).first()
    if not c:
        raise HTTPException(status_code=404, detail="Không tìm thấy danh mục")
    if "name" in cat or "ten_dm" in cat:
        c.ten_dm = cat.get("name") or cat.get("ten_dm")
    if "type" in cat or "loai_dm" in cat:
        c.loai_dm = cat.get("type") or cat.get("loai_dm")
    if "budget_limit" in cat or "han_muc" in cat:
        new_limit = float(cat.get("budget_limit") or cat.get("han_muc") or 0.0) if c.loai_dm == 'chi' else 0.0
        if c.loai_dm == 'chi':
            # Kiểm tra: Hạn mức mới không được nhỏ hơn số tiền đã chi trong danh mục này
            txs = db.query(GiaoDich).filter(GiaoDich.ma_dm == cat_id, GiaoDich.loai_gd == "chi").all()
            spent = sum(float(t.so_tien or 0.0) for t in txs)
            if new_limit < spent:
                raise HTTPException(
                    status_code=400,
                    detail=f"Hạn mức mới ({new_limit:,.0f} đ) không được nhỏ hơn số tiền đã chi ({spent:,.0f} đ) trong danh mục này! Bạn chỉ có thể nâng hạn mức chứ không được giảm nhỏ hơn số tiền đã chi."
                )

            old_limit = float(c.han_muc or 0.0)
            diff = new_limit - old_limit
            if diff > 0:
                current_balance = _get_wallet_balance(db, current_user.ma_nd)
                if diff > current_balance:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Số dư ví chính không đủ để tăng hạn mức thêm {diff:,.0f} đ! Số dư còn lại: {max(0.0, current_balance):,.0f} đ."
                    )
            c.han_muc = new_limit
        else:
            c.han_muc = 0.0
    db.commit()
    return _format_dm(c)

@app.delete("/danh-muc/{cat_id}")
def xoa_danh_muc_legacy(cat_id: int, db: Session = Depends(get_db), current_user: NguoiDung = Depends(get_current_active_user)):
    c = db.query(DanhMuc).filter(DanhMuc.ma_dm == cat_id, DanhMuc.ma_nd == current_user.ma_nd).first()
    if not c:
        raise HTTPException(status_code=404, detail="Không tìm thấy danh mục")

    cat_name = c.ten_dm
    cat_type = c.loai_dm
    cat_limit = float(c.han_muc or 0.0)

    spent = 0.0
    if cat_type == "chi":
        txs = db.query(GiaoDich).filter(GiaoDich.ma_dm == cat_id, GiaoDich.loai_gd == "chi").all()
        spent = sum(t.so_tien for t in txs)
    remaining = max(0.0, cat_limit - spent)

    db.query(GiaoDich).filter(GiaoDich.ma_dm == cat_id).delete()
    db.query(NganSach).filter(NganSach.ma_dm == cat_id).delete()
    db.delete(c)
    db.commit()

    if cat_type == "chi" and remaining > 0:
        save_notification(
            db, current_user.ma_nd,
            "💰 Hoàn Trả Hạn Mức Về Ví Chính",
            f"Đã xóa danh mục '{cat_name}'. Số tiền hạn mức khả dụng còn lại {remaining:,.0f} đ đã được hoàn trả về ví chính để bạn sử dụng cho các mục tiêu chi tiêu tiếp theo."
        )

    return {
        "thong_bao": "OK",
        "ten_dm": cat_name,
        "so_tien_hoan": remaining
    }

@app.get("/danh-muc")
def lay_danh_sach_danh_muc_legacy(db: Session = Depends(get_db), current_user: NguoiDung = Depends(get_current_active_user)):
    cats = db.query(DanhMuc).filter(DanhMuc.ma_nd == current_user.ma_nd).all()
    return [_format_dm(c) for c in cats]

@app.post("/quen-mat-khau")
def quen_mat_khau_legacy(payload: dict, db: Session = Depends(get_db)):
    from app.controllers.auth_controller import quen_mat_khau
    return quen_mat_khau(payload, db)

@app.post("/dat-lai-mat-khau")
def dat_lai_mat_khau_legacy(payload: dict, db: Session = Depends(get_db)):
    from app.controllers.auth_controller import dat_lai_mat_khau
    return dat_lai_mat_khau(payload, db)

def _format_tx(t: GiaoDich):
    return {
        "id": t.ma_gd,
        "ma_gd": t.ma_gd,
        "amount": t.so_tien,
        "so_tien": t.so_tien,
        "type": t.loai_gd,
        "loai_gd": t.loai_gd,
        "category_id": t.ma_dm,
        "ma_dm": t.ma_dm,
        "date": t.ngay_gd.isoformat() if t.ngay_gd else None,
        "ngay_gd": t.ngay_gd.isoformat() if t.ngay_gd else None,
        "note": t.ghi_chu or "",
        "ghi_chu": t.ghi_chu or "",
        "user_id": t.ma_nd,
        "ma_nd": t.ma_nd
    }

def _format_savings(g: MucTieuTietKiem):
    return {
        "id": g.ma_mt,
        "ma_mt": g.ma_mt,
        "title": g.ten_muc_tieu,
        "ten_muc_tieu": g.ten_muc_tieu,
        "target_amount": g.so_tien_muc_tieu,
        "so_tien_muc_tieu": g.so_tien_muc_tieu,
        "current_amount": g.so_tien_hien_tai,
        "so_tien_hien_tai": g.so_tien_hien_tai,
        "deadline": g.han_chot,
        "han_chot": g.han_chot,
        "user_id": g.ma_nd,
        "ma_nd": g.ma_nd,
        "trang_thai": g.trang_thai
    }

@app.post("/giao-dich", status_code=status.HTTP_201_CREATED)
def tao_giao_dich_legacy(payload: dict, db: Session = Depends(get_db), current_user: NguoiDung = Depends(get_current_active_user)):
    amount = float(payload.get("amount") or payload.get("so_tien") or 0.0)
    ttype = payload.get("type") or payload.get("loai_gd")
    cat_id = int(payload.get("category_id") or payload.get("ma_dm"))

    if amount <= 0:
        raise HTTPException(status_code=400, detail="Số tiền giao dịch phải lớn hơn 0")

    cat = db.query(DanhMuc).filter(DanhMuc.ma_dm == cat_id, DanhMuc.ma_nd == current_user.ma_nd).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Không tìm thấy danh mục")

    parsed_date = datetime.now()
    if payload.get("date") or payload.get("ngay_gd"):
        d_val = payload.get("date") or payload.get("ngay_gd")
        if isinstance(d_val, str):
            try:
                parsed_date = datetime.fromisoformat(d_val.replace('Z', '+00:00'))
            except Exception:
                pass
    if parsed_date and parsed_date.tzinfo is not None:
        parsed_date = parsed_date.replace(tzinfo=None)

    tx = GiaoDich(
        so_tien=amount,
        loai_gd=ttype,
        ghi_chu=payload.get("note") or payload.get("ghi_chu") or "",
        ma_dm=cat_id,
        ma_nd=current_user.ma_nd,
        ngay_gd=parsed_date
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    # NFR-02: Kiểm tra cảnh báo ngân sách (đã được lưu/cập nhật 1 thông báo duy nhất trong NganSachService)
    res = _format_tx(tx)
    if ttype == 'chi':
        canh_bao = NganSachService.kiem_tra_ngan_sach(db, current_user.ma_nd, cat_id, parsed_date)
        res["canh_bao"] = {
            "co_canh_bao": canh_bao.co_canh_bao,
            "vuot_ngan_sach": canh_bao.vuot_ngan_sach,
            "ty_le": canh_bao.ty_le,
            "han_muc": canh_bao.han_muc,
            "so_tien_da_chi": canh_bao.so_tien_da_chi,
            "thong_bao": canh_bao.thong_bao,
            "ten_dm": cat.ten_dm
        }

    return res

@app.get("/giao-dich")
def lay_danh_sach_giao_dich_legacy(db: Session = Depends(get_db), current_user: NguoiDung = Depends(get_current_active_user)):
    txs = db.query(GiaoDich).filter(GiaoDich.ma_nd == current_user.ma_nd).order_by(GiaoDich.ngay_gd.desc(), GiaoDich.ma_gd.desc()).all()
    return [_format_tx(t) for t in txs]

@app.put("/giao-dich/{tx_id}")
def sua_giao_dich_legacy(tx_id: int, payload: dict, db: Session = Depends(get_db), current_user: NguoiDung = Depends(get_current_active_user)):
    tx = db.query(GiaoDich).filter(GiaoDich.ma_gd == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Không tìm thấy giao dịch")
    if tx.ma_nd != current_user.ma_nd:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập giao dịch của người khác")

    amount = payload.get("so_tien") or payload.get("amount")
    if amount is not None:
        try:
            so_tien = float(amount)
            if so_tien <= 0:
                raise HTTPException(status_code=400, detail="Số tiền giao dịch phải lớn hơn 0")
            tx.so_tien = so_tien
        except ValueError:
            raise HTTPException(status_code=400, detail="Số tiền không hợp lệ")

    if "loai_gd" in payload or "type" in payload:
        tx.loai_gd = payload.get("loai_gd") or payload.get("type")
    if "ma_dm" in payload or "category_id" in payload:
        tx.ma_dm = int(payload.get("ma_dm") or payload.get("category_id"))
    if "ghi_chu" in payload or "note" in payload:
        tx.ghi_chu = payload.get("ghi_chu") or payload.get("note")

    if "ngay_gd" in payload or "date" in payload:
        d_val = payload.get("ngay_gd") or payload.get("date")
        if isinstance(d_val, str) and d_val:
            try:
                parsed_date = datetime.fromisoformat(d_val.replace('Z', '+00:00'))
                if parsed_date and parsed_date.tzinfo is not None:
                    parsed_date = parsed_date.replace(tzinfo=None)
                tx.ngay_gd = parsed_date
            except Exception:
                pass

    db.commit()
    db.refresh(tx)
    res = _format_tx(tx)
    if tx.loai_gd == "chi":
        cat = db.query(DanhMuc).filter(DanhMuc.ma_dm == tx.ma_dm).first()
        if cat and cat.han_muc and cat.han_muc > 0:
            canh_bao = NganSachService.kiem_tra_ngan_sach(db, current_user.ma_nd, tx.ma_dm, tx.ngay_gd or datetime.now())
            res["canh_bao"] = {
                "co_canh_bao": canh_bao.co_canh_bao,
                "vuot_ngan_sach": canh_bao.vuot_ngan_sach,
                "ty_le": canh_bao.ty_le,
                "han_muc": canh_bao.han_muc,
                "so_tien_da_chi": canh_bao.so_tien_da_chi,
                "thong_bao": canh_bao.thong_bao,
                "ten_dm": cat.ten_dm
            }
    return res

@app.delete("/giao-dich/{tx_id}")
def xoa_giao_dich_legacy(tx_id: int, db: Session = Depends(get_db), current_user: NguoiDung = Depends(get_current_active_user)):
    tx = db.query(GiaoDich).filter(GiaoDich.ma_gd == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Không tìm thấy giao dịch")
    if tx.ma_nd != current_user.ma_nd:
        raise HTTPException(status_code=403, detail="Không có quyền xóa giao dịch của người khác")

    db.delete(tx)
    db.commit()
    return {"thong_bao": "Xóa giao dịch thành công"}

@app.get("/thong-ke")
def thong_ke_tai_chinh_legacy(db: Session = Depends(get_db), current_user: NguoiDung = Depends(get_current_active_user)):
    txs = db.query(GiaoDich).filter(GiaoDich.ma_nd == current_user.ma_nd).all()
    categories = db.query(DanhMuc).filter(DanhMuc.ma_nd == current_user.ma_nd).all()
    savings_goals = db.query(MucTieuTietKiem).filter(MucTieuTietKiem.ma_nd == current_user.ma_nd).all()

    # Không cộng đúp tiền hoàn từ hũ tiết kiệm đã xóa vào thu nhập cơ bản
    t_thu = sum(t.so_tien for t in txs if t.loai_gd == "thu" and not (t.ghi_chu and ("Hoàn tiền từ hũ tiết kiệm" in t.ghi_chu or "Hoàn Trả Hạn Mức" in t.ghi_chu)))
    # Không tính các giao dịch tiền đã hoàn về ví chính (hũ tiết kiệm đã xóa / hoàn trả hạn mức) vào tổng chi
    t_chi = sum(t.so_tien for t in txs if t.loai_gd == "chi" and not (t.ghi_chu and ("(đã xoá)" in t.ghi_chu.lower() or "(đã xóa)" in t.ghi_chu.lower() or "hoàn trả" in t.ghi_chu.lower() or "hoàn tiền" in t.ghi_chu.lower())))
    total_savings = sum(g.so_tien_hien_tai for g in savings_goals)

    # Tính tổng tiền phân bổ cho các hũ chi tiêu:
    spent_by_cat = {}
    for t in txs:
        if t.loai_gd == "chi" and not (t.ghi_chu and t.ghi_chu.startswith("Trích quỹ tiết kiệm")):
            spent_by_cat[t.ma_dm] = spent_by_cat.get(t.ma_dm, 0.0) + t.so_tien

    total_allocated_chi = 0.0
    for c in categories:
        if c.loai_dm == "chi" and c.ten_dm != "Tiết kiệm":
            c_spent = spent_by_cat.get(c.ma_dm, 0.0)
            if c.han_muc and c.han_muc > 0:
                total_allocated_chi += max(float(c.han_muc), c_spent)
            else:
                total_allocated_chi += c_spent

    # Số dư ví chính = Tổng thu - Tổng tiền cấp cho các hũ chi tiêu - Tổng tiền vào tiết kiệm
    so_du_vi_chinh = NganSachService.tinh_so_du_vi_chinh(db, current_user.ma_nd)

    return {
        "tong_thu": t_thu,
        "tong_chi": t_chi,
        "so_du": so_du_vi_chinh,
        "tong_cap_hu": total_allocated_chi,
        "tong_tiet_kiem": total_savings
    }

@app.get("/tiet-kiem")
def lay_tiet_kiem_legacy(db: Session = Depends(get_db), current_user: NguoiDung = Depends(get_current_active_user)):
    goals = db.query(MucTieuTietKiem).filter(MucTieuTietKiem.ma_nd == current_user.ma_nd).all()
    # Sắp xếp: hũ chưa hoàn thành (current < target) lên trước, hũ đã hoàn thành (current >= target) xuống dưới
    goals.sort(key=lambda g: (1 if float(g.so_tien_hien_tai or 0.0) >= float(g.so_tien_muc_tieu or 1.0) else 0, g.ma_mt))
    return [_format_savings(g) for g in goals]

def validate_savings_deadline(deadline_raw):
    if not deadline_raw:
        return None
    dl_str = str(deadline_raw).strip()
    if not dl_str:
        return None
    if "/" in dl_str:
        parts = dl_str.split("/")
        if len(parts) == 3:
            if len(parts[2]) == 4:
                dl_str = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
            elif len(parts[0]) == 4:
                dl_str = f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
    clean_date = dl_str[:10]
    today_str = datetime.now().strftime("%Y-%m-%d")
    if clean_date < today_str:
        raise HTTPException(status_code=400, detail="Hạn chót phải là ngày hôm nay hoặc thời gian trong tương lai, không được đặt ngày trong quá khứ.")
    return clean_date

@app.post("/tiet-kiem")
def tao_tiet_kiem_legacy(goal: dict, db: Session = Depends(get_db), current_user: NguoiDung = Depends(get_current_active_user)):
    title = goal.get("title") or goal.get("ten_muc_tieu")
    target = float(goal.get("target_amount") or goal.get("so_tien_muc_tieu"))
    deadline = goal.get("deadline") or goal.get("han_chot")

    if not title:
        raise HTTPException(status_code=400, detail="Vui lòng nhập tên mục tiêu tiết kiệm")
    if target <= 0:
        raise HTTPException(status_code=400, detail="Số tiền mục tiêu phải lớn hơn 0")

    valid_deadline = validate_savings_deadline(deadline)

    new_g = MucTieuTietKiem(ten_muc_tieu=title, so_tien_muc_tieu=target, han_chot=valid_deadline, ma_nd=current_user.ma_nd)
    db.add(new_g)
    db.commit()
    db.refresh(new_g)
    return _format_savings(new_g)

@app.post("/tiet-kiem/{goal_id}/nop")
def nop_tiet_kiem_legacy(goal_id: int, payload: dict, db: Session = Depends(get_db), current_user: NguoiDung = Depends(get_current_active_user)):
    amount = float(payload.get("amount") or payload.get("so_tien") or 0.0)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Số tiền trích nộp phải lớn hơn 0")

    goal = db.query(MucTieuTietKiem).filter(MucTieuTietKiem.ma_mt == goal_id, MucTieuTietKiem.ma_nd == current_user.ma_nd).first()
    if not goal:
        raise HTTPException(status_code=404)

    # Kiểm tra số dư ví chính khả dụng trước khi trích nộp
    current_balance = NganSachService.tinh_so_du_vi_chinh(db, current_user.ma_nd)
    if amount > current_balance:
        raise HTTPException(
            status_code=400,
            detail=f"Số dư ví chính không đủ để trích vào quỹ tiết kiệm! (Số dư khả dụng: {max(0.0, current_balance):,.0f} đ)"
        )

    if goal.so_tien_hien_tai >= goal.so_tien_muc_tieu:
        raise HTTPException(status_code=400, detail="Mục tiêu này đã hoàn thành 100%!")

    if goal.so_tien_hien_tai + amount > goal.so_tien_muc_tieu:
        max_can_nop = goal.so_tien_muc_tieu - goal.so_tien_hien_tai
        raise HTTPException(status_code=400, detail=f"Số tiền trích vượt quá số còn lại để đạt 100%. Tối đa bạn chỉ có thể trích thêm {max_can_nop:,.0f} đ.")

    dm_sav = db.query(DanhMuc).filter(DanhMuc.ma_nd == current_user.ma_nd, DanhMuc.ten_dm == "Tiết kiệm").first()
    if not dm_sav:
        dm_sav = DanhMuc(ten_dm="Tiết kiệm", loai_dm="chi", han_muc=0.0, ma_nd=current_user.ma_nd)
        db.add(dm_sav)
        db.commit()
        db.refresh(dm_sav)

    tx = GiaoDich(so_tien=amount, loai_gd="chi", ghi_chu=f"Mục tiêu: {goal.ten_muc_tieu}", ma_dm=dm_sav.ma_dm, ma_nd=current_user.ma_nd, ngay_gd=datetime.now())
    db.add(tx)

    goal.so_tien_hien_tai += amount
    db.commit()

    pct = round((goal.so_tien_hien_tai / goal.so_tien_muc_tieu) * 100)
    if pct >= 90:
        if pct >= 100:
            notif_title = "🎉 Chúc Mừng Hoàn Thành Mục Tiêu Tiết Kiệm!"
            notif_msg = f"Tuyệt vời! Bạn đã hoàn thành 100% mục tiêu '{goal.ten_muc_tieu}' ({goal.so_tien_hien_tai:,.0f}đ / {goal.so_tien_muc_tieu:,.0f}đ)! Hãy tiếp tục phát huy và cố gắng hoàn thành thêm nhiều mục tiêu tài chính khác nhé!"
        else:
            notif_title = "🌟 Động Viên: Sắp Đạt Mục Tiêu Tiết Kiệm!"
            notif_msg = f"Cố lên! Hũ tiết kiệm '{goal.ten_muc_tieu}' của bạn đã đạt {pct}% ({goal.so_tien_hien_tai:,.0f}đ / {goal.so_tien_muc_tieu:,.0f}đ)! Bạn sắp chạm đích rồi, hãy tiếp tục duy trì và cố gắng hoàn thành nhé!"
        save_notification(db, current_user.ma_nd, notif_title, notif_msg)

    return {
        "thong_bao": "OK",
        "pct": pct,
        "current_amount": goal.so_tien_hien_tai,
        "target_amount": goal.so_tien_muc_tieu,
        "title": goal.ten_muc_tieu
    }

@app.put("/tiet-kiem/{goal_id}")
def sua_tiet_kiem_legacy(goal_id: int, payload: dict, db: Session = Depends(get_db), current_user: NguoiDung = Depends(get_current_active_user)):
    goal = db.query(MucTieuTietKiem).filter(MucTieuTietKiem.ma_mt == goal_id, MucTieuTietKiem.ma_nd == current_user.ma_nd).first()
    if not goal:
        raise HTTPException(status_code=404)
    if "title" in payload or "ten_muc_tieu" in payload:
        goal.ten_muc_tieu = payload.get("title") or payload.get("ten_muc_tieu")
    if "target_amount" in payload or "so_tien_muc_tieu" in payload:
        new_target = float(payload.get("target_amount") or payload.get("so_tien_muc_tieu"))
        curr_amt = float(goal.so_tien_hien_tai or 0.0)
        if new_target < curr_amt:
            raise HTTPException(status_code=400, detail=f"Số tiền mục tiêu mới không được nhỏ hơn số tiền đang có trong hũ ({curr_amt:,.0f} đ)!")
        goal.so_tien_muc_tieu = new_target
        if goal.so_tien_hien_tai >= goal.so_tien_muc_tieu:
            goal.trang_thai = "hoan_thanh"
        else:
            goal.trang_thai = "dang_thuc_hien"
    if "deadline" in payload or "han_chot" in payload:
        dl = payload.get("deadline") if "deadline" in payload else payload.get("han_chot")
        goal.han_chot = validate_savings_deadline(dl)
    db.commit()
    return {"thong_bao": "OK"}

@app.delete("/tiet-kiem/{goal_id}")
def xoa_tiet_kiem_legacy(goal_id: int, db: Session = Depends(get_db), current_user: NguoiDung = Depends(get_current_active_user)):
    goal = db.query(MucTieuTietKiem).filter(MucTieuTietKiem.ma_mt == goal_id, MucTieuTietKiem.ma_nd == current_user.ma_nd).first()
    if not goal:
        raise HTTPException(status_code=404)

    refund_amt = float(goal.so_tien_hien_tai or 0.0)
    goal_title = goal.ten_muc_tieu

    # Cập nhật các giao dịch trước đây liên quan đến mục tiêu này thành (đã xóa)
    goal_txs = db.query(GiaoDich).filter(
        GiaoDich.ma_nd == current_user.ma_nd,
        GiaoDich.ghi_chu.like(f"%{goal_title}%")
    ).all()
    for t in goal_txs:
        t.ghi_chu = f"Mục tiêu: {goal_title} (đã xoá)"

    if refund_amt > 0:
        save_notification(
            db, current_user.ma_nd,
            "💰 Hoàn Tiền Hũ Tiết Kiệm Về Ví Chính",
            f"Đã hoàn trả {refund_amt:,.0f} đ từ hũ '{goal_title}' về ví chính để bạn sử dụng cho các mục đích khác."
        )

    db.delete(goal)
    db.commit()
    return {
        "thong_bao": "OK",
        "refund_amount": refund_amt,
        "refunded": refund_amt,
        "title": goal_title
    }

@app.post("/ai-tro-ly")
def ai_tro_ly_legacy(payload: dict, db: Session = Depends(get_db), current_user: NguoiDung = Depends(get_current_active_user)):
    cau_hoi = payload.get("cau_hoi", "").strip()
    lich_su_chat = payload.get("lich_su_chat") or payload.get("history") or []
    tra_loi = AIService.hoi_dap_ai(db=db, ma_nd=current_user.ma_nd, cau_hoi=cau_hoi, lich_su_chat=lich_su_chat)
    return {"tra_loi": tra_loi}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    is_dev = os.environ.get("PORT") is None
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=is_dev)