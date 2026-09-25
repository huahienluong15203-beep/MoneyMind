from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import (
    get_password_hash, verify_password,
    create_access_token, create_refresh_token, verify_refresh_token
)
from app.core.config import settings
from app.models.nguoi_dung import NguoiDung
from app.schemas.auth import DangKyRequest, DangNhapRequest, TokenResponse, RefreshTokenRequest
from app.services.ngan_sach_service import NganSachService

router = APIRouter(prefix="/api/auth", tags=["Xác thực tài khoản (UC001)"])

@router.post("/dang-ky", status_code=status.HTTP_201_CREATED, summary="Đăng ký tài khoản mới (UC001)")
def dang_ky(payload: DangKyRequest, db: Session = Depends(get_db)):
    """
    UC001 & TC-01:
    Kiểm tra email chưa tồn tại.
    Mã hoá mật khẩu bằng Bcrypt (BR-02, NFR-05).
    """
    existing_user = db.query(NguoiDung).filter(NguoiDung.email == payload.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email đã được sử dụng. Vui lòng chọn một email khác."
        )

    new_user = NguoiDung(
        email=payload.email,
        ho_ten=payload.ho_ten or payload.email.split("@")[0],
        mat_khau_hash=get_password_hash(payload.password),
        trang_thai="hoat_dong",
        so_lan_sai=0,
        ngay_tao=datetime.utcnow()
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "thong_bao": "Đăng ký tài khoản thành công",
        "ma_nd": new_user.ma_nd,
        "email": new_user.email
    }

@router.post("/gui-otp-dang-ky", summary="Gửi mã OTP xác nhận đăng ký về Gmail thật")
def gui_otp_dang_ky(payload: dict, db: Session = Depends(get_db)):
    email = payload.get("email", "").strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Vui lòng nhập địa chỉ Gmail hợp lệ.")

    existing_user = db.query(NguoiDung).filter(NguoiDung.email == email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email này đã được sử dụng. Vui lòng đăng nhập hoặc chọn email khác."
        )

    from app.services.email_service import EmailService
    from app.models.xac_nhan_otp import XacNhanOTP

    otp_code = EmailService.generate_otp()
    het_han = datetime.utcnow() + timedelta(minutes=10)

    otp_record = XacNhanOTP(
        email=email,
        otp_code=otp_code,
        het_han=het_han,
        da_dung=False
    )
    db.add(otp_record)
    db.commit()

    # Gửi email trong luồng nền (background thread) để không bắt người dùng phải chờ kết nối SMTP (20s+)
    import threading
    t = threading.Thread(
        target=EmailService.send_registration_otp,
        args=(email, otp_code),
        daemon=True
    )
    t.start()

    msg = f"Mã xác nhận OTP đã được gửi đến hòm thư {email}. Vui lòng kiểm tra hộp thư đến hoặc thư rác (Spam)."
    return {
        "thong_bao": msg,
        "email": email,
        "dev_otp": otp_code
    }

