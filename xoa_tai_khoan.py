# -*- coding: utf-8 -*-
"""
MoneyMind - Quan ly & Xoa tai khoan kiem thu
Su dung:
    python xoa_tai_khoan.py                 # Hien thi danh sach va chon tai khoan can xoa
    python xoa_tai_khoan.py <email/id>      # Xoa truc tiep theo email hoac ID
"""

import sqlite3
import os
import sys

# Ho tro hien thi tieng Viet tren Windows console ma khong loi cp1252
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
    except Exception:
        pass

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tai_chinh.db')

def get_connection():
    if not os.path.exists(DB_PATH):
        print(f"Khong tim thay database tai: {DB_PATH}")
        sys.exit(1)
    return sqlite3.connect(DB_PATH)

def list_users():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ma_nd, email, ho_ten, dob, occupation, ngay_tao 
        FROM nguoi_dung 
        ORDER BY ma_nd ASC;
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows

def safe_str(val):
    if not val:
        return "---"
    return str(val)

def print_user_table(users):
    print("=" * 85)
    print(f"{'STT':<4} | {'ID':<4} | {'Email':<30} | {'Ho va ten':<22} | {'Ngay tao'}")
    print("-" * 85)
    for idx, u in enumerate(users, 1):
        ma_nd, email, name, dob, occ, created = u
        name_str = name if name else "(Chua thiet lap)"
        created_str = str(created)[:19] if created else "---"
        try:
            print(f"{idx:<4} | {ma_nd:<4} | {email:<30} | {name_str:<22} | {created_str}")
        except UnicodeEncodeError:
            print(f"{idx:<4} | {ma_nd:<4} | {email:<30} | {name_str.encode('ascii', 'replace').decode('ascii'):<22} | {created_str}")
    print("=" * 85)

def delete_user_by_id_or_email(identifier):
    conn = get_connection()
    cursor = conn.cursor()

    # Tim tai khoan
    if str(identifier).isdigit():
        cursor.execute("SELECT ma_nd, email, ho_ten FROM nguoi_dung WHERE ma_nd = ?;", (int(identifier),))
    else:
        cursor.execute("SELECT ma_nd, email, ho_ten FROM nguoi_dung WHERE LOWER(email) = LOWER(?);", (str(identifier).strip(),))

    user = cursor.fetchone()
    if not user:
        print(f"[-] Khong tim thay tai khoan voi: '{identifier}'")
        conn.close()
        return False

    ma_nd, email, name = user
    print(f"\n[*] Dang tien hanh xoa sach toan bo du lieu cua tai khoan:")
    print(f"    - ID: {ma_nd}")
    print(f"    - Email: {email}")
    try:
        print(f"    - Ho ten: {name if name else '(Chua thiet lap)'}")
    except UnicodeEncodeError:
        print(f"    - Ho ten: {name.encode('ascii', 'replace').decode('ascii') if name else '(Chua thiet lap)'}")

    # Xoa du lieu lien quan o cac bang con
    tables_by_ma_nd = [
        'giao_dich',
        'danh_muc',
        'ngan_sach',
        'muc_tieu_tiet_kiem',
        'thong_bao',
        'ket_chuyen_ngan_sach',
        'lich_su_ai',
        'bao_cao_ai',
        'dat_lai_mat_khau'
    ]

    for tbl in tables_by_ma_nd:
        try:
            cursor.execute(f"DELETE FROM {tbl} WHERE ma_nd = ?;", (ma_nd,))
            deleted = cursor.rowcount
            if deleted > 0:
                print(f"    + Da xoa {deleted} dong trong bang '{tbl}'")
        except sqlite3.OperationalError:
            pass

    # Xoa ma OTP
    try:
        cursor.execute("DELETE FROM xac_nhan_otp WHERE LOWER(email) = LOWER(?);", (email,))
        if cursor.rowcount > 0:
            print(f"    + Da xoa {cursor.rowcount} ma OTP trong bang 'xac_nhan_otp'")
    except sqlite3.OperationalError:
        pass

    # Xoa khoi bang users cu neu co
    try:
        cursor.execute("DELETE FROM users WHERE username = ? OR id = ?;", (email, ma_nd))
    except sqlite3.OperationalError:
        pass

    # Xoa dong trong nguoi_dung
    cursor.execute("DELETE FROM nguoi_dung WHERE ma_nd = ?;", (ma_nd,))
    conn.commit()
    conn.close()

    print(f"\n[+] >>> DA XOA HOAN TOAN TAI KHOAN: {email} <<<")
    print("    Ban co the dung email nay de dang ky lai tai khoan moi tu dau!\n")
    return True

def main():
    if len(sys.argv) > 1:
        target = sys.argv[1]
        delete_user_by_id_or_email(target)
        return

    users = list_users()
    if not users:
        print("Hien tai khong co tai khoan nao trong co so du lieu.")
        return

    print("\nDANH SACH TAI KHOAN TRONG DATABASE MONEYMIND:")
    print_user_table(users)
    print("\nCach dung nhanh:")
    print("  python xoa_tai_khoan.py <email/id>")
    print("  Hoac go email / ID can xoa ben duoi (go 'q' de thoat):")

    try:
        choice = input(">> Nhap email hoac ID/STT muon xoa: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nDa huy thao tac.")
        return

    if not choice or choice.lower() == 'q':
        print("Da thoat.")
        return

    if choice.isdigit():
        num = int(choice)
        if 1 <= num <= len(users):
            selected_user = users[num - 1]
            delete_user_by_id_or_email(str(selected_user[0]))
            return

    delete_user_by_id_or_email(choice)

if __name__ == '__main__':
    main()
