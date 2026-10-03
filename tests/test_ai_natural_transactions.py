"""
Kiểm thử tính năng Ghi nhận giao dịch và Nộp quỹ tiết kiệm qua lệnh giao tiếp tự nhiên của AI (Natural Language Actions)
"""
from fastapi import status
from app.models.giao_dich import GiaoDich
from app.models.muc_tieu_tiet_kiem import MucTieuTietKiem
from app.models.danh_muc import DanhMuc

def test_ai_them_giao_dich_chi_tieu_tu_nhien(client, db_session, user_a, auth_headers_a, cat_chi_a):
    """
    Test người dùng chat: 'tôi đi ăn bánh mì hết 20000'
    Hệ thống tự động:
    1. Parse số tiền 20.000đ, loại chi tiêu, danh mục Ăn uống
    2. Thêm bản ghi GiaoDich vào CSDL
    3. Trả về câu phản hồi xác nhận đầy đủ số liệu và cảnh báo ngân sách
    """
    payload = {"cau_hoi": "tôi đi ăn bánh mì hết 20000"}
    res = client.post("/api/ai/hoi-dap", json=payload, headers=auth_headers_a)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    tra_loi = data["tra_loi"]

    assert "ghi nhận giao dịch thành công" in tra_loi.lower()
    assert "20,000" in tra_loi or "20.000" in tra_loi

    # Kiểm tra CSDL đã có giao dịch
    tx = db_session.query(GiaoDich).filter(
        GiaoDich.ma_nd == user_a.ma_nd,
        GiaoDich.so_tien == 20000.0,
        GiaoDich.loai_gd == "chi"
    ).first()
    assert tx is not None
    assert "Bánh mì" in tx.ghi_chu or "bánh mì" in tx.ghi_chu

def test_ai_them_giao_dich_xang_xe_tu_nhien(client, db_session, user_a, auth_headers_a):
    """Test: 'đổ xăng 50k' -> tự động ghi nhận danh mục Đi lại"""
    payload = {"cau_hoi": "đổ xăng 50k"}
    res = client.post("/api/ai/hoi-dap", json=payload, headers=auth_headers_a)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert "50,000" in data["tra_loi"]

    tx = db_session.query(GiaoDich).filter(
        GiaoDich.ma_nd == user_a.ma_nd,
        GiaoDich.so_tien == 50000.0
    ).first()
    assert tx is not None
    assert tx.loai_gd == "chi"

def test_ai_nop_hu_tiet_kiem_tu_nhien(client, db_session, user_a, auth_headers_a, cat_thu_a):
    """
    Test người dùng nói: 'nộp 200k vào hũ du lịch'
    Hệ thống tự động:
    1. Tìm hũ Du lịch
    2. Kiểm tra số dư ví (tạo trước 1 khoản thu để có số dư)
    3. Trích nộp, cập nhật tiến độ mục tiêu tiết kiệm
    """
    # Tạo khoản thu để ví có tiền
    tx_thu = GiaoDich(ma_nd=user_a.ma_nd, ma_dm=cat_thu_a.ma_dm, so_tien=2000000.0, loai_gd="thu", ghi_chu="Lương")
    db_session.add(tx_thu)
    
    # Tạo mục tiêu tiết kiệm Du lịch
    goal = MucTieuTietKiem(
        ma_nd=user_a.ma_nd,
        ten_muc_tieu="Du lịch hè",
        so_tien_muc_tieu=1000000.0,
        so_tien_hien_tai=300000.0
    )
    db_session.add(goal)
    db_session.commit()

    payload = {"cau_hoi": "nộp 200k vào hũ du lịch hè"}
    res = client.post("/api/ai/hoi-dap", json=payload, headers=auth_headers_a)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    tra_loi = data["tra_loi"]

    assert "Du lịch hè" in tra_loi
    assert "200,000" in tra_loi

    # Kiểm tra CSDL tiến độ đã tăng lên 500.000đ (50%)
    db_session.refresh(goal)
    assert goal.so_tien_hien_tai == 500000.0

