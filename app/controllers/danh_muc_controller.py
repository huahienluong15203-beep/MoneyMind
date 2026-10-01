from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.nguoi_dung import NguoiDung
from app.models.danh_muc import DanhMuc
from app.models.giao_dich import GiaoDich
from app.models.ngan_sach import NganSach
from app.models.thong_bao import ThongBao
from app.schemas.danh_muc import DanhMucCreate, DanhMucUpdate, DanhMucResponse

router = APIRouter(prefix="/api/danh-muc", tags=["Quản lý danh mục thu / chi (UC003)"])

@router.get("", response_model=List[DanhMucResponse], summary="Lấy danh sách danh mục (UC003)")
def lay_danh_sach_danh_muc(
    db: Session = Depends(get_db),
    current_user: NguoiDung = Depends(get_current_user)
):
    from app.services.ngan_sach_service import NganSachService
    NganSachService.tu_dong_ket_chuyen_thang_moi(db, current_user.ma_nd)
    cats = db.query(DanhMuc).filter(DanhMuc.ma_nd == current_user.ma_nd).all()
    now_ym = datetime.now().strftime("%Y-%m")
    results = []
    for c in cats:
        ns = db.query(NganSach).filter(
            NganSach.ma_dm == c.ma_dm,
            NganSach.thang_nam == now_ym
        ).first()
        current_limit = float(ns.han_muc) if (ns and ns.han_muc and ns.han_muc > 0) else 0.0
        so_du = float(ns.so_du_chuyen_sang or 0.0) if ns else 0.0
        cap_moi = float(ns.han_muc_cap_moi or 0.0) if ns else 0.0
        da_cap = (ns is not None and ns.han_muc is not None and ns.han_muc > 0)
        results.append(DanhMucResponse(
            ma_dm=c.ma_dm,
            ma_nd=c.ma_nd,
            ten_dm=c.ten_dm,
            loai_dm=c.loai_dm,
            icon=c.icon,
            mau_sac=c.mau_sac,
            han_muc=current_limit,
            budget_limit=current_limit,
            id=c.ma_dm,
            user_id=c.ma_nd,
            name=c.ten_dm,
            type=c.loai_dm,
            so_du_chuyen_sang=so_du,
            han_muc_cap_moi=cap_moi,
            da_cap_han_muc=da_cap,
            han_muc_goc=float(c.han_muc or 0.0)
        ))
    return results

@router.post("", response_model=DanhMucResponse, status_code=status.HTTP_201_CREATED, summary="Tạo danh mục mới (UC003)")
def tao_danh_muc(
    payload: DanhMucCreate,
    db: Session = Depends(get_db),
    current_user: NguoiDung = Depends(get_current_user)
):
    from datetime import datetime
    limit = (payload.han_muc or 0.0) if payload.loai_dm == 'chi' else 0.0
    new_cat = DanhMuc(
        ma_nd=current_user.ma_nd,
        ten_dm=payload.ten_dm,
        loai_dm=payload.loai_dm,
        icon=payload.icon or "tag",
        mau_sac=payload.mau_sac or "#0ea5e9",
        han_muc=limit
    )
    db.add(new_cat)
    db.commit()
    db.refresh(new_cat)

    if payload.loai_dm == 'chi' and payload.han_muc and payload.han_muc > 0:
        now_ym = datetime.now().strftime("%Y-%m")
        ns = NganSach(
            ma_nd=current_user.ma_nd,
            ma_dm=new_cat.ma_dm,
            thang_nam=now_ym,
            han_muc=payload.han_muc,
            so_tien_da_chi=0.0
        )
        db.add(ns)
        db.commit()

    if payload.loai_dm == 'thu' and payload.han_muc and payload.han_muc > 0:
        tx = GiaoDich(
            ma_nd=current_user.ma_nd,
            ma_dm=new_cat.ma_dm,
            so_tien=payload.han_muc,
            loai_gd="thu",
            ghi_chu=f"Khoản thu danh mục: {new_cat.ten_dm}",
            ngay_gd=datetime.now()
        )
        db.add(tx)
        db.commit()

    return new_cat

