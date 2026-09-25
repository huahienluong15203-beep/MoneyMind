from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.nguoi_dung import NguoiDung
from app.models.muc_tieu_tiet_kiem import MucTieuTietKiem
from app.models.giao_dich import GiaoDich
from app.models.danh_muc import DanhMuc
from app.models.thong_bao import ThongBao
from app.schemas.muc_tieu import MucTieuCreate, MucTieuUpdate, MucTieuNopTien, MucTieuResponse

router = APIRouter(prefix="/api/muc-tieu", tags=["Quản lý mục tiêu tiết kiệm (UC008)"])

@router.get("", response_model=List[MucTieuResponse], summary="Lấy danh sách mục tiêu tiết kiệm (UC008)")
def lay_danh_sach_muc_tieu(
    db: Session = Depends(get_db),
    current_user: NguoiDung = Depends(get_current_user)
):
    goals = db.query(MucTieuTietKiem).filter(MucTieuTietKiem.ma_nd == current_user.ma_nd).all()
    # Sắp xếp: hũ chưa hoàn thành lên trước, hũ đã hoàn thành đưa xuống dưới
    goals.sort(key=lambda g: (1 if float(g.so_tien_hien_tai or 0.0) >= float(g.so_tien_muc_tieu or 1.0) else 0, g.ma_mt))
    results = []
    for g in goals:
        pct = round((g.so_tien_hien_tai / g.so_tien_muc_tieu) * 100, 1) if g.so_tien_muc_tieu > 0 else 0.0
        r = MucTieuResponse(
            ma_mt=g.ma_mt,
            ma_nd=g.ma_nd,
            ten_muc_tieu=g.ten_muc_tieu,
            so_tien_muc_tieu=g.so_tien_muc_tieu,
            so_tien_hien_tai=g.so_tien_hien_tai,
            han_chot=g.han_chot,
            trang_thai=g.trang_thai,
            phan_tram_hoan_thanh=pct,
            id=g.ma_mt,
            user_id=g.ma_nd,
            title=g.ten_muc_tieu,
            target_amount=g.so_tien_muc_tieu,
            current_amount=g.so_tien_hien_tai,
            deadline=g.han_chot
        )
        results.append(r)
    return results

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
    from datetime import datetime
    today_str = datetime.now().strftime("%Y-%m-%d")
    if clean_date < today_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hạn chót phải là ngày hôm nay hoặc thời gian trong tương lai, không được đặt ngày trong quá khứ"
        )
    return clean_date

@router.post("", response_model=MucTieuResponse, status_code=status.HTTP_201_CREATED, summary="Tạo mục tiêu tiết kiệm mới (UC008)")
def tao_muc_tieu(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: NguoiDung = Depends(get_current_user)
):
    title = payload.get("ten_muc_tieu") or payload.get("title")
    target = payload.get("so_tien_muc_tieu") or payload.get("target_amount")
    deadline = payload.get("han_chot") or payload.get("deadline")

    if not title:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Thiếu tên mục tiêu tiết kiệm")
    if not target or float(target) < 1000:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Số tiền mục tiêu phải lớn hơn 0 và tối thiểu là 1.000 đ")

    valid_deadline = validate_savings_deadline(deadline)

    new_g = MucTieuTietKiem(
        ma_nd=current_user.ma_nd,
        ten_muc_tieu=title,
        so_tien_muc_tieu=float(target),
        so_tien_hien_tai=0.0,
        han_chot=valid_deadline,
        trang_thai="dang_thuc_hien"
    )
    db.add(new_g)
    db.commit()
    db.refresh(new_g)

    return MucTieuResponse(
        ma_mt=new_g.ma_mt,
        ma_nd=new_g.ma_nd,
        ten_muc_tieu=new_g.ten_muc_tieu,
        so_tien_muc_tieu=new_g.so_tien_muc_tieu,
        so_tien_hien_tai=new_g.so_tien_hien_tai,
        han_chot=new_g.han_chot,
        trang_thai=new_g.trang_thai,
        phan_tram_hoan_thanh=0.0,
        id=new_g.ma_mt,
        user_id=new_g.ma_nd,
        title=new_g.ten_muc_tieu,
        target_amount=new_g.so_tien_muc_tieu,
        current_amount=new_g.so_tien_hien_tai,
        deadline=new_g.han_chot
    )