def test_ai_nang_muc_tieu_tiet_kiem_tu_nhien(client, db_session, user_a, auth_headers_a):
    """
    Test người dùng nói: 'Nâng mục tiêu lên 3tr5 giúp tôi'
    Hệ thống PHẢI:
    1. Cập nhật hạn mức mục tiêu tiết kiệm lên 3.500.000đ
    2. TUYỆT ĐỐI KHÔNG thêm giao dịch chi tiêu vào Ăn uống
    """
    goal = MucTieuTietKiem(
        ma_nd=user_a.ma_nd,
        ten_muc_tieu="Du lịch",
        so_tien_muc_tieu=3000000.0,
        so_tien_hien_tai=500000.0
    )
    db_session.add(goal)
    db_session.commit()

    # Đếm số giao dịch trước khi gọi
    tx_count_before = db_session.query(GiaoDich).filter(GiaoDich.ma_nd == user_a.ma_nd).count()

    payload = {"cau_hoi": "Nâng mục tiêu lên 3tr5 giúp tôi"}
    res = client.post("/api/ai/hoi-dap", json=payload, headers=auth_headers_a)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    tra_loi = data["tra_loi"]

    assert "cập nhật mục tiêu tiết kiệm thành công" in tra_loi.lower()
    assert "3,500,000" in tra_loi

    db_session.refresh(goal)
    assert goal.so_tien_muc_tieu == 3500000.0

    # Tuyệt đối không tạo giao dịch chi tiêu nhầm
    tx_count_after = db_session.query(GiaoDich).filter(GiaoDich.ma_nd == user_a.ma_nd).count()
    assert tx_count_after == tx_count_before

def test_ai_nang_han_muc_ngan_sach_tu_nhien(client, db_session, user_a, auth_headers_a, cat_chi_a):
    """
    Test người dùng nói: 'nâng hạn mức ăn uống lên 3 triệu'
    Hệ thống PHẢI:
    1. Điều chỉnh hạn mức hũ Ăn uống thành 3.000.000đ
    2. TUYỆT ĐỐI KHÔNG tạo giao dịch chi tiêu
    """
    tx_count_before = db_session.query(GiaoDich).filter(GiaoDich.ma_nd == user_a.ma_nd).count()

    payload = {"cau_hoi": f"nâng hạn mức {cat_chi_a.ten_dm} lên 3 triệu"}
    res = client.post("/api/ai/hoi-dap", json=payload, headers=auth_headers_a)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    tra_loi = data["tra_loi"]

    assert "điều chỉnh hạn mức ngân sách thành công" in tra_loi.lower()
    assert "3,000,000" in tra_loi

    db_session.refresh(cat_chi_a)
    assert cat_chi_a.han_muc == 3000000.0

    tx_count_after = db_session.query(GiaoDich).filter(GiaoDich.ma_nd == user_a.ma_nd).count()
    assert tx_count_after == tx_count_before

def test_ai_tao_hu_tiet_kiem_tu_nhien(client, db_session, user_a, auth_headers_a):
    """Test người dùng: 'tạo hũ tiết kiệm mua laptop 20 triệu'"""
    payload = {"cau_hoi": "tạo hũ tiết kiệm mua laptop 20 triệu"}
    res = client.post("/api/ai/hoi-dap", json=payload, headers=auth_headers_a)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert "tạo hũ tiết kiệm mới thành công" in data["tra_loi"].lower()
    assert "20,000,000" in data["tra_loi"]

    goal = db_session.query(MucTieuTietKiem).filter(
        MucTieuTietKiem.ma_nd == user_a.ma_nd,
        MucTieuTietKiem.so_tien_muc_tieu == 20000000.0
    ).first()
    assert goal is not None
    assert "laptop" in goal.ten_muc_tieu.lower()

