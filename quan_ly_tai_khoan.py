"""
Công cụ Quản trị & Quản lý Tài khoản MoneyMind (CLI Tool)
Cho phép:
1. Liệt kê danh sách tất cả tài khoản đã đăng ký trong hệ thống
2. Xóa sạch vĩnh viễn 100% dữ liệu của tài khoản (giao dịch, danh mục, hũ, tiết kiệm, OTP...)
   Giúp Gmail đó trở về trạng thái như chưa từng đăng ký.
"""

import sys
import sqlite3
import argparse

sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = "tai_chinh.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def list_users():
    con = get_connection()
    cur = con.cursor()
    
    print("\n" + "=" * 70)
    print("📋 DANH SÁCH TÀI KHOẢN ĐÃ ĐĂNG KÝ TRONG HỆ THỐNG")
    print("=" * 70)
    
    users = cur.execute("""
        SELECT ma_nd, email, ho_ten, trang_thai, ngay_tao 
        FROM nguoi_dung 
        ORDER BY ma_nd ASC
    """).fetchall()
    
    if not users:
        print("  (Chưa có tài khoản nào được đăng ký)")
        con.close()
        return []
    
    print(f"{'ID':<5} | {'Email':<32} | {'Họ tên':<15} | {'Số GD':<6} | {'Ngày tạo'}")
    print("-" * 70)
    
    for u in users:
        ma_nd, email, ho_ten, status, created = u
        ho_ten_str = ho_ten or "---"
        created_str = str(created)[:16] if created else "---"
        
        # Đếm số giao dịch
        tx_count = cur.execute("SELECT count(*) FROM giao_dich WHERE ma_nd = ?", (ma_nd,)).fetchone()[0]
        
        print(f"{ma_nd:<5} | {email:<32} | {ho_ten_str:<15} | {tx_count:<6} | {created_str}")
    
    print("=" * 70)
    con.close()
    return users

def delete_user_completely(identifier):
    """
    Xóa sạch 100% dữ liệu của 1 tài khoản dựa trên Email hoặc ID.
    Sau khi xóa, email này hoàn toàn như mới, có thể đăng ký lại từ đầu.
    """
    con = get_connection()
    cur = con.cursor()
    
    # Tìm kiếm theo ID hoặc Email
    user = None
    if str(identifier).isdigit():
        user = cur.execute("SELECT ma_nd, email, ho_ten FROM nguoi_dung WHERE ma_nd = ?", (int(identifier),)).fetchone()
    
    if not user:
        user = cur.execute("SELECT ma_nd, email, ho_ten FROM nguoi_dung WHERE LOWER(email) = LOWER(?)", (str(identifier).strip(),)).fetchone()
    
    if not user:
        # Thử tìm trong bảng users legacy nếu có
        user_legacy = cur.execute("SELECT id, username, full_name FROM users WHERE LOWER(username) = LOWER(?)", (str(identifier).strip(),)).fetchone()
        if user_legacy:
            user = (user_legacy[0], user_legacy[1], user_legacy[2])
    
    if not user:
        print(f"\n❌ Không tìm thấy tài khoản nào khớp với '{identifier}'!")
        con.close()
        return False
    
    ma_nd, email, ho_ten = user
    print(f"\n⚠️  BẮT ĐẦU XÓA SẠCH DỮ LIỆU TÀI KHOẢN:")
    print(f"   • ID: {ma_nd}")
    print(f"   • Email: {email}")
    print(f"   • Họ tên: {ho_ten or '---'}")
    
    deleted_counts = {}
    
    # 1. Bảng giao dịch
    try:
        cur.execute("DELETE FROM giao_dich WHERE ma_nd = ?", (ma_nd,))
        deleted_counts["giao_dich"] = cur.rowcount
    except Exception:
        pass
    try:
        cur.execute("DELETE FROM transactions WHERE user_id = ?", (ma_nd,))
        deleted_counts["transactions_legacy"] = cur.rowcount
    except Exception:
        pass
        
    # 2. Bảng mục tiêu tiết kiệm
    try:
        cur.execute("DELETE FROM muc_tieu_tiet_kiem WHERE ma_nd = ?", (ma_nd,))
        deleted_counts["muc_tieu_tiet_kiem"] = cur.rowcount
    except Exception:
        pass
    try:
        cur.execute("DELETE FROM savings_goals WHERE user_id = ?", (ma_nd,))
        deleted_counts["savings_goals_legacy"] = cur.rowcount
    except Exception:
        pass

    # 3. Bảng ngân sách
    try:
        cur.execute("DELETE FROM ngan_sach WHERE ma_nd = ?", (ma_nd,))
        deleted_counts["ngan_sach"] = cur.rowcount
    except Exception:
        pass

    # 4. Bảng danh mục
    try:
        cur.execute("DELETE FROM danh_muc WHERE ma_nd = ?", (ma_nd,))
        deleted_counts["danh_muc"] = cur.rowcount
    except Exception:
        pass
    try:
        cur.execute("DELETE FROM categories WHERE user_id = ?", (ma_nd,))
        deleted_counts["categories_legacy"] = cur.rowcount
    except Exception:
        pass

    # 5. Bảng thông báo
    try:
        cur.execute("DELETE FROM thong_bao WHERE ma_nd = ?", (ma_nd,))
        deleted_counts["thong_bao"] = cur.rowcount
    except Exception:
        pass
    try:
        cur.execute("DELETE FROM notifications WHERE user_id = ?", (ma_nd,))
        deleted_counts["notifications_legacy"] = cur.rowcount
    except Exception:
        pass

    # 6. Báo cáo AI
    try:
        cur.execute("DELETE FROM bao_cao_ai WHERE ma_nd = ?", (ma_nd,))
        deleted_counts["bao_cao_ai"] = cur.rowcount
    except Exception:
        pass

    # 7. OTP và đặt lại mật khẩu
    try:
        cur.execute("DELETE FROM xac_nhan_otp WHERE LOWER(email) = LOWER(?)", (email,))
        deleted_counts["xac_nhan_otp"] = cur.rowcount
    except Exception:
        pass
    try:
        cur.execute("DELETE FROM dat_lai_mat_khau WHERE ma_nd = ?", (ma_nd,))
        deleted_counts["dat_lai_mat_khau"] = cur.rowcount
    except Exception:
        pass

    # 8. Bảng người dùng chính
    try:
        cur.execute("DELETE FROM nguoi_dung WHERE ma_nd = ?", (ma_nd,))
        deleted_counts["nguoi_dung"] = cur.rowcount
    except Exception:
        pass
    try:
        cur.execute("DELETE FROM users WHERE id = ? OR LOWER(username) = LOWER(?)", (ma_nd, email))
        deleted_counts["users_legacy"] = cur.rowcount
    except Exception:
        pass

    con.commit()
    con.close()
    
    print("\n✅ ĐÃ XÓA SẠCH HOÀN TOÀN:")
    for tbl, cnt in deleted_counts.items():
        if cnt > 0:
            print(f"   - {tbl}: đã xóa {cnt} dòng")
            
    print(f"\n🎉 Email '{email}' giờ đây hoàn toàn trắng dữ liệu và như một tài khoản chưa từng đăng ký!")
    print("👉 Bạn có thể dùng Gmail này để Đăng ký mới ngay lập tức.\n")
    return True

