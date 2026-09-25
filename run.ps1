# MoneyMind Quick Starter Script
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "       🚀 Đang khởi động hệ thống MoneyMind...          " -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Cyan

$CurrentDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $CurrentDir

$PythonPath = Join-Path $CurrentDir "venv\Scripts\python.exe"
if (-not (Test-Path $PythonPath)) {
    Write-Host "[LỖI] Không tìm thấy môi trường ảo venv tại: $PythonPath" -ForegroundColor Red
    exit 1
}

Write-Host "[1/2] Đang mở trình duyệt tại http://127.0.0.1:8000 ..." -ForegroundColor Yellow
Start-Process "http://127.0.0.1:8000"

Write-Host "[2/2] Máy chủ đang chạy. Nhấn Ctrl+C để dừng." -ForegroundColor Green
& $PythonPath "main.py"
