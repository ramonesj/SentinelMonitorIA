"""Authenticated, organization-scoped conversational API."""

from typing import Any, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.auth import get_current_user_record
from src.config.settings import settings
from src.database.database import get_db_session
from src.models.intelligence import Alert
from src.models.user import User, UserOrganization
from src.services.chat import build_chat_provider


router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequestSchema(BaseModel):
    """Provider-neutral chat request accepted by the local and future AWS flows."""

    message: str = Field(..., min_length=1, max_length=2000)
    conversation_id: Optional[str] = Field(default=None, min_length=1, max_length=128)
    context: dict[str, Any] = Field(default_factory=dict)


async def _organization_ids(db: AsyncSession, user_id: UUID) -> list[UUID]:
    result = await db.execute(select(UserOrganization.organization_id).where(UserOrganization.user_id == user_id))
    return list(result.scalars().all())


def _serialize_alert_context(alert: Alert) -> dict[str, Any]:
    payload = alert.payload if isinstance(alert.payload, dict) else {}
    raw_findings = payload.get("findings", [])
    findings = []
    for finding in raw_findings[:3] if isinstance(raw_findings, list) else []:
        if not isinstance(finding, dict):
            continue
        evidence = finding.get("evidence", {}) if isinstance(finding.get("evidence"), dict) else {}
        findings.append(
            {
                "rule_id": str(finding.get("rule_id") or ""),
                "title": str(finding.get("title") or "Signal"),
                "description": str(finding.get("description") or ""),
                "evidence": {
                    key: evidence[key]
                    for key in ("metric", "value", "unit", "service", "component", "source")
                    if key in evidence
                },
            }
        )
    recommendations = payload.get("recommendations", [])
    if not isinstance(recommendations, list):
        recommendations = []

    return jsonable_encoder(
        {
            "id": alert.id,
            "title": alert.title,
            "description": alert.description,
            "severity": alert.severity,
            "status": alert.status,
            "rule_id": alert.rule_id,
            "source": alert.source,
            "created_at": alert.created_at,
            "findings": findings,
            "recommendations": [str(item) for item in recommendations[:4]],
        }
    )


@router.post("", summary="Ask the organization-scoped chatbot")
async def chat(
    request: ChatRequestSchema,
    user: User = Depends(get_current_user_record),
    db: AsyncSession = Depends(get_db_session),
):
    """Answer from recent organization-scoped alerts without executing actions."""
    organization_ids = await _organization_ids(db, user.id)
    alerts: list[Alert] = []
    if organization_ids:
        result = await db.execute(
            select(Alert)
            .where(Alert.organization_id.in_(organization_ids))
            .order_by(Alert.created_at.desc())
            .limit(settings.chat_context_alert_limit)
        )
        alerts = list(result.scalars().all())

    conversation_id = request.conversation_id or str(uuid4())
    context = {
        "organization_count": len(organization_ids),
        "alerts": [_serialize_alert_context(alert) for alert in alerts],
        "request_context": request.context,
        "conversation_id": conversation_id,
    }
    provider = build_chat_provider()
    result = await provider.respond(request.message.strip(), context)
    open_alerts = sum(1 for alert in alerts if alert.status == "open")
    priority_alerts = sum(
        1 for alert in alerts if alert.status == "open" and alert.severity in {"critical", "high"}
    )

    return {
        "status": "success",
        "conversation_id": conversation_id,
        "provider": provider.name,
        "message": result.message,
        "suggestions": result.suggestions,
        "sources": result.sources,
        "actions": result.actions,
        "context_summary": {
            "alerts_considered": len(alerts),
            "open_alerts": open_alerts,
            "high_priority_open_alerts": priority_alerts,
            "actions_enabled": False,
        },
    }
