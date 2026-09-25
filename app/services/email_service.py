import smtplib
import random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Tuple
from app.core.config import settings

class EmailService:
    @staticmethod
    def generate_otp() -> str:
        """Tạo mã xác nhận OTP gồm 6 chữ số ngẫu nhiên"""
        return f"{random.randint(100000, 999999)}"

    @staticmethod
    def send_registration_otp(to_email: str, otp_code: str) -> Tuple[bool, str]:
        """
        Gửi mã OTP xác nhận đăng ký tài khoản về hòm thư Gmail của người dùng.
        Hỗ trợ 2 phương thức:
        1. Google Apps Script Web App (Tự động gửi email thật mà không cần mật khẩu ứng dụng).
        2. SMTP Gmail truyền thống (qua cổng 587 và App Password).
        """
        # Ưu tiên 1: Gửi qua Google Apps Script Web App (Không cần mật khẩu ứng dụng hay cấu hình SMTP)
        gas_url = (settings.GOOGLE_APPS_SCRIPT_URL or "").strip()
        if gas_url:
            try:
                import httpx
                response = httpx.post(
                    gas_url,
                    json={"email": to_email, "otp": otp_code},
                    follow_redirects=True,
                    timeout=15.0
                )
                if response.status_code == 200:
                    try:
                        res_json = response.json()
                        if res_json.get("status") == "ok":
                            return True, f"Mã xác nhận OTP đã được gửi thành công đến hòm thư {to_email}. Vui lòng kiểm tra hộp thư đến hoặc thư rác (Spam)."
                    except Exception:
                        return True, f"Mã xác nhận OTP đã được gửi đến hòm thư {to_email} qua Google Service."
                print(f"[GAS Error] Google Apps Script phản hồi mã: {response.status_code}")
            except Exception as e:
                print(f"[GAS Error] Không thể gửi qua Google Apps Script: {e}")

        # Ưu tiên 2: Gửi qua SMTP Gmail
        sender_email = (settings.SMTP_USERNAME or settings.SMTP_FROM_EMAIL or "").strip()
        sender_password = (settings.SMTP_PASSWORD or "").replace(" ", "").strip()

        if not sender_email or not sender_password:
            err_msg = (
                "Hệ thống chưa được cấu hình tài khoản gửi thư! "
                "Vui lòng điền GOOGLE_APPS_SCRIPT_URL hoặc SMTP_USERNAME/SMTP_PASSWORD vào file .env để gửi email thật."
            )
            print(f"[EmailService Error] {err_msg} - Mã dự phòng nếu thử nghiệm: {otp_code}")
            return False, err_msg

        import time
        print(f"\n🔥 [XÁC THỰC GMAIL] Đang gửi mã OTP [{otp_code}] về hộp thư: {to_email}...")
        t_start = time.time()

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"Mã xác nhận đăng ký tài khoản MoneyMind: {otp_code}"
            msg["From"] = f"MoneyMind <{sender_email}>"
            msg["To"] = to_email

            html_content = f"""
            <div style="font-family: Arial, 'Segoe UI', Tahoma, sans-serif; max-width: 520px; margin: 0 auto; padding: 28px; border: 1px solid #e2e8f0; border-radius: 20px; background-color: #ffffff; color: #1e293b;">
                <div style="text-align: center; margin-bottom: 24px;">
                    <div style="display: inline-block; width: 48px; height: 48px; line-height: 48px; font-size: 26px; background: linear-gradient(135deg, #0d9488, #06b6d4); color: #fff; border-radius: 16px; margin-bottom: 8px;">💰</div>
                    <h2 style="color: #0f766e; margin: 0; font-size: 22px; font-weight: 800;">MoneyMind</h2>
                    <p style="color: #64748b; font-size: 13px; margin: 4px 0 0 0;">Quản Lý Tài Chính Toàn Diện</p>
                </div>
                
                <div style="background-color: #f0fdfa; border: 1px solid #99f6e4; border-radius: 16px; padding: 24px; text-align: center;">
                    <h3 style="color: #115e59; font-size: 16px; margin: 0 0 8px 0; font-weight: 700;">Xác Nhận Đăng Ký Tài Khoản</h3>
                    <p style="font-size: 13px; color: #334155; margin: 0 0 16px 0; line-height: 1.5;">
                        Cảm ơn bạn đã đăng ký tài khoản MoneyMind. Vui lòng nhập mã OTP xác thực bên dưới để kích hoạt tài khoản của bạn:
                    </p>
                    <div style="font-size: 34px; font-weight: 800; letter-spacing: 8px; color: #0f766e; padding: 14px 24px; background: #ffffff; border-radius: 12px; border: 2px dashed #0d9488; display: inline-block; margin-bottom: 12px;">
                        {otp_code}
                    </div>
                    <p style="font-size: 12px; color: #64748b; margin: 0; line-height: 1.4;">
                        Mã xác thực có hiệu lực trong vòng <strong>10 phút</strong>.<br>
                        Vì lý do an toàn, tuyệt đối không chia sẻ mã này cho bất kỳ ai.
                    </p>
                </div>
                
                <div style="text-align: center; margin-top: 24px; padding-top: 16px; border-top: 1px solid #f1f5f9;">
                    <p style="font-size: 11px; color: #94a3b8; margin: 0;">
                        Nếu bạn không thực hiện đăng ký trên MoneyMind, vui lòng bỏ qua thư này.
                    </p>
                </div>
            </div>
            """
            part = MIMEText(html_content, "html", "utf-8")
            msg.attach(part)

            # Thử cổng 465 (SSL trực tiếp) trước vì nhanh hơn STARTTLS 587
            try:
                server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10)
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, [to_email], msg.as_string())
                server.quit()
                elapsed = time.time() - t_start
                print(f"✅ [XÁC THỰC GMAIL] Đã chuyển mã OTP [{otp_code}] đến {to_email} thành công qua SSL:465 ({elapsed:.2f}s)!\n")
                return True, f"Mã xác nhận OTP đã được gửi thành công đến hòm thư {to_email}. Vui lòng kiểm tra hộp thư đến hoặc thư rác (Spam)."
            except Exception as e_ssl:
                print(f"[SMTP 465 Notice] Thử cổng 465 gặp sự cố ({e_ssl}), đang chuyển hướng sang cổng {settings.SMTP_PORT or 587}...")
                server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT or 587, timeout=12)
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, [to_email], msg.as_string())
                server.quit()
                elapsed = time.time() - t_start
                print(f"✅ [XÁC THỰC GMAIL] Đã chuyển mã OTP [{otp_code}] đến {to_email} thành công qua TLS:{settings.SMTP_PORT} ({elapsed:.2f}s)!\n")
                return True, f"Mã xác nhận OTP đã được gửi thành công đến hòm thư {to_email}. Vui lòng kiểm tra hộp thư đến hoặc thư rác (Spam)."
        except Exception as e:
            print(f"[SMTP Error] Lỗi gửi email đến {to_email}: {e}\n")
            return False, f"Không thể gửi email đến {to_email}: {str(e)}. Vui lòng kiểm tra kết nối mạng hoặc cấu hình SMTP."

    @staticmethod
    def send_otp_email(to_email: str, otp_code: str) -> Tuple[bool, str]:
        return EmailService.send_registration_otp(to_email, otp_code)
