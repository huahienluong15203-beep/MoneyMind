from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.nguoi_dung import NguoiDung
from app.models.giao_dich import GiaoDich
from app.models.danh_muc import DanhMuc
from app.services.ngan_sach_service import NganSachService
from app.schemas.giao_dich import (
    GiaoDichCreate, GiaoDichUpdate, GiaoDichResponse,
    CanhBaoNganSachInfo, GiaoDichCreateResponse
)

router = APIRouter(prefix="/api/giao-dich", tags=["Quản lý & Tra cứu giao dịch (UC004, UC005, UC007)"])

@router.get("", response_model=List[GiaoDichResponse], summary="Lấy danh sách giao dịch (UC004)")
def lay_danh_sach_giao_dich(
    db: Session = Depends(get_db),
    current_user: NguoiDung = Depends(get_current_user)
):
    txs = db.query(GiaoDich).filter(
        GiaoDich.ma_nd == current_user.ma_nd
    ).order_by(desc(GiaoDich.ngay_gd), desc(GiaoDich.ma_gd)).all()

    # Populate compatibility fields
    results = []
    for t in txs:
        r = GiaoDichResponse.model_validate(t)
        r.id = t.ma_gd
        r.user_id = t.ma_nd
        r.category_id = t.ma_dm
        r.amount = t.so_tien
        r.type = t.loai_gd
        r.date = t.ngay_gd
        r.note = t.ghi_chu
        results.append(r)
    return results

@router.post("", status_code=status.HTTP_201_CREATED, summary="Thêm giao dịch mới (UC004 <<include>> UC007)")
def tao_giao_dich(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: NguoiDung = Depends(get_current_user)
):
    """
    UC004 <<include>> UC007:
    - Kiểm tra tính hợp lệ: so_tien > 0 (TC-03)
    - BR-01: loai_gd phải khớp với loai_dm của danh mục
    - NFR-02 & TC-04: Cảnh báo vượt ngân sách được kiểm tra và trả về ngay trong cùng một request
    """
    amount = payload.get("so_tien") or payload.get("amount")
    if amount is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Thiếu số tiền giao dịch")

    try:
        so_tien = float(amount)
    except (ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Số tiền giao dịch không hợp lệ")

    # TC-03: Số tiền < 1000 trả về lỗi 400
    if so_tien < 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Số tiền giao dịch phải lớn hơn 0 và tối thiểu là 1.000 đ"
        )

    loai_gd = payload.get("loai_gd") or payload.get("type") or "chi"
    ma_dm = payload.get("ma_dm") or payload.get("category_id")
    if not ma_dm:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Thiếu danh mục giao dịch")

    ma_dm = int(ma_dm)
    danh_muc = db.query(DanhMuc).filter(
        DanhMuc.ma_dm == ma_dm,
        DanhMuc.ma_nd == current_user.ma_nd
    ).first()

    if not danh_muc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Danh mục không tồn tại hoặc không thuộc về người dùng"
        )

    # BR-01: Loại giao dịch phải khớp với loại danh mục
    if danh_muc.loai_dm != loai_gd:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Loại giao dịch '{loai_gd}' không khớp với loại danh mục '{danh_muc.loai_dm}'"
        )

    ghi_chu = payload.get("ghi_chu") or payload.get("note") or ""

    ngay_gd_input = payload.get("ngay_gd") or payload.get("date")
    parsed_date = datetime.now()
    if ngay_gd_input:
        if isinstance(ngay_gd_input, datetime):
            parsed_date = ngay_gd_input
        elif isinstance(ngay_gd_input, str):
            try:
                parsed_date = datetime.fromisoformat(ngay_gd_input.replace("Z", "+00:00"))
            except Exception:
                pass
    if parsed_date and parsed_date.tzinfo is not None:
        parsed_date = parsed_date.replace(tzinfo=None)

    # Lưu giao dịch vào CSDL
    new_tx = GiaoDich(
        ma_nd=current_user.ma_nd,
        ma_dm=ma_dm,
        so_tien=so_tien,
        loai_gd=loai_gd,
        ngay_gd=parsed_date,
        ghi_chu=ghi_chu,
        ngay_tao=datetime.utcnow()
    )
    db.add(new_tx)
    db.commit()
    db.refresh(new_tx)

    # NFR-02 & UC007 & TC-04: Cảnh báo vượt ngân sách real-time ngay trong cùng một response
    canh_bao_info = CanhBaoNganSachInfo()
    if loai_gd == "chi":
        canh_bao_info = NganSachService.kiem_tra_ngan_sach(
            db=db,
            ma_nd=current_user.ma_nd,
            ma_dm=ma_dm,
            ngay_gd=parsed_date
        )

    tx_resp = GiaoDichResponse.model_validate(new_tx)
    tx_resp.id = new_tx.ma_gd
    tx_resp.user_id = new_tx.ma_nd
    tx_resp.category_id = new_tx.ma_dm
    tx_resp.amount = new_tx.so_tien
    tx_resp.type = new_tx.loai_gd
    tx_resp.date = new_tx.ngay_gd
    tx_resp.note = new_tx.ghi_chu

    return {
        "giao_dich": tx_resp,
        "canh_bao": canh_bao_info,
        # Trả về cả các thuộc tính top-level để frontend cũ vẫn hoạt động trơn tru
        "id": new_tx.ma_gd,
        "ma_gd": new_tx.ma_gd,
        "so_tien": new_tx.so_tien,
        "amount": new_tx.so_tien,
        "loai_gd": new_tx.loai_gd,
        "type": new_tx.loai_gd,
        "ma_dm": new_tx.ma_dm,
        "category_id": new_tx.ma_dm,
        "ghi_chu": new_tx.ghi_chu,
        "note": new_tx.ghi_chu,
        "ngay_gd": new_tx.ngay_gd,
        "date": new_tx.ngay_gd
    }

