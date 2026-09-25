from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, get_password_hash, verify_password
from app.models.nguoi_dung import NguoiDung
from app.schemas.nguoi_dung import NguoiDungUpdate, NguoiDungResponse

router = APIRouter(prefix="/api/nguoi-dung", tags=["Quản lý thông tin tài khoản (UC002)"])

@router.get("/toi", response_model=NguoiDungResponse, summary="Xem thông tin tài khoản hiện tại (UC002)")
def lay_thong_tin_toi(current_user: NguoiDung = Depends(get_current_user)):
    return current_user

@router.put("/toi", response_model=NguoiDungResponse, summary="Cập nhật thông tin tài khoản (UC002)")
def cap_nhat_thong_tin_toi(
    payload: NguoiDungUpdate,
    db: Session = Depends(get_db),
    current_user: NguoiDung = Depends(get_current_user)
):
    if payload.ho_ten is not None:
        current_user.ho_ten = payload.ho_ten
    if payload.dob is not None:
        current_user.dob = payload.dob
    if payload.occupation is not None:
        current_user.occupation = payload.occupation
    if payload.goals is not None:
        current_user.goals = payload.goals

    # Đổi mật khẩu nếu có yêu cầu
    if payload.mat_khau_moi:
        if not payload.mat_khau_cu:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vui lòng cung cấp mật khẩu cũ để thực hiện đổi mật khẩu."
            )
        if not verify_password(payload.mat_khau_cu, current_user.mat_khau_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mật khẩu cũ không chính xác."
            )
        if len(payload.mat_khau_moi) < 4:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mật khẩu mới phải có độ dài tối thiểu 4 ký tự."
            )
        current_user.mat_khau_hash = get_password_hash(payload.mat_khau_moi)

    db.commit()
    db.refresh(current_user)
    return current_user