@router.put("/{ma_mt}", response_model=MucTieuResponse, summary="Cập nhật mục tiêu tiết kiệm (UC008)")
def sua_muc_tieu(
    ma_mt: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: NguoiDung = Depends(get_current_user)
):
    goal = db.query(MucTieuTietKiem).filter(MucTieuTietKiem.ma_mt == ma_mt).first()
    if not goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy mục tiêu tiết kiệm")

    # NFR-07
    if goal.ma_nd != current_user.ma_nd:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Không có quyền thao tác trên mục tiêu của người khác")

    new_title = payload.get("ten_muc_tieu") or payload.get("title")
    if new_title:
        goal.ten_muc_tieu = new_title

    new_target = payload.get("so_tien_muc_tieu") or payload.get("target_amount")
    if new_target is not None:
        target_val = float(new_target)
        if target_val < 1000:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Số tiền mục tiêu phải lớn hơn 0 và tối thiểu là 1.000 đ")
        curr_amt = float(goal.so_tien_hien_tai or 0.0)
        if target_val < curr_amt:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Số tiền mục tiêu không được nhỏ hơn số tiền đang có trong hũ ({curr_amt:,.0f} đ)!")
        goal.so_tien_muc_tieu = target_val

    new_current = payload.get("so_tien_hien_tai") or payload.get("current_amount")
    if new_current is not None:
        goal.so_tien_hien_tai = max(0.0, float(new_current))

    if "han_chot" in payload or "deadline" in payload:
        new_deadline = payload.get("han_chot") if "han_chot" in payload else payload.get("deadline")
        goal.han_chot = validate_savings_deadline(new_deadline)

    new_status = payload.get("trang_thai")
    if new_status:
        goal.trang_thai = new_status
    elif goal.so_tien_hien_tai >= goal.so_tien_muc_tieu:
        goal.trang_thai = "hoan_thanh"
    else:
        goal.trang_thai = "dang_thuc_hien"

    db.commit()
    db.refresh(goal)

    pct = round((goal.so_tien_hien_tai / goal.so_tien_muc_tieu) * 100, 1) if goal.so_tien_muc_tieu > 0 else 0.0
    return MucTieuResponse(
        ma_mt=goal.ma_mt,
        ma_nd=goal.ma_nd,
        ten_muc_tieu=goal.ten_muc_tieu,
        so_tien_muc_tieu=goal.so_tien_muc_tieu,
        so_tien_hien_tai=goal.so_tien_hien_tai,
        han_chot=goal.han_chot,
        trang_thai=goal.trang_thai,
        phan_tram_hoan_thanh=pct,
        id=goal.ma_mt,
        user_id=goal.ma_nd,
        title=goal.ten_muc_tieu,
        target_amount=goal.so_tien_muc_tieu,
        current_amount=goal.so_tien_hien_tai,
        deadline=goal.han_chot
    )

@router.delete("/{ma_mt}", summary="Xóa mục tiêu tiết kiệm (UC008)")
def xoa_muc_tieu(
    ma_mt: int,
    db: Session = Depends(get_db),
    current_user: NguoiDung = Depends(get_current_user)
):
    goal = db.query(MucTieuTietKiem).filter(MucTieuTietKiem.ma_mt == ma_mt).first()
    if not goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy mục tiêu tiết kiệm")

    # NFR-07
    if goal.ma_nd != current_user.ma_nd:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Không có quyền xóa mục tiêu của người khác")

    refund_amt = goal.so_tien_hien_tai
    goal_title = goal.ten_muc_tieu

    # Cập nhật chi tiết các giao dịch trước đó của mục tiêu này thành (đã xóa)
    goal_txs = db.query(GiaoDich).filter(
        GiaoDich.ma_nd == current_user.ma_nd,
        GiaoDich.ghi_chu.like(f"%{goal_title}%")
    ).all()
    for t in goal_txs:
        t.ghi_chu = f"Mục tiêu: {goal_title} (đã xoá)"

    if refund_amt > 0:
        tb = ThongBao(
            ma_nd=current_user.ma_nd,
            tieu_de="💰 Hoàn tiền hũ tiết kiệm về ví chính",
            noi_dung=f"Đã hoàn trả {refund_amt:,.0f} đ từ hũ '{goal_title}' về ví chính để bạn sử dụng cho các mục đích khác."
        )
        db.add(tb)

    db.delete(goal)
    db.commit()
    return {
        "thong_bao": f"Đã xóa mục tiêu tiết kiệm '{goal_title}'",
        "refunded": refund_amt,
        "refund_amount": refund_amt,
        "title": goal_title
    }