def test_ai_rut_tien_hu_tiet_kiem_tu_nhien(client, db_session, user_a, auth_headers_a):
    """Test người dùng: 'rút 500k từ hũ du lịch về ví chính'"""
    goal = MucTieuTietKiem(
        ma_nd=user_a.ma_nd,
        ten_muc_tieu="Du lịch biển",
        so_tien_muc_tieu=3000000.0,
        so_tien_hien_tai=1000000.0
    )
    db_session.add(goal)
    db_session.commit()

    payload = {"cau_hoi": "rút 500k từ hũ du lịch biển về ví chính"}
    res = client.post("/api/ai/hoi-dap", json=payload, headers=auth_headers_a)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert "rút tiền từ hũ tiết kiệm về ví chính thành công" in data["tra_loi"].lower()
    assert "500,000" in data["tra_loi"]

    db_session.refresh(goal)
    assert goal.so_tien_hien_tai == 500000.0

def test_ai_xoa_hu_tiet_kiem_tu_nhien(client, db_session, user_a, auth_headers_a):
    """Test người dùng: 'xóa hũ du lịch' -> hoàn tiền về ví và xóa hũ"""
    goal = MucTieuTietKiem(
        ma_nd=user_a.ma_nd,
        ten_muc_tieu="Du lịch hè",
        so_tien_muc_tieu=2000000.0,
        so_tien_hien_tai=400000.0
    )
    db_session.add(goal)
    db_session.commit()
    goal_id = goal.ma_mt

    payload = {"cau_hoi": "xóa hũ du lịch hè"}
    res = client.post("/api/ai/hoi-dap", json=payload, headers=auth_headers_a)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert "xóa hũ tiết kiệm" in data["tra_loi"].lower()
    assert "400,000" in data["tra_loi"]

    # Xác nhận xóa lượt 2 (Multi-turn Confirmation)
    res_confirm = client.post("/api/ai/hoi-dap", json={"cau_hoi": "đồng ý"}, headers=auth_headers_a)
    assert res_confirm.status_code == status.HTTP_200_OK
    assert "xóa hũ tiết kiệm" in res_confirm.json()["tra_loi"].lower() and "thành công" in res_confirm.json()["tra_loi"].lower()

    deleted = db_session.query(MucTieuTietKiem).filter(MucTieuTietKiem.ma_mt == goal_id).first()
    assert deleted is None

def test_ai_tao_danh_muc_tu_nhien(client, db_session, user_a, auth_headers_a):
    """Test người dùng: 'tạo danh mục học tập hạn mức 1 triệu'"""
    payload = {"cau_hoi": "tạo danh mục học tập hạn mức 1 triệu"}
    res = client.post("/api/ai/hoi-dap", json=payload, headers=auth_headers_a)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert "tạo danh mục mới thành công" in data["tra_loi"].lower()

    cat = db_session.query(DanhMuc).filter(
        DanhMuc.ma_nd == user_a.ma_nd,
        DanhMuc.ten_dm.ilike("%học tập%")
    ).first()
    assert cat is not None
    assert cat.han_muc == 1000000.0

def test_ai_doi_ten_danh_muc_tu_nhien(client, db_session, user_a, auth_headers_a):
    """Test người dùng: 'đổi tên danh mục đi chơi thành giải trí'"""
    cat = DanhMuc(ten_dm="Đi chơi", loai_dm="chi", han_muc=500000.0, ma_nd=user_a.ma_nd)
    db_session.add(cat)
    db_session.commit()

    payload = {"cau_hoi": "đổi tên danh mục đi chơi thành giải trí"}
    res = client.post("/api/ai/hoi-dap", json=payload, headers=auth_headers_a)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert "đổi tên danh mục thành công" in data["tra_loi"].lower()

    db_session.refresh(cat)
    assert cat.ten_dm == "Giải trí"

def test_ai_sua_giao_dich_tu_nhien(client, db_session, user_a, auth_headers_a, cat_chi_a):
    """Test người dùng: 'sửa giao dịch gần nhất thành 45k'"""
    tx = GiaoDich(ma_nd=user_a.ma_nd, ma_dm=cat_chi_a.ma_dm, so_tien=30000.0, loai_gd="chi", ghi_chu="Mua cafe")
    db_session.add(tx)
    db_session.commit()

    payload = {"cau_hoi": "sửa giao dịch gần nhất thành 45k"}
    res = client.post("/api/ai/hoi-dap", json=payload, headers=auth_headers_a)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert "cập nhật giao dịch thành công" in data["tra_loi"].lower()
    assert "45,000" in data["tra_loi"]

    db_session.refresh(tx)
    assert tx.so_tien == 45000.0

