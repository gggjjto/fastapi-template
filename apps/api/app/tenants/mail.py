from __future__ import annotations

import smtplib
from email.message import EmailMessage

import structlog

from app.core.config import Settings

logger = structlog.get_logger(__name__)


def send_invitation(settings: Settings, *, email: str, tenant_name: str, token: str) -> None:
    url = f"{settings.admin_url.rstrip('/')}/invitations/accept?token={token}"
    if settings.mail_backend == "console":
        logger.info("tenant.invitation.console", email=email, tenant=tenant_name, url=url)
        return

    message = EmailMessage()
    message["Subject"] = f"Invitation to join {tenant_name}"
    message["From"] = settings.mail_from
    message["To"] = email
    message.set_content(f"You were invited to join {tenant_name}.\n\nAccept: {url}\n")
    with smtplib.SMTP(settings.mail_host, settings.mail_port, timeout=10) as smtp:
        if settings.mail_starttls:
            smtp.starttls()
        if settings.mail_username:
            smtp.login(settings.mail_username, settings.mail_password or "")
        smtp.send_message(message)