@router.post("/xac-nhan-dang-ky", summary="Xác nhận mã OTP và hoàn tất tạo tài khoản")
def xac_nhan_dang_ky(payload: dict, db: Session = Depends(get_db)):
    email = payload.get("email", "").strip().lower()
    otp_code = str(payload.get("otp") or payload.get("ma_otp") or "").strip()
    password = payload.get("password") or ""
    full_name = payload.get("full_name") or payload.get("ho_ten") or email.split("@")[0]

    if not email or not otp_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Vui lòng nhập đầy đủ Email và mã OTP.")

    if not password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Vui lòng cung cấp mật khẩu tài khoản.")

    from app.models.xac_nhan_otp import XacNhanOTP
    from app.models.danh_muc import DanhMuc

    record = db.query(XacNhanOTP).filter(
        XacNhanOTP.email == email,
        XacNhanOTP.otp_code == otp_code,
        XacNhanOTP.da_dung == False,
        XacNhanOTP.het_han > datetime.utcnow()
    ).order_by(XacNhanOTP.id.desc()).first()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã xác nhận OTP không chính xác hoặc đã hết hạn. Vui lòng kiểm tra lại Gmail."
        )

    if db.query(NguoiDung).filter(NguoiDung.email == email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email này đã được sử dụng.")

    record.da_dung = True
    db.commit()

    new_user = NguoiDung(
        email=email,
        ho_ten=full_name,
        mat_khau_hash=get_password_hash(password),
        trang_thai="hoat_dong",
        so_lan_sai=0,
        ngay_tao=datetime.utcnow()
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    default_cats = [
        ("Ăn uống", "chi", "utensils", "#f43f5e", 0.0),
        ("Đi lại", "chi", "car", "#0ea5e9", 0.0),
        ("Mua sắm", "chi", "shopping-bag", "#f59e0b", 0.0),
        ("Tiền lương", "thu", "wallet", "#10b981", 0.0)
    ]
    for cname, ctype, cicon, ccolor, climit in default_cats:
        cat = DanhMuc(ma_nd=new_user.ma_nd, ten_dm=cname, loai_dm=ctype, icon=cicon, mau_sac=ccolor, han_muc=climit)
        db.add(cat)
    db.commit()

    access_token = create_access_token(data={"sub": new_user.email, "user_id": new_user.ma_nd})
    refresh_token = create_refresh_token(data={"sub": new_user.email, "user_id": new_user.ma_nd})

    return {
        "thong_bao": "Đăng ký tài khoản thành công",
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": refresh_token,
        "user": {
            "ma_nd": new_user.ma_nd,
            "email": new_user.email,
            "ho_ten": new_user.ho_ten
        }
    }

@router.post("/dang-nhap", response_model=TokenResponse, summary="Đăng nhập tài khoản (UC001)")
def dang_nhap(payload: DangNhapRequest, db: Session = Depends(get_db)):
    """
    UC001 & TC-02:
    Đăng nhập bằng email và mật khẩu.
    Nếu sai mật khẩu 5 lần liên tiếp trong 15 phút, tài khoản sẽ bị tạm khóa (A2, TC-02).
    """
    user = db.query(NguoiDung).filter(NguoiDung.email == payload.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email hoặc mật khẩu không chính xác"
        )

    # Kiểm tra trạng thái khóa tài khoản
    if user.trang_thai == "khoa":
        if user.khoa_den and datetime.utcnow() < user.khoa_den:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Tài khoản đang bị tạm khóa do nhập sai mật khẩu nhiều lần. Vui lòng thử lại sau {settings.LOCKOUT_MINUTES} phút."
            )
        else:
            # Hết thời gian khóa, tự động mở
            user.trang_thai = "hoat_dong"
            user.so_lan_sai = 0
            user.khoa_den = None
            db.commit()

    # Kiểm tra mật khẩu
    if not verify_password(payload.password, user.mat_khau_hash):
        user.so_lan_sai = (user.so_lan_sai or 0) + 1
        if user.so_lan_sai >= settings.MAX_FAILED_LOGINS:
            user.trang_thai = "khoa"
            user.khoa_den = datetime.utcnow() + timedelta(minutes=settings.LOCKOUT_MINUTES)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Bạn đã nhập sai mật khẩu {user.so_lan_sai} lần liên tiếp. Tài khoản đã bị tạm khóa trong {settings.LOCKOUT_MINUTES} phút."
            )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Email hoặc mật khẩu không chính xác (Lần thử {user.so_lan_sai}/{settings.MAX_FAILED_LOGINS})"
        )

    # Đăng nhập thành công -> Reset số lần sai
    user.so_lan_sai = 0
    user.khoa_den = None
    db.commit()

    access_token = create_access_token(data={"sub": user.email, "user_id": user.ma_nd})
    refresh_token = create_refresh_token(data={"sub": user.email, "user_id": user.ma_nd})

    NganSachService.check_and_generate_login_budget_notifications(db, user)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        refresh_token=refresh_token
    )

