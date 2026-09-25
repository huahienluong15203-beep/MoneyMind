from app.controllers.auth_controller import router as auth_router
from app.controllers.nguoi_dung_controller import router as nguoi_dung_router
from app.controllers.danh_muc_controller import router as danh_muc_router
from app.controllers.giao_dich_controller import router as giao_dich_router
from app.controllers.ngan_sach_controller import router as ngan_sach_router
from app.controllers.muc_tieu_controller import router as muc_tieu_router
from app.controllers.thong_ke_controller import router as thong_ke_router
from app.controllers.ai_controller import router as ai_router

__all__ = [
    "auth_router",
    "nguoi_dung_router",
    "danh_muc_router",
    "giao_dich_router",
    "ngan_sach_router",
    "muc_tieu_router",
    "thong_ke_router",
    "ai_router"
]