def interactive_menu():
    while True:
        print("\n" + "=" * 50)
        print("🛠️  HỆ THỐNG QUẢN LÝ TÀI KHOẢN MONEYMIND")
        print("=" * 50)
        print("1. Xem danh sách tất cả tài khoản")
        print("2. Xóa tài khoản vĩnh viễn (xóa trắng dữ liệu)")
        print("0. Thoát")
        choice = input("👉 Chọn chức năng (0-2): ").strip()
        
        if choice == "1":
            list_users()
        elif choice == "2":
            list_users()
            target = input("\nNhập Email hoặc ID tài khoản bạn muốn xóa: ").strip()
            if target:
                confirm = input(f"Bạn có CHẮC CHẮN muốn xóa sạch tài khoản '{target}' không? (y/N): ").strip().lower()
                if confirm in ['y', 'yes']:
                    delete_user_completely(target)
                else:
                    print("Đã hủy thao tác xóa.")
        elif choice == "0":
            print("Tạm biệt!")
            break
        else:
            print("Lựa chọn không hợp lệ, vui lòng chọn lại.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Quản lý tài khoản MoneyMind")
    parser.add_argument("action", nargs="?", choices=["list", "delete"], help="Hành động: list hoặc delete")
    parser.add_argument("target", nargs="?", help="Email hoặc ID tài khoản cần xóa")
    
    args = parser.parse_args()
    
    if args.action == "list":
        list_users()
    elif args.action == "delete":
        if not args.target:
            print("Vui lòng cung cấp Email hoặc ID cần xóa. Ví dụ: python quan_ly_tai_khoan.py delete hienluong03legit@gmail.com")
        else:
            delete_user_completely(args.target)
    else:
        # Nếu không có tham số dòng lệnh, chạy menu tương tác hoặc hiển thị danh sách
        list_users()

# chạy python quan_ly_tai_khoan.py list
# chạy python quan_ly_tai_khoan.py delete <email_hoặc_id>
# chạy python quan_ly_tai_khoan.py delete example@gmail.com
# chạy lại python quan_ly_tai_khoan.py

