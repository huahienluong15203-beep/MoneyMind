# -*- coding: utf-8 -*-
import smtplib
import random
import time
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
    def _send_via_smtp(to_email: str, subject: str, html_content: str, otp_code: str, action_title: str) -> Tuple[bool, str]:
        sender_email = (settings.SMTP_USERNAME or settings.SMTP_FROM_EMAIL or "").strip()
        sender_password = (settings.SMTP_PASSWORD or "").replace(" ", "").strip()

        if not sender_email or not sender_password:
            err_msg = (
                "Hệ thống chưa được cấu hình tài khoản gửi thư! "
                "Vui lòng điền SMTP_USERNAME/SMTP_PASSWORD vào file .env để gửi email thật."
            )
            print(f"[EmailService Error] {err_msg} - Mã dự phòng nếu thử nghiệm: {otp_code}")
            return False, err_msg

        try:
            print(f"\n📧 [{action_title.upper()}] Đang gửi mã OTP [{otp_code}] về hộp thư: {to_email}...")
        except Exception:
            print(f"\n[EMAIL] Dang gui ma OTP [{otp_code}] ve hop thu: {to_email}...")
        t_start = time.time()

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"MoneyMind <{sender_email}>"
        msg["To"] = to_email
        msg.attach(MIMEText(html_content, "html", "utf-8"))
        msg_str = msg.as_string()

        # Tối ưu: Ưu tiên cổng theo cấu hình (mặc định 587 hoặc 465)
        # Sử dụng local_hostname='localhost' để loại bỏ hoàn toàn độ trễ 12s reverse DNS trên Windows
        configured_port = int(settings.SMTP_PORT or 587)
        ports_to_try = [465, 587] if configured_port == 465 else [587, 465]

        last_error = None
        for port in ports_to_try:
            try:
                if port == 465:
                    server = smtplib.SMTP_SSL("smtp.gmail.com", 465, local_hostname="localhost", timeout=7)
                    server.login(sender_email, sender_password)
                    server.sendmail(sender_email, [to_email], msg_str)
                    server.quit()
                else:
                    server = smtplib.SMTP(settings.SMTP_SERVER or "smtp.gmail.com", 587, local_hostname="localhost", timeout=7)
                    server.ehlo("localhost")
                    server.starttls()
                    server.ehlo("localhost")
                    server.login(sender_email, sender_password)
                    server.sendmail(sender_email, [to_email], msg_str)
                    server.quit()

                elapsed = time.time() - t_start
                try:
                    print(f"✅ [{action_title.upper()}] Đã chuyển mã OTP [{otp_code}] đến {to_email} thành công qua Port:{port} ({elapsed:.2f}s)!\n")
                except Exception:
                    print(f"[EMAIL SUCCESS] Da gui ma OTP [{otp_code}] den {to_email} qua Port:{port} ({elapsed:.2f}s)!\n")
                return True, f"Mã xác nhận OTP đã được gửi thành công đến hòm thư {to_email}. Vui lòng kiểm tra hộp thư đến hoặc thư rác (Spam)."
            except Exception as e_port:
                last_error = e_port
                print(f"[SMTP Port {port} Notice] Cổng {port} gặp sự cố ({e_port}), đang thử cổng dự phòng...")

        elapsed = time.time() - t_start
        print(f"[SMTP Error] Lỗi gửi email đến {to_email} sau {elapsed:.2f}s: {last_error}\n")
        return False, f"Không thể gửi email đến {to_email}: {str(last_error)}. Vui lòng kiểm tra kết nối mạng hoặc cấu hình SMTP."

    @staticmethod
    def send_registration_otp(to_email: str, otp_code: str) -> Tuple[bool, str]:
        """
        Gửi mã OTP xác nhận đăng ký tài khoản về hòm thư Gmail của người dùng.
        """
        gas_url = (settings.GOOGLE_APPS_SCRIPT_URL or "").strip()
        if gas_url:
            try:
                import httpx
                response = httpx.post(
                    gas_url,
                    json={"email": to_email, "otp": otp_code},
                    follow_redirects=True,
                    timeout=6.0
                )
                if response.status_code == 200:
                    try:
                        res_json = response.json()
                        if res_json.get("status") == "ok":
                            return True, f"Mã xác nhận OTP đã được gửi thành công đến hòm thư {to_email}. Vui lòng kiểm tra hộp thư đến hoặc thư rác (Spam)."
                    except Exception:
                        return True, f"Mã xác nhận OTP đã được gửi đến hòm thư {to_email} qua Google Service."
            except Exception as e:
                print(f"[GAS Error] Không thể gửi qua Google Apps Script: {e}")

        subject = f"Mã xác nhận đăng ký tài khoản MoneyMind: {otp_code}"
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
        return EmailService._send_via_smtp(to_email, subject, html_content, otp_code, "Xác Thực Đăng Ký")

    @staticmethod
    def send_password_reset_otp(to_email: str, otp_code: str) -> Tuple[bool, str]:
        """
        Gửi mã OTP xác nhận đặt lại mật khẩu về hòm thư Gmail của người dùng.
        """
        gas_url = (settings.GOOGLE_APPS_SCRIPT_URL or "").strip()
        if gas_url:
            try:
                import httpx
                response = httpx.post(
                    gas_url,
                    json={"email": to_email, "otp": otp_code, "action": "reset_password"},
                    follow_redirects=True,
                    timeout=6.0
                )
                if response.status_code == 200:
                    try:
                        res_json = response.json()
                        if res_json.get("status") == "ok":
                            return True, f"Mã đặt lại mật khẩu OTP đã được gửi thành công đến hòm thư {to_email}."
                    except Exception:
                        return True, f"Mã đặt lại mật khẩu OTP đã được gửi đến hòm thư {to_email} qua Google Service."
            except Exception as e:
                print(f"[GAS Error] Không thể gửi qua Google Apps Script: {e}")

        subject = f"Mã xác nhận đặt lại mật khẩu MoneyMind: {otp_code}"
        html_content = f"""
        <div style="font-family: Arial, 'Segoe UI', Tahoma, sans-serif; max-width: 520px; margin: 0 auto; padding: 28px; border: 1px solid #e2e8f0; border-radius: 20px; background-color: #ffffff; color: #1e293b;">
            <div style="text-align: center; margin-bottom: 24px;">
                <div style="display: inline-block; width: 48px; height: 48px; line-height: 48px; font-size: 26px; background: linear-gradient(135deg, #0d9488, #06b6d4); color: #fff; border-radius: 16px; margin-bottom: 8px;">🔐</div>
                <h2 style="color: #0f766e; margin: 0; font-size: 22px; font-weight: 800;">MoneyMind</h2>
                <p style="color: #64748b; font-size: 13px; margin: 4px 0 0 0;">Quản Lý Tài Chính Toàn Diện</p>
            </div>
            
            <div style="background-color: #f0fdfa; border: 1px solid #99f6e4; border-radius: 16px; padding: 24px; text-align: center;">
                <h3 style="color: #115e59; font-size: 16px; margin: 0 0 8px 0; font-weight: 700;">Yêu Cầu Đặt Lại Mật Khẩu</h3>
                <p style="font-size: 13px; color: #334155; margin: 0 0 16px 0; line-height: 1.5;">
                    Bạn (hoặc ai đó) vừa yêu cầu đặt lại mật khẩu cho tài khoản MoneyMind liên kết với email này.<br>
                    Vui lòng nhập mã OTP xác thực bên dưới để thiết lập mật khẩu mới:
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
                    Nếu bạn không yêu cầu đặt lại mật khẩu, vui lòng bỏ qua thư này. Tài khoản của bạn vẫn an toàn.
                </p>
            </div>
        </div>
        """
        return EmailService._send_via_smtp(to_email, subject, html_content, otp_code, "Đặt Lại Mật Khẩu")

    @staticmethod
    def send_otp_email(to_email: str, otp_code: str) -> Tuple[bool, str]:
        return EmailService.send_registration_otp(to_email, otp_code)
