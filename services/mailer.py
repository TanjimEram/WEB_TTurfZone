"""Plain-text email through the hosting mailbox (SMTP, stdlib only; D-30).

Settings come from the MAIL_* environment variables (config.py). Port 465 uses SSL
from the start; any other port (587) upgrades with STARTTLS. Never log the password.
"""
import smtplib
import ssl
from email.message import EmailMessage

from flask import current_app


def mail_configured() -> bool:
    cfg = current_app.config
    return bool(cfg.get("MAIL_SERVER") and cfg.get("MAIL_FROM"))


def send_email(to: str, subject: str, body: str) -> None:
    """Send one email. Raises on any SMTP/network error; the caller decides what to show."""
    cfg = current_app.config
    msg = EmailMessage()
    msg["From"] = cfg["MAIL_FROM"]
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

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