@router.get("/tim-kiem", summary="Tra cứu & lọc giao dịch có phân trang (UC005)")
def tim_kiem_giao_dich(
    tu_ngay: Optional[str] = Query(None, description="Từ ngày định dạng YYYY-MM-DD"),
    den_ngay: Optional[str] = Query(None, description="Đến ngày định dạng YYYY-MM-DD"),
    ma_dm: Optional[int] = Query(None, description="Mã danh mục"),
    loai_gd: Optional[str] = Query(None, description="'thu' hoặc 'chi'"),
    so_tien_min: Optional[float] = Query(None, description="Số tiền tối thiểu"),
    so_tien_max: Optional[float] = Query(None, description="Số tiền tối đa"),
    tu_khoa: Optional[str] = Query(None, description="Từ khóa trong ghi chú"),
    page: int = Query(1, ge=1, description="Trang hiện tại (bắt đầu từ 1)"),
    limit: int = Query(20, ge=1, le=100, description="Số bản ghi mỗi trang (mặc định 20)"),
    db: Session = Depends(get_db),
    current_user: NguoiDung = Depends(get_current_user)
):
    """
    UC005: Tra cứu giao dịch theo khoảng ngày, danh mục, loại thu/chi, số tiền.
    Phân trang mặc định 20 bản ghi/trang để tối ưu hiệu năng.
    """
    query = db.query(GiaoDich).filter(GiaoDich.ma_nd == current_user.ma_nd)

    if tu_ngay:
        try:
            d_start = datetime.strptime(tu_ngay, "%Y-%m-%d")
            query = query.filter(GiaoDich.ngay_gd >= d_start)
        except ValueError:
            pass

    if den_ngay:
        try:
            d_end = datetime.strptime(f"{den_ngay} 23:59:59", "%Y-%m-%d %H:%M:%S")
            query = query.filter(GiaoDich.ngay_gd <= d_end)
        except ValueError:
            pass

    if ma_dm:
        query = query.filter(GiaoDich.ma_dm == ma_dm)

    if loai_gd:
        query = query.filter(GiaoDich.loai_gd == loai_gd)

    if so_tien_min is not None:
        query = query.filter(GiaoDich.so_tien >= so_tien_min)

    if so_tien_max is not None:
        query = query.filter(GiaoDich.so_tien <= so_tien_max)

    if tu_khoa:
        query = query.filter(GiaoDich.ghi_chu.ilike(f"%{tu_khoa}%"))

    total = query.count()
    offset = (page - 1) * limit
    items = query.order_by(desc(GiaoDich.ngay_gd)).offset(offset).limit(limit).all()

    formatted_items = []
    for t in items:
        dm = db.query(DanhMuc).filter(DanhMuc.ma_dm == t.ma_dm).first()
        formatted_items.append({
            "ma_gd": t.ma_gd,
            "id": t.ma_gd,
            "ma_dm": t.ma_dm,
            "ten_dm": dm.ten_dm if dm else "Khác",
            "so_tien": t.so_tien,
            "amount": t.so_tien,
            "loai_gd": t.loai_gd,
            "type": t.loai_gd,
            "ngay_gd": t.ngay_gd.isoformat() if t.ngay_gd else None,
            "date": t.ngay_gd.isoformat() if t.ngay_gd else None,
            "ghi_chu": t.ghi_chu,
            "note": t.ghi_chu
        })

    return {
        "items": formatted_items,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit if limit > 0 else 1
    }

