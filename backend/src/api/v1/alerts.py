"""Authenticated alert queries, acknowledgement, and local WebSocket updates."""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.auth import get_current_user_record
from src.config.settings import settings
from src.database.database import get_db_session
from src.models.intelligence import Alert
from src.models.user import User, UserOrganization
from src.services.auth import auth_service


router = APIRouter(prefix="/alerts", tags=["alerts"])


async def _organization_ids(db: AsyncSession, user_id: UUID) -> list[UUID]:
    result = await db.execute(select(UserOrganization.organization_id).where(UserOrganization.user_id == user_id))
    return list(result.scalars().all())


def _serialize_alert(alert: Alert) -> dict[str, Any]:
    return jsonable_encoder(
        {
            "id": alert.id,
            "organization_id": alert.organization_id,
            "analysis_id": alert.analysis_id,
            "rule_id": alert.rule_id,
            "source": alert.source,
            "title": alert.title,
            "description": alert.description,
            "severity": alert.severity,
            "status": alert.status,
            "payload": alert.payload,
            "created_at": alert.created_at,
            "updated_at": alert.updated_at,
            "acknowledged_at": alert.acknowledged_at,
            "resolved_at": alert.resolved_at,
        }
    )


@router.get("", summary="List organization alerts")
async def list_alerts(
    limit: int = Query(default=50, ge=1, le=100),
    user: User = Depends(get_current_user_record),
    db: AsyncSession = Depends(get_db_session),
):
    """List recent alerts visible to the authenticated user's organizations."""
    organization_ids = await _organization_ids(db, user.id)
    if not organization_ids:
        return {"status": "success", "alerts": []}
    result = await db.execute(
        select(Alert)
        .where(Alert.organization_id.in_(organization_ids))
        .order_by(Alert.created_at.desc())
        .limit(limit)
    )
    return {"status": "success", "alerts": [_serialize_alert(alert) for alert in result.scalars().all()]}


@router.post("/{alert_id}/acknowledge", summary="Acknowledge an alert")
async def acknowledge_alert(
    alert_id: UUID,
    user: User = Depends(get_current_user_record),
    db: AsyncSession = Depends(get_db_session),
):
    """Acknowledge an alert without executing an operational action."""
    organization_ids = await _organization_ids(db, user.id)
    result = await db.execute(
        select(Alert).where(
            (Alert.id == alert_id) & Alert.organization_id.in_(organization_ids)
        )
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    if alert.status == "open":
        alert.status = "acknowledged"
        alert.acknowledged_at = datetime.utcnow()
        await db.commit()
    return {"status": "success", "alert": _serialize_alert(alert)}


WEBSOCKET_AUTH_TIMEOUT_SECONDS = 10


@router.websocket("/ws")
async def alerts_websocket(
    websocket: WebSocket,
    db: AsyncSession = Depends(get_db_session),
):
    """Poll organization alerts after an in-band WebSocket authentication.

    The client sends ``{"type": "authenticate", "access_token": "..."}``
    as its first message after opening the socket. Keeping the token in the
    WebSocket message prevents Uvicorn access logs, browser history, proxies,
    and metrics from recording it as part of the request URL.
    """
    await websocket.accept()
    try:
        handshake = await asyncio.wait_for(
            websocket.receive_json(),
            timeout=WEBSOCKET_AUTH_TIMEOUT_SECONDS,
        )
        if not isinstance(handshake, dict) or handshake.get("type") != "authenticate":
            raise ValueError("websocket authentication required")

        access_token = handshake.get("access_token")
        if not isinstance(access_token, str) or len(access_token) < 20:
            raise ValueError("access token required")

        payload = auth_service.decode_token(access_token)
        if payload.get("type") != "access":
            raise ValueError("access token required")
        await auth_service.ensure_jwt_session_active(db, payload, "access")
        user_id = UUID(payload["sub"])
        organization_ids = await _organization_ids(db, user_id)
    except Exception:
        try:
            await websocket.close(code=1008)
        except RuntimeError:
            pass
        return

    last_seen = datetime.now(timezone.utc) - timedelta(seconds=2)
    try:
        while True:
            result = await db.execute(
                select(Alert)
                .where(
                    Alert.organization_id.in_(organization_ids),
                    Alert.created_at > last_seen,
                )
                .order_by(Alert.created_at.asc())
            )
            alerts = result.scalars().all()
            for alert in alerts:
                await websocket.send_json(_serialize_alert(alert))
                if alert.created_at and alert.created_at > last_seen:
                    last_seen = alert.created_at
            await asyncio.sleep(settings.alert_websocket_poll_seconds)
    except WebSocketDisconnect:
        return