@router.put("/{ma_dm}", response_model=DanhMucResponse, summary="Chỉnh sửa danh mục (UC003)")
def sua_danh_muc(
    ma_dm: int,
    payload: DanhMucUpdate,
    db: Session = Depends(get_db),
    current_user: NguoiDung = Depends(get_current_user)
):
    cat = db.query(DanhMuc).filter(DanhMuc.ma_dm == ma_dm).first()
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy danh mục")

    # BR-06 & NFR-07: Kiểm tra quyền sở hữu
    if cat.ma_nd != current_user.ma_nd:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Không có quyền thao tác trên danh mục của người khác")

    if payload.ten_dm is not None:
        cat.ten_dm = payload.ten_dm
    if payload.loai_dm is not None:
        cat.loai_dm = payload.loai_dm
    if payload.icon is not None:
        cat.icon = payload.icon
    if payload.mau_sac is not None:
        cat.mau_sac = payload.mau_sac
    if payload.han_muc is not None:
        if cat.loai_dm == 'chi':
            now_dt = datetime.now()
            start_this = datetime(now_dt.year, now_dt.month, 1)
            end_this = datetime(now_dt.year + 1, 1, 1) if now_dt.month == 12 else datetime(now_dt.year, now_dt.month + 1, 1)
            now_ym = now_dt.strftime("%Y-%m")
            txs = db.query(GiaoDich).filter(
                GiaoDich.ma_dm == ma_dm,
                GiaoDich.loai_gd == "chi",
                GiaoDich.ngay_gd >= start_this,
                GiaoDich.ngay_gd < end_this
            ).all()
            spent = sum(float(t.so_tien or 0.0) for t in txs)
            if payload.han_muc < spent:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Hạn mức mới ({payload.han_muc:,.0f} đ) không được nhỏ hơn số tiền đã chi ({spent:,.0f} đ) trong danh mục này! Bạn chỉ có thể nâng hạn mức chứ không được giảm nhỏ hơn số tiền đã chi."
                )
            
            from app.services.ngan_sach_service import NganSachService
            ns = db.query(NganSach).filter(
                NganSach.ma_nd == current_user.ma_nd,
                NganSach.ma_dm == ma_dm,
                NganSach.thang_nam == now_ym
            ).first()
            old_limit = float(ns.han_muc) if (ns and ns.han_muc) else float(cat.han_muc or 0.0)
            so_du = float(ns.so_du_chuyen_sang or 0.0) if ns else 0.0
            old_allocated = max(0.0, old_limit - so_du)
            new_allocated = max(0.0, payload.han_muc - so_du)
            diff = new_allocated - old_allocated
            if diff > 0:
                current_balance = NganSachService.tinh_so_du_vi_chinh(db, current_user.ma_nd)
                if diff > current_balance:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Số dư ví chính không đủ để cấp hạn mức thêm {diff:,.0f} đ cho hũ '{cat.ten_dm}'! Số dư còn lại: {max(0.0, current_balance):,.0f} đ."
                    )

            if ns:
                ns.han_muc = payload.han_muc
                ns.han_muc_cap_moi = new_allocated
                ns.so_tien_da_chi = spent
            elif payload.han_muc > 0:
                ns = NganSach(
                    ma_nd=current_user.ma_nd,
                    ma_dm=ma_dm,
                    thang_nam=now_ym,
                    han_muc=payload.han_muc,
                    han_muc_cap_moi=new_allocated,
                    so_du_chuyen_sang=0.0,
                    so_tien_da_chi=spent
                )
                db.add(ns)

            if diff > 0:
                tb = ThongBao(
                    ma_nd=current_user.ma_nd,
                    tieu_de="📤 Tăng Hạn Mức Hũ Chi Tiêu",
                    noi_dung=f"Đã tăng hạn mức hũ '{cat.ten_dm}' thêm {diff:,.0f} đ (hạn mức mới: {payload.han_muc:,.0f} đ). Số tiền {diff:,.0f} đ đã được trích từ ví chính vào hũ."
                )
                db.add(tb)
            elif diff < 0:
                refund_amt = abs(diff)
                tb = ThongBao(
                    ma_nd=current_user.ma_nd,
                    tieu_de="💰 Hoàn Trả Hạn Mức Về Ví Chính",
                    noi_dung=f"Đã giảm hạn mức hũ '{cat.ten_dm}' bớt {refund_amt:,.0f} đ (hạn mức mới: {payload.han_muc:,.0f} đ). Số tiền {refund_amt:,.0f} đ đã được hoàn trả về ví chính để bạn sử dụng cho các mục tiêu tiếp theo."
                )
                db.add(tb)
        else:
            cat.han_muc = 0.0
            now_ym = datetime.now().strftime("%Y-%m")
            db.query(NganSach).filter(NganSach.ma_nd == current_user.ma_nd, NganSach.ma_dm == ma_dm, NganSach.thang_nam == now_ym).delete()
        cat.han_muc = payload.han_muc

    db.commit()
    db.refresh(cat)
    return cat

@router.delete("/{ma_dm}", summary="Xóa danh mục (UC003)")
def xoa_danh_muc(
    ma_dm: int,
    db: Session = Depends(get_db),
    current_user: NguoiDung = Depends(get_current_user)
):
    cat = db.query(DanhMuc).filter(DanhMuc.ma_dm == ma_dm).first()
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy danh mục")

    # BR-06 & NFR-07: Kiểm tra quyền sở hữu
    if cat.ma_nd != current_user.ma_nd:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Không có quyền thao tác trên danh mục của người khác")

    cat_name = cat.ten_dm
    cat_type = cat.loai_dm
    cat_limit = float(cat.han_muc or 0.0)

    spent = 0.0
    if cat_type == "chi":
        now_dt = datetime.now()
        start_this = datetime(now_dt.year, now_dt.month, 1)
        end_this = datetime(now_dt.year + 1, 1, 1) if now_dt.month == 12 else datetime(now_dt.year, now_dt.month + 1, 1)
        txs = db.query(GiaoDich).filter(
            GiaoDich.ma_dm == ma_dm,
            GiaoDich.loai_gd == "chi",
            GiaoDich.ngay_gd >= start_this,
            GiaoDich.ngay_gd < end_this
        ).all()
        spent = sum(t.so_tien for t in txs)
    remaining = max(0.0, cat_limit - spent)

    # Xóa các giao dịch và ngân sách liên quan đến danh mục này
    db.query(GiaoDich).filter(GiaoDich.ma_dm == ma_dm).delete()
    db.query(NganSach).filter(NganSach.ma_dm == ma_dm).delete()
    db.delete(cat)
    db.commit()

    if cat_type == "chi" and remaining > 0:
        tb = ThongBao(
            ma_nd=current_user.ma_nd,
            tieu_de="💰 Hoàn Trả Hạn Mức Về Ví Chính",
            noi_dung=f"Đã xóa danh mục '{cat_name}'. Số tiền hạn mức khả dụng còn lại {remaining:,.0f} đ đã được hoàn trả về ví chính để bạn sử dụng cho các mục tiêu chi tiêu tiếp theo."
        )
        db.add(tb)
        db.commit()

    return {
        "thong_bao": f"Đã xóa danh mục '{cat_name}' thành công",
        "ten_dm": cat_name,
        "so_tien_hoan": remaining
    }
