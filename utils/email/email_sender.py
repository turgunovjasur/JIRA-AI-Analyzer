"""
SMTP orqali email yuborish.

Env vars:
  SMTP_HOST        — majburiy (smtp.gmail.com, smtp.yandex.ru, ...)
  SMTP_PORT        — default 587
  SMTP_USER        — majburiy
  SMTP_PASS        — majburiy
  SMTP_FROM_EMAIL  — default SMTP_USER
  SMTP_FROM_NAME   — default "QA Assistant"
  APP_BASE_URL     — reset link uchun, default http://localhost:3000
"""
from __future__ import annotations

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from core.logger import get_logger

log = get_logger("email_sender")


def _cfg(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


def is_email_configured() -> bool:
    return bool(_cfg("SMTP_HOST") and _cfg("SMTP_USER") and _cfg("SMTP_PASS"))


def send_email(to_email: str, subject: str, html_body: str, text_body: str = "") -> bool:
    host = _cfg("SMTP_HOST")
    port = int(_cfg("SMTP_PORT", "587"))
    user = _cfg("SMTP_USER")
    password = _cfg("SMTP_PASS")
    from_email = _cfg("SMTP_FROM_EMAIL") or user
    from_name = _cfg("SMTP_FROM_NAME", "QA Assistant")

    if not (host and user and password):
        log.warning(f"Email yuborilmadi ({to_email}): SMTP sozlanmagan")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = to_email

    if text_body:
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(host, port, timeout=15) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(user, password)
            smtp.sendmail(from_email, [to_email], msg.as_bytes())
        log.info(f"Email yuborildi: {to_email} | {subject}")
        return True
    except Exception as exc:
        log.error(f"Email yuborishda xato ({to_email}): {exc}")
        return False


def send_password_reset_email(to_email: str, username: str, reset_token: str) -> bool:
    base_url = _cfg("APP_BASE_URL", "http://localhost:3000").rstrip("/")
    reset_url = f"{base_url}/reset-password?token={reset_token}"
    subject = "Parolni tiklash — QA Assistant"

    html_body = f"""
<!DOCTYPE html>
<html lang="uz">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:Arial,sans-serif">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;padding:40px 0">
    <tr><td align="center">
      <table width="520" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08)">
        <tr>
          <td style="background:#1a1a2e;padding:28px 40px">
            <div style="color:#fff;font-size:20px;font-weight:700">QA Assistant</div>
            <div style="color:#a0a0b8;font-size:13px;margin-top:4px">Parolni tiklash</div>
          </td>
        </tr>
        <tr>
          <td style="padding:36px 40px">
            <p style="margin:0 0 16px;font-size:15px;color:#333">Salom, <strong>{username}</strong>!</p>
            <p style="margin:0 0 24px;font-size:14px;color:#555;line-height:1.6">
              Parolni tiklash so'rovi keldi. Quyidagi tugmani bosib yangi parol o'rnating.
            </p>
            <table cellpadding="0" cellspacing="0"><tr><td>
              <a href="{reset_url}"
                 style="display:inline-block;padding:14px 32px;background:#4f46e5;color:#fff;
                        text-decoration:none;border-radius:8px;font-size:14px;font-weight:600">
                Parolni tiklash
              </a>
            </td></tr></table>
            <p style="margin:24px 0 0;font-size:12px;color:#999;line-height:1.6">
              Havola 30 daqiqa amal qiladi.<br>
              Agar siz so'rov yubormagan bo'lsangiz, bu xabarni e'tiborsiz qoldiring.
            </p>
          </td>
        </tr>
        <tr>
          <td style="background:#f8f8f8;padding:20px 40px;border-top:1px solid #eee">
            <p style="margin:0;font-size:12px;color:#aaa">
              © 2026 QA Assistant Platform — avtomatik xabar, javob qilmang.
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""
    text_body = (
        f"Salom, {username}!\n\n"
        f"Parolni tiklash uchun quyidagi havolaga o'ting:\n{reset_url}\n\n"
        "Havola 30 daqiqa amal qiladi.\n"
        "Agar siz so'rov yubormagan bo'lsangiz, bu xabarni e'tiborsiz qoldiring."
    )
    return send_email(to_email, subject, html_body, text_body)
