"""Plain-text email (stdlib only, no new dependency).

Two transports, picked by configuration:
- **Gmail API over HTTPS** (CR-9): when GMAIL_REFRESH_TOKEN is set. Production uses this,
  because the host blocks outgoing SMTP ports. Sent as MAIL_FROM (tturfzone@gmail.com).
- **SMTP** (D-30): MAIL_SERVER etc. Port 465 uses SSL from the start; any other port
  upgrades with STARTTLS. Kept for hosts where SMTP works.
Never log passwords or tokens.
"""
import smtplib
import ssl
from email.message import EmailMessage

from flask import current_app

from services import google


def mail_configured() -> bool:
    cfg = current_app.config
    if not cfg.get("MAIL_FROM"):
        return False
    return bool(cfg.get("GMAIL_REFRESH_TOKEN") or cfg.get("MAIL_SERVER"))


def send_email(to: str, subject: str, body: str) -> None:
    """Send one email. Raises on any failure; the caller decides what to show."""
    cfg = current_app.config
    msg = EmailMessage()
    msg["From"] = cfg["MAIL_FROM"]
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    if cfg.get("GMAIL_REFRESH_TOKEN"):
        google.gmail_send(msg.as_bytes())
        return

    port = int(cfg.get("MAIL_PORT") or 465)
    context = ssl.create_default_context()
    if port == 465:
        server = smtplib.SMTP_SSL(cfg["MAIL_SERVER"], port, context=context, timeout=15)
    else:
        server = smtplib.SMTP(cfg["MAIL_SERVER"], port, timeout=15)
        server.starttls(context=context)
    with server:
        if cfg.get("MAIL_USERNAME"):
            server.login(cfg["MAIL_USERNAME"], cfg.get("MAIL_PASSWORD", ""))
        server.send_message(msg)
