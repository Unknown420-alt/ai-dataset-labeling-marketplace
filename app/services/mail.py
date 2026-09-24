"""OTP email delivery. Real SMTP when configured, honest dev fallback otherwise."""

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

log = logging.getLogger("otp")


def send_otp_email(to_email: str, code: str, purpose: str) -> str:
    """Send the code. Returns 'smtp' or 'dev-log'.

    Production without SMTP configured refuses loudly instead of
    silently dropping the code.
    """
    subject = "Verify your email" if purpose == "verify" else "Your login code"
    body = (
        f"Your verification code is: {code}\n\n"
        f"It expires in 10 minutes. If you did not ask for this, ignore this email."
    )
    if settings.smtp_host and settings.smtp_user:
        msg = EmailMessage()
        msg["Subject"] = f"[Labeling Marketplace] {subject}"
        msg["From"] = settings.smtp_from or settings.smtp_user
        msg["To"] = to_email
        msg.set_content(body)
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            smtp.starttls()
            smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
        return "smtp"
    if settings.environment == "production":
        raise RuntimeError(
            "SMTP is not configured. Set SMTP_HOST/SMTP_USER/SMTP_PASSWORD to send OTP codes."
        )
    log.warning("DEV OTP for %s (%s): %s", to_email, purpose, code)
    return "dev-log"
