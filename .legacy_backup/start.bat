@echo off
chcp 65001 >nul
title MoneyMind - Quản Lý Tài Chính Toàn Diện

echo ========================================================
echo        🚀 Đang khởi động hệ thống MoneyMind...
echo ========================================================
echo.

cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo [LỖI] Không tìm thấy môi trường ảo venv!
    echo Vui lòng tạo venv hoặc cài đặt môi trường.
    pause
    exit /b 1
)

echo [1/2] Đang khởi động máy chủ FastAPI tại http://127.0.0.1:8000 ...
start "" http://127.0.0.1:8000

echo [2/2] Máy chủ đang hoạt động. Nhấn Ctrl+C để dừng hệ thống.
echo.
venv\Scripts\python.exe main.py