def test_ai_xoa_giao_dich_tu_nhien(client, db_session, user_a, auth_headers_a, cat_chi_a):
    """Test người dùng: 'xóa giao dịch vừa thêm'"""
    tx = GiaoDich(ma_nd=user_a.ma_nd, ma_dm=cat_chi_a.ma_dm, so_tien=25000.0, loai_gd="chi", ghi_chu="Ăn bánh bao")
    db_session.add(tx)
    db_session.commit()
    tx_id = tx.ma_gd

    payload = {"cau_hoi": "xóa giao dịch vừa thêm"}
    res = client.post("/api/ai/hoi-dap", json=payload, headers=auth_headers_a)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert "xác nhận xóa" in data["tra_loi"].lower()
    assert "25,000" in data["tra_loi"]

    # Xác nhận xóa lượt 2 (Multi-turn Confirmation)
    res_confirm = client.post("/api/ai/hoi-dap", json={"cau_hoi": "đồng ý"}, headers=auth_headers_a)
    assert res_confirm.status_code == status.HTTP_200_OK
    assert "xóa giao dịch thành công" in res_confirm.json()["tra_loi"].lower()

    deleted = db_session.query(GiaoDich).filter(GiaoDich.ma_gd == tx_id).first()
    assert deleted is None

def test_ai_tra_cuu_giao_dich_tu_nhien(client, db_session, user_a, auth_headers_a, cat_chi_a):
    """Test người dùng: 'tìm các giao dịch ăn uống'"""
    tx1 = GiaoDich(ma_nd=user_a.ma_nd, ma_dm=cat_chi_a.ma_dm, so_tien=35000.0, loai_gd="chi", ghi_chu="Phở bò")
    tx2 = GiaoDich(ma_nd=user_a.ma_nd, ma_dm=cat_chi_a.ma_dm, so_tien=20000.0, loai_gd="chi", ghi_chu="Bánh mì que")
    db_session.add_all([tx1, tx2])
    db_session.commit()

    payload = {"cau_hoi": "tìm các giao dịch ăn uống"}
    res = client.post("/api/ai/hoi-dap", json=payload, headers=auth_headers_a)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    tra_loi = data["tra_loi"]
    assert "kết quả tra cứu giao dịch" in tra_loi.lower()
    assert "35,000" in tra_loi or "20,000" in tra_loi

def test_ai_danh_gia_suc_khoe_tai_chinh(client, db_session, user_a, auth_headers_a, cat_thu_a):
    """Test người dùng: 'đánh giá sức khỏe tài chính' -> Trả về điểm số & 6 chiếc hũ"""
    tx_thu = GiaoDich(ma_nd=user_a.ma_nd, ma_dm=cat_thu_a.ma_dm, so_tien=15000000.0, loai_gd="thu", ghi_chu="Lương tháng")
    db_session.add(tx_thu)
    db_session.commit()

    payload = {"cau_hoi": "đánh giá sức khỏe tài chính"}
    res = client.post("/api/ai/hoi-dap", json=payload, headers=auth_headers_a)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    tra_loi = data["tra_loi"]
    assert "đánh giá sức khỏe tài chính" in tra_loi.lower()
    assert "phương pháp 6 chiếc hũ" in tra_loi.lower()


def test_ai_lam_sach_mo_ta_giao_dich_khong_chua_tu_thua_va_so_tien(client, db_session, user_a, auth_headers_a):
    """
    Test người dùng chat: 'vừa đi ăn bánh cuốn hết 35k'
    Yêu cầu:
    1. Số tiền là 35,000đ
    2. Mô tả (ghi_chu) KHÔNG chứa từ thừa 'vừa' / 'vừa đi', và KHÔNG chứa số tiền '35k' / 'hết 35k'
    3. Ghi chú chuẩn phải là: 'Ăn bánh cuốn'
    """
    payload = {"cau_hoi": "vừa đi ăn bánh cuốn hết 35k"}
    res = client.post("/api/ai/hoi-dap", json=payload, headers=auth_headers_a)
    assert res.status_code == status.HTTP_200_OK

    tx = db_session.query(GiaoDich).filter(
        GiaoDich.ma_nd == user_a.ma_nd,
        GiaoDich.so_tien == 35000.0,
        GiaoDich.loai_gd == "chi"
    ).order_by(GiaoDich.ma_gd.desc()).first()

    assert tx is not None
    assert tx.ghi_chu == "Ăn bánh cuốn"
    assert "35k" not in tx.ghi_chu
    assert "vừa" not in tx.ghi_chu.lower()


