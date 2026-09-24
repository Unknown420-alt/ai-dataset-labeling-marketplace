"""Send a test email with the configured SMTP settings.

Usage:  python scripts/test_mail.py you@example.com
Reads SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASSWORD / SMTP_FROM from .env.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.services.mail import send_otp_email


def main() -> None:
    to = sys.argv[1] if len(sys.argv) > 1 else None
    if not to:
        print("Usage: python scripts/test_mail.py you@example.com")
        raise SystemExit(2)
    if not (settings.smtp_host and settings.smtp_user):
        print("SMTP not configured. Set SMTP_HOST/SMTP_USER/SMTP_PASSWORD in .env first.")
        raise SystemExit(1)
    via = send_otp_email(to, "123456", "verify")
    print(f"Test email sent via {via} to {to}. Check inbox (and spam).")


if __name__ == "__main__":
    main()
