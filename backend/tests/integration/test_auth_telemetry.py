import os
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import select

from src.database.database import DatabaseContext
from src.models.organization import Agent, Organization
from src.models.telemetry import Event, LogEntry, Metric, TelemetryBatch
from src.models.user import Token
from src.services.auth import AuthenticationService


pytestmark = pytest.mark.integration

BASE_URL = os.getenv("SENTINEL_TEST_BASE_URL", "http://localhost:8000")


def unique_identity() -> tuple[str, str, str]:
    suffix = uuid4().hex[:12]
    return (
        f"operator-{suffix}",
        f"operator-{suffix}@example.com",
        f"local-org-{suffix}",
    )


async def register_user(client: httpx.AsyncClient) -> dict:
    username, email, organization_slug = unique_identity()
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": email,
            "password": "LocalSmoke!2026",
            "full_name": "Integration Operator",
            "organization_name": "Integration Organization",
            "organization_slug": organization_slug,
            "timezone": "UTC",
            "locale": "en-US",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
async def client():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as async_client:
        yield async_client


def test_api_key_hash_does_not_equal_usable_secret():
    secret = "eyJhbGciOiJIUzI1NiJ9.test.integration.secret"
    digest = AuthenticationService.hash_api_token(secret)

    assert digest != secret
    assert len(digest) == 64


async def test_register_login_refresh_and_me(client: httpx.AsyncClient):
    registered = await register_user(client)
    access_token = registered["access_token"]
    refresh_token = registered["refresh_token"]

    me_response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_response.status_code == 200, me_response.text
    assert me_response.json()["organizations"]

    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_response.status_code == 200, refresh_response.text
    assert refresh_response.json()["access_token"]
    assert refresh_response.json()["refresh_token"]


async def test_api_key_lifecycle_and_telemetry(client: httpx.AsyncClient):
    registered = await register_user(client)
    access_token = registered["access_token"]
    organization_id = registered["user"]["organizations"][0]["id"]
    access_headers = {"Authorization": f"Bearer {access_token}"}

    create_response = await client.post(
        "/api/v1/auth/api-keys",
        headers=access_headers,
        json={
            "name": "Integration telemetry key",
            "description": "Created by the local integration suite",
            "expires_in_days": 1,
            "organization_id": organization_id,
        },
    )
    assert create_response.status_code == 201, create_response.text
    api_key = create_response.json()["token"]
    token_id = None

    list_response = await client.get(
        "/api/v1/auth/api-keys",
        headers=access_headers,
    )
    assert list_response.status_code == 200, list_response.text
    listed_key = next(
        item
        for item in list_response.json()["tokens"]
        if item["name"] == "Integration telemetry key"
    )
    token_id = listed_key["id"]
    assert "token" not in listed_key

    async with DatabaseContext() as db:
        stored_result = await db.execute(
            select(Token).where(Token.id == UUID(token_id))
        )
        stored_token = stored_result.scalar_one()
        assert stored_token.token == AuthenticationService.hash_api_token(api_key)
        assert stored_token.token != api_key
        # Simulate a pre-hardening row; the first successful use must migrate it.
        stored_token.token = api_key
        await db.commit()

    telemetry_payload = {
        "metadata": {
            "agent_id": f"integration-agent-{uuid4().hex[:8]}",
            "hostname": "integration-host",
            "agent_version": "1.0.0",
            "platform": "windows",
            "architecture": "amd64",
            "tags": {"suite": "integration"},
        },
        "metrics": [
            {
                "name": "integration.metric",
                "value": 1,
                "type": "gauge",
                "labels": {"source": "pytest"},
                "unit": "count",
            }
        ],
        "logs": [],
        "events": [],
        "batch_id": f"integration-batch-{uuid4().hex}",
    }
    key_headers = {"Authorization": f"Bearer {api_key}"}

    telemetry_response = await client.post(
        "/api/v1/telemetry",
        headers=key_headers,
        json=telemetry_payload,
    )
    assert telemetry_response.status_code == 202, telemetry_response.text

    async with DatabaseContext() as db:
        migrated_result = await db.execute(
            select(Token).where(Token.id == UUID(token_id))
        )
        migrated_token = migrated_result.scalar_one()
        assert migrated_token.token == AuthenticationService.hash_api_token(api_key)

    revoke_response = await client.delete(
        f"/api/v1/auth/api-keys/{token_id}",
        headers=access_headers,
    )
    assert revoke_response.status_code == 200, revoke_response.text

    rejected_response = await client.post(
        "/api/v1/telemetry",
        headers=key_headers,
        json=telemetry_payload,
    )
    assert rejected_response.status_code == 401, rejected_response.text


