"""Provider-neutral chat responses for local operation and future AWS adapters."""

import unicodedata
from dataclasses import dataclass, field
from typing import Any, Protocol

from src.config.logging import logger
from src.config.settings import settings


@dataclass(frozen=True)
class ChatResult:
    """Normalized response returned by any chat provider."""

    message: str
    suggestions: list[str] = field(default_factory=list)
    sources: list[dict[str, Any]] = field(default_factory=list)
    actions: list[dict[str, Any]] = field(default_factory=list)


class ChatProvider(Protocol):
    """Stable interface implemented by local and future cloud providers."""

    name: str

    async def respond(self, message: str, context: dict[str, Any]) -> ChatResult:
        """Return a grounded response for the supplied organization context."""


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.lower())
    return "".join(character for character in normalized if not unicodedata.combining(character))


def _alert_source(alert: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "alert",
        "id": str(alert.get("id")),
        "title": str(alert.get("title") or "Operational alert"),
        "severity": str(alert.get("severity") or "info"),
        "status": str(alert.get("status") or "open"),
    }


class RulesChatProvider:
    """No-network provider that answers from organization-scoped alert context."""

    name = "rules"

    async def respond(self, message: str, context: dict[str, Any]) -> ChatResult:
        alerts = [alert for alert in context.get("alerts", []) if isinstance(alert, dict)]
        open_alerts = [alert for alert in alerts if alert.get("status") == "open"]
        priority_alerts = [
            alert for alert in open_alerts if str(alert.get("severity", "info")).lower() in {"critical", "high"}
        ]
        normalized_message = _normalize(message)
        sources = [_alert_source(alert) for alert in alerts[:5]]

        if any(term in normalized_message for term in ("ayuda", "help", "puedes hacer", "que haces")):
            response = (
                "Puedo consultar el contexto operativo disponible para tu organización: "
                "alertas abiertas, severidades, estados y últimos hallazgos. "
                "Las acciones automáticas están deshabilitadas."
            )
        elif any(term in normalized_message for term in ("critica", "critical", "alta", "high", "prioridad")):
            if priority_alerts:
                response = (
                    f"Hay {len(priority_alerts)} alerta(s) abierta(s) de prioridad alta o crítica.\n"
                    + "\n".join(self._format_alert(alert) for alert in priority_alerts[:5])
                )
            else:
                response = "No hay alertas abiertas de prioridad alta o crítica en el contexto reciente."
        elif any(term in normalized_message for term in ("alerta", "alertas", "alert", "incidente", "incidents")):
            if open_alerts:
                response = (
                    f"Hay {len(open_alerts)} alerta(s) abierta(s) de {len(alerts)} registro(s) recientes.\n"
                    + "\n".join(self._format_alert(alert) for alert in open_alerts[:5])
                )
            else:
                response = "No hay alertas abiertas en el contexto reciente."
        elif any(term in normalized_message for term in ("estado", "salud", "health", "status", "resumen", "summary")):
            response = (
                f"Resumen operativo: {len(open_alerts)} alerta(s) abierta(s), "
                f"{len(priority_alerts)} de alta prioridad y {len(alerts)} registro(s) de alerta recientes. "
                "El chatbot local usa reglas y no realiza acciones automáticas."
            )
        elif any(term in normalized_message for term in ("ultima", "ultimas", "latest", "reciente", "recent")):
            if alerts:
                response = "Últimas señales registradas:\n" + "\n".join(
                    self._format_alert(alert) for alert in alerts[:5]
                )
            else:
                response = "No hay señales de alerta recientes disponibles."
        else:
            response = (
                f"Puedo ayudarte con el estado operativo. Actualmente hay {len(open_alerts)} alerta(s) abierta(s) "
                f"y {len(priority_alerts)} de alta prioridad. Pregunta por alertas, alertas críticas, estado o ayuda."
            )

        return ChatResult(
            message=response,
            suggestions=[
                "¿Cuántas alertas abiertas hay?",
                "Resume las alertas críticas",
                "¿Qué puedes hacer?",
            ],
            sources=sources,
            actions=[],
        )

    @staticmethod
    def _format_alert(alert: dict[str, Any]) -> str:
        title = str(alert.get("title") or "Operational alert").strip()
        severity = str(alert.get("severity") or "info").lower()
        status = str(alert.get("status") or "open").lower()
        description = str(alert.get("description") or "").strip().replace("\n", " ")
        if len(description) > 140:
            description = f"{description[:137]}..."
        suffix = f" — {description}" if description else ""
        return f"- {title} [{severity}, {status}]{suffix}"


def build_chat_provider() -> ChatProvider:
    """Build the configured provider without making a network call.

    The local rules provider is intentionally the only active implementation for now.
    Lex + Bedrock can implement the same interface later without changing the API or UI.
    """
    requested_provider = settings.chat_provider.strip().lower()
    if requested_provider != "rules":
        logger.warning(f"CHAT_PROVIDER={requested_provider} is not active in the local build; using rules provider")
    return RulesChatProvider()
