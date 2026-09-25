from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.nguoi_dung import NguoiDung
from app.models.ngan_sach import NganSach
from app.models.danh_muc import DanhMuc
from app.models.giao_dich import GiaoDich
from app.services.ngan_sach_service import NganSachService
from app.schemas.ngan_sach import (
    NganSachCreate, NganSachUpdate, NganSachResponse, CanhBaoNgayResponse
)

router = APIRouter(prefix="/api/ngan-sach", tags=["Quản lý ngân sách & Cảnh báo (UC006, UC007)"])

@router.get("", response_model=List[NganSachResponse], summary="Xem danh sách hạn mức ngân sách (UC006)")
def lay_danh_sach_ngan_sach(
    thang_nam: Optional[str] = Query(None, description="Định dạng YYYY-MM (mặc định tháng hiện tại)"),
    db: Session = Depends(get_db),
    current_user: NguoiDung = Depends(get_current_user)
):
    if not thang_nam:
        thang_nam = datetime.now().strftime("%Y-%m")

    ngan_sachs = db.query(NganSach).filter(
        NganSach.ma_nd == current_user.ma_nd,
        NganSach.thang_nam == thang_nam
    ).all()

    results = []
    for ns in ngan_sachs:
        dm = db.query(DanhMuc).filter(DanhMuc.ma_dm == ns.ma_dm).first()
        ten_dm = dm.ten_dm if dm else "Không rõ"
        ty_le = round(ns.so_tien_da_chi / ns.han_muc, 2) if ns.han_muc > 0 else 0.0

        results.append(NganSachResponse(
            ma_ns=ns.ma_ns,
            ma_nd=ns.ma_nd,
            ma_dm=ns.ma_dm,
            thang_nam=ns.thang_nam,
            han_muc=ns.han_muc,
            so_tien_da_chi=ns.so_tien_da_chi,
            canh_bao_da_gui=ns.canh_bao_da_gui,
            ten_dm=ten_dm,
            ty_le=ty_le
        ))
    return results

@router.post("", response_model=NganSachResponse, status_code=status.HTTP_201_CREATED, summary="Thiết lập ngân sách theo tháng (UC006 & TC-06)")
def thiet_lap_ngan_sach(
    payload: NganSachCreate,
    db: Session = Depends(get_db),
    current_user: NguoiDung = Depends(get_current_user)
):
    """
    UC006 & TC-06:
    - Kiểm tra han_muc > 0, nếu han_muc <= 0 trả về lỗi 400 (TC-06)
    - Nếu đã có ngân sách cho danh mục trong tháng, cập nhật lại giá trị mới
    """
    if payload.han_muc < 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hạn mức ngân sách phải lớn hơn 0 và tối thiểu là 1.000 đ"
        )

    # Kiểm tra danh mục thuộc quyền sở hữu
    dm = db.query(DanhMuc).filter(
        DanhMuc.ma_dm == payload.ma_dm,
        DanhMuc.ma_nd == current_user.ma_nd
    ).first()
    if not dm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Danh mục không tồn tại hoặc không thuộc quyền sở hữu"
        )

    # Tính số tiền đã chi thực tế trong tháng đó
    start_date = datetime.strptime(f"{payload.thang_nam}-01", "%Y-%m-%d")
    if start_date.month == 12:
        end_date = datetime(start_date.year + 1, 1, 1)
    else:
        end_date = datetime(start_date.year, start_date.month + 1, 1)

    da_chi = db.query(func.coalesce(func.sum(GiaoDich.so_tien), 0.0)).filter(
        GiaoDich.ma_nd == current_user.ma_nd,
        GiaoDich.ma_dm == payload.ma_dm,
        GiaoDich.loai_gd == "chi",
        GiaoDich.ngay_gd >= start_date,
        GiaoDich.ngay_gd < end_date
    ).scalar() or 0.0

    # Kiểm tra nếu đã có bản ghi
    ns = db.query(NganSach).filter(
        NganSach.ma_nd == current_user.ma_nd,
        NganSach.ma_dm == payload.ma_dm,
        NganSach.thang_nam == payload.thang_nam
    ).first()

    if ns:
        ns.han_muc = payload.han_muc
        ns.so_tien_da_chi = da_chi
        ns.canh_bao_da_gui = (da_chi > payload.han_muc)
    else:
        ns = NganSach(
            ma_nd=current_user.ma_nd,
            ma_dm=payload.ma_dm,
            thang_nam=payload.thang_nam,
            han_muc=payload.han_muc,
            so_tien_da_chi=da_chi,
            canh_bao_da_gui=(da_chi > payload.han_muc)
        )
        db.add(ns)

    # Đồng bộ hạn mức sang danh mục nếu là tháng hiện tại
    now_ym = datetime.now().strftime("%Y-%m")
    if payload.thang_nam == now_ym:
        dm.han_muc = payload.han_muc

    db.commit()
    db.refresh(ns)

    ty_le = round(ns.so_tien_da_chi / ns.han_muc, 2) if ns.han_muc > 0 else 0.0
    return NganSachResponse(
        ma_ns=ns.ma_ns,
        ma_nd=ns.ma_nd,
        ma_dm=ns.ma_dm,
        thang_nam=ns.thang_nam,
        han_muc=ns.han_muc,
        so_tien_da_chi=ns.so_tien_da_chi,
        canh_bao_da_gui=ns.canh_bao_da_gui,
        ten_dm=dm.ten_dm,
        ty_le=ty_le
    )

