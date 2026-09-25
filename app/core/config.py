import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()
except Exception:
    pass

class Settings:
    PROJECT_NAME: str = "MoneyMind - Quản Lý Tài Chính Toàn Diện"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./tai_chinh.db")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "CHUOI_BI_MAT_SIEU_CAP_CHO_DO_AN_MONEYMIND_2026")
    REFRESH_SECRET_KEY: str = os.getenv("REFRESH_SECRET_KEY", "CHUOI_BI_MAT_REFRESH_TOKEN_MONEYMIND_2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 ngày
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    AI_TIMEOUT_SECONDS: float = 30.0  # NFR-03 (tăng lên 30s để Gemini phản hồi đủ)
    MAX_FAILED_LOGINS: int = 5
    LOCKOUT_MINUTES: int = 15

    # Cấu hình gửi mail OTP qua Google Apps Script Web App (Không cần mật khẩu ứng dụng)
    GOOGLE_APPS_SCRIPT_URL: str = os.getenv("GOOGLE_APPS_SCRIPT_URL", "")

    # Cấu hình gửi mail OTP qua Gmail SMTP
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")  # Mật khẩu ứng dụng Gmail (App Password)
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "")

settings = Settings()
