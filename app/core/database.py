import os
import sqlite3
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def migrate_legacy_data():
    """Tự động đồng bộ/chuyển đổi dữ liệu từ các bảng cũ nếu có sang schema chuẩn theo báo cáo"""
    db_path = "./tai_chinh.db"
    if not os.path.exists(db_path):
        return
    try:
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]

        # 1. users -> nguoi_dung
        if "users" in tables and "nguoi_dung" in tables:
            cur.execute("SELECT count(*) FROM nguoi_dung")
            count_nd = cur.fetchone()[0]
            if count_nd == 0:
                cur.execute("""
                    INSERT OR IGNORE INTO nguoi_dung (ma_nd, ho_ten, email, mat_khau_hash, trang_thai, dob, occupation, goals, ngay_tao)
                    SELECT id, full_name, username, hashed_password, 'hoat_dong', dob, occupation, goals, datetime('now')
                    FROM users
                """)
                con.commit()

        # 2. categories -> danh_muc
        if "categories" in tables and "danh_muc" in tables:
            cur.execute("SELECT count(*) FROM danh_muc")
            count_dm = cur.fetchone()[0]
            if count_dm == 0:
                cur.execute("""
                    INSERT OR IGNORE INTO danh_muc (ma_dm, ma_nd, ten_dm, loai_dm, icon, mau_sac, han_muc)
                    SELECT id, user_id, name, type, 'tag', '#0ea5e9', budget_limit
                    FROM categories
                """)
                con.commit()

        # 3. transactions -> giao_dich
        if "transactions" in tables and "giao_dich" in tables:
            cur.execute("SELECT count(*) FROM giao_dich")
            count_gd = cur.fetchone()[0]
            if count_gd == 0:
                cur.execute("""
                    INSERT OR IGNORE INTO giao_dich (ma_gd, ma_nd, ma_dm, so_tien, loai_gd, ngay_gd, ghi_chu, ngay_tao)
                    SELECT id, user_id, category_id, amount, type, date, note, datetime('now')
                    FROM transactions
                """)
                con.commit()

        # 4. savings_goals -> muc_tieu_tiet_kiem
        if "savings_goals" in tables and "muc_tieu_tiet_kiem" in tables:
            cur.execute("SELECT count(*) FROM muc_tieu_tiet_kiem")
            count_mt = cur.fetchone()[0]
            if count_mt == 0:
                cur.execute("""
                    INSERT OR IGNORE INTO muc_tieu_tiet_kiem (ma_mt, ma_nd, ten_muc_tieu, so_tien_muc_tieu, so_tien_hien_tai, han_chot, trang_thai)
                    SELECT id, user_id, title, target_amount, current_amount, deadline, 'dang_thuc_hien'
                    FROM savings_goals
                """)
                con.commit()

        # 5. notifications -> thong_bao
        if "notifications" in tables and "thong_bao" in tables:
            cur.execute("SELECT count(*) FROM thong_bao")
            count_tb = cur.fetchone()[0]
            if count_tb == 0:
                cur.execute("""
                    INSERT OR IGNORE INTO thong_bao (id, ma_nd, tieu_de, noi_dung, ngay_tao)
                    SELECT id, user_id, title, message, created_at
                    FROM notifications
                """)
                con.commit()

        # 6. Thêm cột da_xem nếu chưa có
        if "thong_bao" in tables:
            cols = [info[1] for info in cur.execute("PRAGMA table_info(thong_bao)").fetchall()]
            if "da_xem" not in cols:
                cur.execute("ALTER TABLE thong_bao ADD COLUMN da_xem BOOLEAN DEFAULT 0")
                con.commit()

        con.close()
    except Exception as e:
        print("Lỗi migrate legacy data:", e)
