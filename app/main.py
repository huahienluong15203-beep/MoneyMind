import os
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.exceptions import RequestValidationError
from app.core.config import settings
from app.core.database import engine, Base, migrate_legacy_data
import app.models  # Đảm bảo nạp toàn bộ models để tạo bảng
from app.controllers import (
    auth_router,
    nguoi_dung_router,
    danh_muc_router,
    giao_dich_router,
    ngan_sach_router,
    muc_tieu_router,
    thong_ke_router,
    ai_router
)

# Tự động tạo các bảng CSDL & migrate
Base.metadata.create_all(bind=engine)
migrate_legacy_data()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Hệ thống Quản lý Tài chính Cá nhân Thông minh tích hợp Trí tuệ Nhân tạo (AI)",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Bắt lỗi validation input Pydantic -> mã 400 (theo quy ước mục 4.3)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    first_err = errors[0] if errors else {}
    msg = first_err.get("msg", "Dữ liệu đầu vào không hợp lệ")
    loc = " -> ".join(str(l) for l in first_err.get("loc", []))
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": f"{msg} (Trường: {loc})", "errors": errors}
    )

# Đăng ký các router controllers REST API chuẩn (Mục 4.3)
app.include_router(auth_router)
app.include_router(nguoi_dung_router)
app.include_router(danh_muc_router)
app.include_router(giao_dich_router)
app.include_router(ngan_sach_router)
app.include_router(muc_tieu_router)
app.include_router(thong_ke_router)
app.include_router(ai_router)

@app.api_route("/api/health", methods=["GET", "HEAD"], tags=["Hệ thống"])
def health_check():
    return {
        "status": "healthy",
        "app": settings.PROJECT_NAME,
        "version": "2.0.0"
    }

from fastapi.staticfiles import StaticFiles

# Phục vụ giao diện web frontend và static assets (css, js)
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    css_dir = os.path.join(frontend_dir, "css")
    js_dir = os.path.join(frontend_dir, "js")
    if os.path.exists(css_dir):
        app.mount("/css", StaticFiles(directory=css_dir), name="css")
    if os.path.exists(js_dir):
        app.mount("/js", StaticFiles(directory=js_dir), name="js")
    icons_dir = os.path.join(frontend_dir, "icons")
    if os.path.exists(icons_dir):
        app.mount("/icons", StaticFiles(directory=icons_dir), name="icons")
    app.mount("/frontend", StaticFiles(directory=frontend_dir), name="frontend")

from fastapi.responses import FileResponse

@app.get("/manifest.json")
def get_manifest():
    manifest_path = os.path.join(frontend_dir, "manifest.json")
    if os.path.exists(manifest_path):
        return FileResponse(manifest_path, media_type="application/manifest+json")
    raise HTTPException(status_code=404, detail="Manifest not found")

@app.get("/sw.js")
def get_service_worker():
    sw_path = os.path.join(frontend_dir, "sw.js")
    if os.path.exists(sw_path):
        return FileResponse(sw_path, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="SW not found")

@app.get("/.well-known/assetlinks.json")
def get_assetlinks():
    assetlinks_path = os.path.join(frontend_dir, ".well-known", "assetlinks.json")
    if os.path.exists(assetlinks_path):
        return FileResponse(assetlinks_path, media_type="application/json")
    return JSONResponse(
        content=[{
            "relation": ["delegate_permission/common.handle_all_urls"],
            "target": {
                "namespace": "android_app",
                "package_name": "com.moneymind.app",
                "sha256_cert_fingerprints": ["72:E7:92:4B:CF:61:BB:02:E8:83:E6:D7:69:84:91:CD:5A:B9:54:05:D4:B7:D9:ED:49:44:A9:5C:56:74:17:47"]
            }
        }]
    )

@app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse, summary="Giao diện Web MoneyMind")
def ung_dung_money_mind():
    frontend_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(frontend_path):
        with open(frontend_path, "r", encoding="utf-8") as f:
            content = f.read()
            return HTMLResponse(content=content, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
    return HTMLResponse("<h1>MoneyMind API Server is running</h1>")

