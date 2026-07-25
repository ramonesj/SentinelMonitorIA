"""Provider-neutral alert notification adapters."""

import asyncio
import hashlib
import hmac
import json
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Any

import httpx

from src.config.logging import logger
from src.config.settings import settings


@dataclass(frozen=True)
class NotificationResult:
    channel: str
    delivered: bool
    external_id: str | None = None
    error: str | None = None


class NotificationDispatcher:
    """Dispatch one alert through a configured channel without executing actions."""

    async def send(self, channel: str, alert: dict[str, Any]) -> NotificationResult:
        channel = channel.strip().lower()
        if channel == "log":
            logger.warning(
                "Alert notification emitted locally",
                alert_id=alert.get("id"),
                severity=alert.get("severity"),
                title=alert.get("title"),
            )
            return NotificationResult(channel=channel, delivered=True, external_id="local-log")
        if channel == "email":
            return await self._send_email(alert)
        if channel in {"webhook", "slack", "discord", "teams"}:
            return await self._send_webhook(channel, alert)
        raise RuntimeError(f"Unsupported notification channel: {channel}")

    async def _send_webhook(self, channel: str, alert: dict[str, Any]) -> NotificationResult:
        urls = {
            "webhook": settings.notification_webhook_url,
            "slack": settings.notification_slack_webhook_url,
            "discord": settings.notification_discord_webhook_url,
            "teams": settings.notification_teams_webhook_url,
        }
        url = urls.get(channel)
        if not url:
            raise RuntimeError(f"No webhook URL configured for channel {channel}")

        text = f"[{alert.get('severity', 'info').upper()}] {alert.get('title')}: {alert.get('description')}"
        if channel == "slack":
            body: dict[str, Any] = {"text": text}
        elif channel == "discord":
            body = {"content": text}
        elif channel == "teams":
            body = {"text": text}
        else:
            body = {"source": "SentinelMonitorIA", "alert": alert}

        serialized = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
        headers = {"Content-Type": "application/json"}
        if settings.notification_webhook_secret:
            signature = hmac.new(
                settings.notification_webhook_secret.encode("utf-8"),
                serialized.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            headers["X-Sentinel-Signature"] = f"sha256={signature}"

        async with httpx.AsyncClient(timeout=settings.notification_request_timeout_seconds) as client:
            response = await client.post(url, content=serialized, headers=headers)
            response.raise_for_status()
        return NotificationResult(channel=channel, delivered=True, external_id=str(response.status_code))

    async def _send_email(self, alert: dict[str, Any]) -> NotificationResult:
        if not settings.notification_email_to or not settings.smtp_host:
            raise RuntimeError("SMTP_HOST and NOTIFICATION_EMAIL_TO are required for email notifications")

        message = EmailMessage()
        message["From"] = settings.smtp_from_email or settings.notification_email_to
        message["To"] = settings.notification_email_to
        message["Subject"] = f"SentinelMonitorIA alert: {alert.get('title')}"
        message.set_content(
            f"Severity: {alert.get('severity')}\n\n"
            f"{alert.get('description')}\n\n"
            "Automated actions are disabled; review the incident before acting."
        )

        def deliver() -> None:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=settings.notification_request_timeout_seconds) as server:
                if settings.smtp_use_tls:
                    server.starttls()
                if settings.smtp_username and settings.smtp_password:
                    server.login(settings.smtp_username, settings.smtp_password)
                server.send_message(message)

        await asyncio.to_thread(deliver)
        return NotificationResult(channel="email", delivered=True, external_id=settings.notification_email_to)


notification_dispatcher = NotificationDispatcher()
