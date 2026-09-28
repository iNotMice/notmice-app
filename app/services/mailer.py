"""Outbound account mail. The message body carries the one-time link, never a stored secret."""

from __future__ import annotations

import asyncio
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Protocol

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class OutboundMail:
    """One message. ``to`` is the recipient; callers must not log it."""

    to: str
    subject: str
    body: str


class Mailer(Protocol):
    """Sends one account message."""

    async def send(self, message: OutboundMail) -> None:
        """Deliver ``message``. Implementations must not raise into the account response."""


class CapturingMailer:
    """Test double that keeps messages in memory."""

    def __init__(self) -> None:
        self.sent: list[OutboundMail] = []

    async def send(self, message: OutboundMail) -> None:
        """Record ``message``."""
        self.sent.append(message)


class DevLoggingMailer:
    """Development sink. The link is logged only when ``reveal_link`` is true."""

    def __init__(self, *, reveal_link: bool) -> None:
        self._reveal_link = reveal_link

    async def send(self, message: OutboundMail) -> None:
        """Log that a message was produced. Production logs omit the link and the address."""
        if self._reveal_link:
            logger.info("auth_mail_dev", subject=message.subject, body=message.body)
            return
        logger.error("auth_mail_unconfigured", subject=message.subject)


class SmtpMailer:
    """SMTP delivery. Retries cover a blip; the account service still hides the outcome."""

    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str,
        password: str,
        sender: str,
        use_tls: bool,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._sender = sender
        self._use_tls = use_tls

    async def send(self, message: OutboundMail) -> None:
        """Send ``message`` on a worker thread."""
        await asyncio.to_thread(self._send_sync, message)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.2, max=2), reraise=True)
    def _send_sync(self, message: OutboundMail) -> None:
        """Open one SMTP session and send ``message``."""
        email = EmailMessage()
        email["From"] = self._sender
        email["To"] = message.to
        email["Subject"] = message.subject
        email.set_content(message.body)
        with smtplib.SMTP(self._host, self._port, timeout=20) as client:
            if self._use_tls:
                client.starttls()
            if self._username:
                client.login(self._username, self._password)
            client.send_message(email)