@router.put("/{ma_ns}", response_model=NganSachResponse, summary="Chỉnh sửa hạn mức ngân sách (UC006)")
def sua_ngan_sach(
    ma_ns: int,
    payload: NganSachUpdate,
    db: Session = Depends(get_db),
    current_user: NguoiDung = Depends(get_current_user)
):
    if payload.han_muc < 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hạn mức ngân sách phải lớn hơn 0 và tối thiểu là 1.000 đ"
        )

    ns = db.query(NganSach).filter(NganSach.ma_ns == ma_ns).first()
    if not ns:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy bản ghi ngân sách")

    # NFR-07
    if ns.ma_nd != current_user.ma_nd:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Không có quyền thao tác trên ngân sách của người khác")

    ns.han_muc = payload.han_muc
    ns.canh_bao_da_gui = (ns.so_tien_da_chi > payload.han_muc)
    db.commit()
    db.refresh(ns)

    dm = db.query(DanhMuc).filter(DanhMuc.ma_dm == ns.ma_dm).first()
    ten_dm = dm.ten_dm if dm else "Không rõ"
    ty_le = round(ns.so_tien_da_chi / ns.han_muc, 2) if ns.han_muc > 0 else 0.0

    return NganSachResponse(
        ma_ns=ns.ma_ns,
        ma_nd=ns.ma_nd,
        ma_dm=ns.ma_dm,
        thang_nam=ns.thang_nam,
        han_muc=ns.han_muc,
        so_tien_da_chi=ns.so_tien_da_chi,
        canh_bao_da_gui=ns.canh_bao_da_gui,
        ten_dm=ten_dm,
        ty_le=ty_le
    )

@router.get("/canh-bao", response_model=List[CanhBaoNgayResponse], summary="Trạng thái cảnh báo vượt ngân sách hiện tại (UC007)")
def lay_danh_sach_canh_bao(
    thang_nam: Optional[str] = Query(None, description="Định dạng YYYY-MM (mặc định tháng hiện tại)"),
    db: Session = Depends(get_db),
    current_user: NguoiDung = Depends(get_current_user)
):
    """UC007: Trạng thái cảnh báo vượt ngân sách hiện tại"""
    return NganSachService.lay_danh_sach_canh_bao(db, current_user.ma_nd, thang_nam)