async def test_refresh_replay_and_logout_revoke_jwt_sessions(client: httpx.AsyncClient):
    registered = await register_user(client)
    access_token = registered["access_token"]
    refresh_token = registered["refresh_token"]

    first_refresh = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert first_refresh.status_code == 200, first_refresh.text
    rotated = first_refresh.json()
    replay = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert replay.status_code == 401, replay.text

    logout = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {rotated['access_token']}"},
    )
    assert logout.status_code == 200, logout.text
    assert logout.json()["revoked_sessions"] >= 1

    rejected_me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {rotated['access_token']}"},
    )
    assert rejected_me.status_code == 401, rejected_me.text

    rejected_refresh = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": rotated["refresh_token"]},
    )
    assert rejected_refresh.status_code == 401, rejected_refresh.text

    # The original access token is revoked as part of the same logout session.
    rejected_original = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert rejected_original.status_code == 401, rejected_original.text


async def test_api_key_scopes_and_rotation(client: httpx.AsyncClient):
    registered = await register_user(client)
    access_headers = {"Authorization": f"Bearer {registered['access_token']}"}
    organization_id = registered["user"]["organizations"][0]["id"]

    read_only = await client.post(
        "/api/v1/auth/api-keys",
        headers=access_headers,
        json={
            "name": "Read-only key",
            "organization_id": organization_id,
            "scopes": ["telemetry:read"],
        },
    )
    assert read_only.status_code == 201, read_only.text
    read_only_key = read_only.json()["token"]
    telemetry_payload = {
        "metadata": {
            "agent_id": f"scope-agent-{uuid4().hex[:8]}",
            "hostname": "scope-host",
            "agent_version": "1.0.0",
            "platform": "windows",
            "architecture": "amd64",
            "tags": {},
        },
        "metrics": [{"name": "scope.metric", "value": 1, "type": "gauge", "labels": {}}],
        "logs": [],
        "events": [],
        "batch_id": f"scope-batch-{uuid4().hex}",
    }
    denied = await client.post(
        "/api/v1/telemetry",
        headers={"Authorization": f"Bearer {read_only_key}"},
        json=telemetry_payload,
    )
    assert denied.status_code == 403, denied.text

    writable = await client.post(
        "/api/v1/auth/api-keys",
        headers=access_headers,
        json={
            "name": "Rotating write key",
            "organization_id": organization_id,
            "scopes": ["telemetry:write"],
        },
    )
    assert writable.status_code == 201, writable.text
    writable_key = writable.json()["token"]
    listed = await client.get("/api/v1/auth/api-keys", headers=access_headers)
    token_id = next(item["id"] for item in listed.json()["tokens"] if item["name"] == "Rotating write key")

    rotated = await client.post(
        f"/api/v1/auth/api-keys/{token_id}/rotate",
        headers=access_headers,
        json={"name": "Rotated write key"},
    )
    assert rotated.status_code == 200, rotated.text
    replacement_key = rotated.json()["token"]

    old_key_response = await client.post(
        "/api/v1/telemetry",
        headers={"Authorization": f"Bearer {writable_key}"},
        json=telemetry_payload,
    )
    assert old_key_response.status_code == 401, old_key_response.text

    replacement_response = await client.post(
        "/api/v1/telemetry",
        headers={"Authorization": f"Bearer {replacement_key}"},
        json=telemetry_payload,
    )
    assert replacement_response.status_code == 202, replacement_response.text