def test_ai_nang_quy_tiet_kiem_theo_ten_tu_nhien(client, db_session, user_a, auth_headers_a):
    """
    Test: 'nâng giúp tôi quỹ tiết kiệm đi chơi đà lạt lên 2 triệu 500'
    Hệ thống PHẢI:
    1. Tìm đúng hũ 'đi chơi Đà Lạt'
    2. Cập nhật số tiền mục tiêu thành 2.500.000đ trong CSDL
    3. Trả về thông báo thành công xác nhận số tiền mới
    """
    goal = MucTieuTietKiem(
        ma_nd=user_a.ma_nd,
        ten_muc_tieu="đi chơi Đà Lạt",
        so_tien_muc_tieu=2000000.0,
        so_tien_hien_tai=500000.0
    )
    db_session.add(goal)
    db_session.commit()

    payload = {"cau_hoi": "nâng giúp tôi quỹ tiết kiệm đi chơi đà lạt lên 2 triệu 500"}
    res = client.post("/api/ai/hoi-dap", json=payload, headers=auth_headers_a)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    tra_loi = data["tra_loi"]

    assert "cập nhật mục tiêu tiết kiệm thành công" in tra_loi.lower()
    assert "2,500,000" in tra_loi
    assert "đi chơi Đà Lạt" in tra_loi or "đi chơi đà lạt" in tra_loi.lower()

    db_session.refresh(goal)
    assert goal.so_tien_muc_tieu == 2500000.0


def test_ai_multi_turn_giao_dich_tu_nhien(client, db_session, user_a, auth_headers_a):
    """
    Test hội thoại đa lượt:
    Lượt 1: Người dùng nói 'trưa nay tôi đi ăn cơm' (chưa có số tiền)
    AI hỏi: 'Bữa trưa nay của bạn hết bao nhiêu tiền thế nè? Bạn nhắn cho mình xin số tiền để mình ghi nhận ngay vào danh mục Ăn uống nhé!'
    Lượt 2: Người dùng nhắn '30k' kèm lịch sử chat
    Hệ thống PHẢI:
    1. Tự động nhận diện '30k' là số tiền cho bữa ăn trưa ở lượt 1
    2. Ghi nhận giao dịch 30.000đ vào CSDL với danh mục 'Ăn uống' và ghi chú 'Ăn cơm' (hoặc 'Ăn trưa')
    3. Trả về thông báo ghi nhận thành công xác nhận số tiền 30.000đ
    """
    payload = {
        "cau_hoi": "30k",
        "lich_su_chat": [
            {"role": "user", "content": "trưa nay tôi đi ăn cơm"},
            {"role": "assistant", "content": "Bữa trưa nay của bạn hết bao nhiêu tiền thế nè? Bạn nhắn cho mình xin số tiền để mình ghi nhận ngay vào danh mục Ăn uống nhé!"}
        ]
    }
    res = client.post("/api/ai/hoi-dap", json=payload, headers=auth_headers_a)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    tra_loi = data["tra_loi"]

    assert "đã ghi nhận giao dịch thành công" in tra_loi.lower()
    assert "30,000" in tra_loi
    assert "Ăn uống" in tra_loi

    tx = db_session.query(GiaoDich).filter(
        GiaoDich.ma_nd == user_a.ma_nd,
        GiaoDich.so_tien == 30000.0,
        GiaoDich.loai_gd == "chi"
    ).order_by(GiaoDich.ma_gd.desc()).first()

    assert tx is not None
    assert tx.so_tien == 30000.0




