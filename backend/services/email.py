"""Email delivery abstraction.

Development uses the console provider (links are logged, never sent). Configure
``EMAIL_PROVIDER=smtp`` with SMTP_* variables for real delivery.
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from functools import lru_cache

from backend.core.config import get_settings

logger = logging.getLogger("vwap_sentinel.email")


class EmailService:
    def send(self, to: str, subject: str, body: str) -> None:  # pragma: no cover
        raise NotImplementedError


class ConsoleEmailService(EmailService):
    def send(self, to: str, subject: str, body: str) -> None:
        logger.info("EMAIL (console) to=%s subject=%s\n%s", to, subject, body)


class SmtpEmailService(EmailService):
    def __init__(self) -> None:
        settings = get_settings()
        self.host = settings.smtp_host
        self.port = settings.smtp_port
        self.username = settings.smtp_username
        self.password = settings.smtp_password
        self.sender = settings.email_from

    def send(self, to: str, subject: str, body: str) -> None:
        message = EmailMessage()
        message["From"] = self.sender
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)
        with smtplib.SMTP(self.host, self.port, timeout=15) as connection:
            connection.starttls()
            if self.username:
                connection.login(self.username, self.password)
            connection.send_message(message)


@lru_cache(maxsize=1)
def get_email_service() -> EmailService:
    settings = get_settings()
    if settings.email_provider.strip().lower() == "smtp" and settings.smtp_host:
        return SmtpEmailService()
    return ConsoleEmailService()


def _link(path: str, token: str) -> str:
    base = get_settings().app_base_url.rstrip("/")
    return f"{base}{path}?token={token}"


def send_verification_email(to: str, full_name: str, token: str) -> None:
    link = _link("/verify-email", token)
    get_email_service().send(
        to,
        "Verify your VWAP Sentinel account",
        f"Hi {full_name},\n\nVerify your email address:\n{link}\n\n"
        "The link expires in 24 hours.",
    )


def send_password_reset_email(to: str, full_name: str, token: str) -> None:
    link = _link("/reset-password", token)
    get_email_service().send(
        to,
        "Reset your VWAP Sentinel password",
        f"Hi {full_name},\n\nReset your password:\n{link}\n\n"
        "The link expires in 30 minutes. Ignore this email if you did not "
        "request a reset.",
    )