@router.post("/refresh", response_model=TokenResponse, summary="Cấp lại access token từ refresh token (UC001)")
def refresh_token(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Cấp lại access token mới khi access token cũ hết hạn"""
    email = verify_refresh_token(payload.refresh_token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token không hợp lệ hoặc đã hết hạn"
        )

    user = db.query(NguoiDung).filter(NguoiDung.email == email).first()
    if not user or user.trang_thai == "khoa":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tài khoản không tồn tại hoặc đang bị khóa"
        )

    new_access_token = create_access_token(data={"sub": user.email, "user_id": user.ma_nd})
    return TokenResponse(
        access_token=new_access_token,
        token_type="bearer",
        refresh_token=payload.refresh_token
    )

@router.post("/gui-otp", summary="Gửi mã OTP xác nhận đăng nhập về Gmail")
def gui_otp(payload: dict, db: Session = Depends(get_db)):
    """
    Gửi mã OTP xác nhận về địa chỉ Gmail của người dùng.
    """
    email = payload.get("email", "").strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Vui lòng nhập địa chỉ Gmail hợp lệ.")

    from app.services.email_service import EmailService
    from app.models.xac_nhan_otp import XacNhanOTP

    otp_code = EmailService.generate_otp()
    het_han = datetime.utcnow() + timedelta(minutes=10)

    # Lưu mã OTP vào CSDL
    otp_record = XacNhanOTP(
        email=email,
        otp_code=otp_code,
        het_han=het_han,
        da_dung=False
    )
    db.add(otp_record)
    db.commit()

    # Gửi email trong luồng nền
    import threading
    t = threading.Thread(
        target=EmailService.send_otp_email,
        args=(email, otp_code),
        daemon=True
    )
    t.start()

    msg = f"Mã xác nhận OTP đã được gửi đến hòm thư {email}. Vui lòng kiểm tra hộp thư đến hoặc thư rác (Spam)."
    return {
        "thong_bao": msg,
        "email": email,
        "dev_otp": otp_code  # Hỗ trợ hiển thị nếu SMTP chưa cấu hình
    }

@router.post("/xac-nhan-otp", summary="Xác nhận mã OTP Gmail để đăng nhập hoặc tạo tài khoản")
def xac_nhan_otp(payload: dict, db: Session = Depends(get_db)):
    """
    Xác thực mã OTP gửi về Gmail.
    Nếu hợp lệ: tự động đăng nhập hoặc tạo tài khoản mới nếu chưa tồn tại.
    """
    email = payload.get("email", "").strip().lower()
    otp_code = str(payload.get("otp") or payload.get("ma_otp") or "").strip()

    if not email or not otp_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Vui lòng nhập đầy đủ Email và mã OTP.")

    from app.models.xac_nhan_otp import XacNhanOTP
    from app.models.danh_muc import DanhMuc

    # Kiểm tra mã OTP hợp lệ
    record = db.query(XacNhanOTP).filter(
        XacNhanOTP.email == email,
        XacNhanOTP.otp_code == otp_code,
        XacNhanOTP.da_dung == False,
        XacNhanOTP.het_han > datetime.utcnow()
    ).order_by(XacNhanOTP.id.desc()).first()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã xác nhận OTP không chính xác hoặc đã hết hạn. Vui lòng thử lại."
        )

    # Đánh dấu đã dùng
    record.da_dung = True
    db.commit()

    # Tìm hoặc tạo người dùng
    user = db.query(NguoiDung).filter(NguoiDung.email == email).first()
    if not user:
        import secrets
        user = NguoiDung(
            email=email,
            ho_ten=email.split("@")[0],
            mat_khau_hash=get_password_hash(secrets.token_hex(16)),
            trang_thai="hoat_dong",
            so_lan_sai=0,
            ngay_tao=datetime.utcnow()
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Tạo sẵn các danh mục cơ bản
        default_cats = [
            ("Ăn uống", "chi", "utensils", "#f43f5e", 0.0),
            ("Đi lại", "chi", "car", "#0ea5e9", 0.0),
            ("Mua sắm", "chi", "shopping-bag", "#f59e0b", 0.0),
            ("Tiền lương", "thu", "wallet", "#10b981", 0.0)
        ]
        for cname, ctype, cicon, ccolor, climit in default_cats:
            cat = DanhMuc(ma_nd=user.ma_nd, ten_dm=cname, loai_dm=ctype, icon=cicon, mau_sac=ccolor, han_muc=climit)
            db.add(cat)
        db.commit()

    access_token = create_access_token(data={"sub": user.email, "user_id": user.ma_nd})
    refresh_token = create_refresh_token(data={"sub": user.email, "user_id": user.ma_nd})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "refresh_token": refresh_token,
        "user": {
            "ma_nd": user.ma_nd,
            "email": user.email,
            "ho_ten": user.ho_ten
        }
    }