@router.put("/{ma_gd}", summary="Sửa giao dịch (UC004 & TC-05)")
def sua_giao_dich(
    ma_gd: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: NguoiDung = Depends(get_current_user)
):
    """
    UC004 & TC-05 & TC-10:
    - Kiểm tra quyền sở hữu NFR-07 / BR-06 (TC-10: không phải của mình trả 403)
    - Nếu thay đổi số tiền chi tiêu -> tính lại và trả kèm cảnh báo ngân sách (TC-05)
    """
    tx = db.query(GiaoDich).filter(GiaoDich.ma_gd == ma_gd).first()
    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy giao dịch")

    # NFR-07 & TC-10: Kiểm tra cách ly dữ liệu theo người dùng
    if tx.ma_nd != current_user.ma_nd:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Không có quyền truy cập giao dịch của người khác")

    amount = payload.get("so_tien") or payload.get("amount")
    if amount is not None:
        try:
            so_tien = float(amount)
            if so_tien < 1000:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Số tiền giao dịch phải lớn hơn 0 và tối thiểu là 1.000 đ")
            tx.so_tien = so_tien
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Số tiền không hợp lệ")

    if "loai_gd" in payload or "type" in payload:
        tx.loai_gd = payload.get("loai_gd") or payload.get("type")

    if "ma_dm" in payload or "category_id" in payload:
        tx.ma_dm = int(payload.get("ma_dm") or payload.get("category_id"))

    if "ghi_chu" in payload or "note" in payload:
        tx.ghi_chu = payload.get("ghi_chu") or payload.get("note")

    db.commit()
    db.refresh(tx)

    # TC-05: Chạy lại kiểm tra ngân sách
    canh_bao_info = CanhBaoNganSachInfo()
    if tx.loai_gd == "chi":
        canh_bao_info = NganSachService.kiem_tra_ngan_sach(
            db=db,
            ma_nd=current_user.ma_nd,
            ma_dm=tx.ma_dm,
            ngay_gd=tx.ngay_gd
        )

    return {
        "thong_bao": "Cập nhật giao dịch thành công",
        "giao_dich": GiaoDichResponse.model_validate(tx),
        "canh_bao": canh_bao_info
    }

@router.delete("/{ma_gd}", summary="Xóa giao dịch (UC004 & TC-10)")
def xoa_giao_dich(
    ma_gd: int,
    db: Session = Depends(get_db),
    current_user: NguoiDung = Depends(get_current_user)
):
    """
    UC004 & TC-10:
    - Kiểm tra quyền sở hữu NFR-07 / BR-06 (TC-10: không phải của mình trả 403)
    """
    tx = db.query(GiaoDich).filter(GiaoDich.ma_gd == ma_gd).first()
    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy giao dịch")

    # NFR-07 & TC-10
    if tx.ma_nd != current_user.ma_nd:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Không có quyền xóa giao dịch của người khác")

    ma_dm = tx.ma_dm
    ngay_gd = tx.ngay_gd
    loai_gd = tx.loai_gd

    db.delete(tx)
    db.commit()

    # Tính lại ngân sách sau khi xóa
    if loai_gd == "chi":
        NganSachService.kiem_tra_ngan_sach(
            db=db,
            ma_nd=current_user.ma_nd,
            ma_dm=ma_dm,
            ngay_gd=ngay_gd
        )

    return {"thong_bao": "Đã xóa giao dịch thành công"}