@router.post("/{ma_mt}/nop", summary="Nộp / trích tiền vào mục tiêu tiết kiệm (UC008)")
def nop_tien_muc_tieu(
    ma_mt: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: NguoiDung = Depends(get_current_user)
):
    amount = float(payload.get("so_tien") or payload.get("amount") or 0.0)
    if amount < 1000:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Số tiền nạp phải lớn hơn 0 và tối thiểu là 1.000 đ")

    goal = db.query(MucTieuTietKiem).filter(MucTieuTietKiem.ma_mt == ma_mt).first()
    if not goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy mục tiêu")

    if goal.ma_nd != current_user.ma_nd:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Không có quyền thao tác")

    # Kiểm tra số dư ví chính khả dụng
    from app.services.ngan_sach_service import NganSachService
    wallet_bal = NganSachService.tinh_so_du_vi_chinh(db, current_user.ma_nd)
    if amount > wallet_bal:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Số dư ví chính không đủ để trích vào mục tiêu tiết kiệm! (Số dư khả dụng hiện tại: {max(0.0, wallet_bal):,.0f} đ)"
        )

    if goal.so_tien_hien_tai >= goal.so_tien_muc_tieu:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mục tiêu này đã hoàn thành 100%!")

    con_lai = goal.so_tien_muc_tieu - goal.so_tien_hien_tai
    if amount > con_lai:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Số tiền trích vượt quá số còn thiếu ({con_lai:,.0f} đ)")

    # Ghi nhận giao dịch chi cho tiết kiệm
    dm_sav = db.query(DanhMuc).filter(DanhMuc.ma_nd == current_user.ma_nd, DanhMuc.ten_dm == "Tiết kiệm").first()
    if not dm_sav:
        dm_sav = DanhMuc(ma_nd=current_user.ma_nd, ten_dm="Tiết kiệm", loai_dm="chi", icon="piggy-bank", han_muc=0.0)
        db.add(dm_sav)
        db.commit()
        db.refresh(dm_sav)

    tx = GiaoDich(
        ma_nd=current_user.ma_nd,
        ma_dm=dm_sav.ma_dm,
        so_tien=amount,
        loai_gd="chi",
        ghi_chu=f"Mục tiêu: {goal.ten_muc_tieu}"
    )
    db.add(tx)

    goal.so_tien_hien_tai += amount
    pct = round((goal.so_tien_hien_tai / goal.so_tien_muc_tieu) * 100)
    if pct >= 100:
        goal.trang_thai = "hoan_thanh"
        tb = ThongBao(
            ma_nd=current_user.ma_nd,
            tieu_de=f"🎉 Hoàn thành mục tiêu '{goal.ten_muc_tieu}'!",
            noi_dung=f"Chúc mừng bạn đã hoàn thành 100% mục tiêu tiết kiệm '{goal.ten_muc_tieu}' với số tiền {goal.so_tien_hien_tai:,.0f} đ!"
        )
        db.add(tb)
    elif pct >= 90:
        tb = ThongBao(
            ma_nd=current_user.ma_nd,
            tieu_de=f"🌟 Sắp hoàn thành mục tiêu '{goal.ten_muc_tieu}'!",
            noi_dung=f"Mục tiêu '{goal.ten_muc_tieu}' đã đạt {pct}% tiến độ ({goal.so_tien_hien_tai:,.0f} đ / {goal.so_tien_muc_tieu:,.0f} đ)!"
        )
        db.add(tb)

    db.commit()
    db.refresh(goal)

    return {
        "thong_bao": f"Nộp thành công {amount:,.0f} đ vào mục tiêu '{goal.ten_muc_tieu}'",
        "so_tien_hien_tai": goal.so_tien_hien_tai,
        "phan_tram_hoan_thanh": pct,
        "trang_thai": goal.trang_thai
    }
