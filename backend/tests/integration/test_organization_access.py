import asyncio
import os
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import select

from src.database.database import DatabaseContext, db_manager
from src.models import telemetry  # noqa: F401
from src.models.organization import OrganizationInvitation
from src.models.user import User
from src.services.organizations import hash_invitation_token


pytestmark = pytest.mark.integration

BASE_URL = os.getenv("SENTINEL_TEST_BASE_URL", "http://localhost:8000")


@pytest.fixture(scope="module")
def event_loop():
    """Keep the shared SQLAlchemy async engine on one pytest event loop."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module", autouse=True)
async def reset_database_engine():
    """Dispose the shared engine created by other integration modules."""
    await db_manager.close()
    yield
    await db_manager.close()


@pytest.fixture
async def client():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as async_client:
        yield async_client


async def register_user(client: httpx.AsyncClient, label: str) -> dict:
    suffix = uuid4().hex[:12]
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "username": f"{label}-{suffix}",
            "email": f"{label}-{suffix}@example.com",
            "password": "RBACSmoke!2026",
            "full_name": f"{label.title()} Integration User",
            "organization_name": f"{label.title()} Organization",
            "organization_slug": f"{label}-{suffix}",
            "timezone": "UTC",
            "locale": "en-US",
        },
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    return {
        "session": payload,
        "email": f"{label}-{suffix}@example.com",
        "organization_id": payload["user"]["organizations"][0]["id"],
    }


def auth_headers(user: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {user['session']['access_token']}"}


async def test_organization_rbac_and_isolation(client: httpx.AsyncClient):
    owner = await register_user(client, "rbac-owner")
    viewer = await register_user(client, "rbac-viewer")
    outsider = await register_user(client, "rbac-outsider")
    organization_id = owner["organization_id"]
    owner_headers = auth_headers(owner)
    viewer_headers = auth_headers(viewer)
    outsider_headers = auth_headers(outsider)

    added = await client.post(
        f"/api/v1/organizations/{organization_id}/members",
        headers=owner_headers,
        json={"email": viewer["email"], "role": "viewer"},
    )
    assert added.status_code == 201, added.text
    member_id = added.json()["id"]

    listed = await client.get(
        f"/api/v1/organizations/{organization_id}/members",
        headers=viewer_headers,
    )
    assert listed.status_code == 200, listed.text
    assert {member["email"] for member in listed.json()} == {
        owner["email"],
        viewer["email"],
    }

    viewer_write = await client.post(
        f"/api/v1/organizations/{organization_id}/members",
        headers=viewer_headers,
        json={"email": outsider["email"], "role": "guest"},
    )
    assert viewer_write.status_code == 403, viewer_write.text

    viewer_key = await client.post(
        "/api/v1/auth/api-keys",
        headers=viewer_headers,
        json={
            "name": "Viewer organization key",
            "organization_id": organization_id,
        },
    )
    assert viewer_key.status_code == 403, viewer_key.text

    isolated_read = await client.get(
        f"/api/v1/organizations/{organization_id}/members",
        headers=outsider_headers,
    )
    assert isolated_read.status_code == 403, isolated_read.text

    removed = await client.delete(
        f"/api/v1/organizations/{organization_id}/members/{member_id}",
        headers=owner_headers,
    )
    assert removed.status_code == 204, removed.text


async def test_invitation_hash_email_match_and_one_time_acceptance(client: httpx.AsyncClient):
    owner = await register_user(client, "invite-owner")
    invitee = await register_user(client, "invitee")
    wrong_user = await register_user(client, "wrong-user")
    organization_id = owner["organization_id"]
    owner_headers = auth_headers(owner)
    invitee_headers = auth_headers(invitee)
    wrong_headers = auth_headers(wrong_user)

    created = await client.post(
        f"/api/v1/organizations/{organization_id}/invitations",
        headers=owner_headers,
        json={"email": invitee["email"], "role": "viewer", "expires_in_days": 7},
    )
    assert created.status_code == 201, created.text
    invitation = created.json()
    raw_token = invitation["token"]
    assert raw_token

    listed = await client.get(
        f"/api/v1/organizations/{organization_id}/invitations",
        headers=owner_headers,
    )
    assert listed.status_code == 200, listed.text
    listed_invitation = next(item for item in listed.json() if item["id"] == invitation["id"])
    assert listed_invitation.get("token") is None

    async with DatabaseContext() as db:
        stored_result = await db.execute(
            select(OrganizationInvitation).where(
                OrganizationInvitation.id == UUID(invitation["id"])
            )
        )
        stored = stored_result.scalar_one()
        assert stored.token_hash == hash_invitation_token(raw_token)
        assert stored.token_hash != raw_token
        assert len(stored.token_hash) == 64

    wrong_accept = await client.post(
        "/api/v1/auth/invitations/accept",
        headers=wrong_headers,
        json={"token": raw_token},
    )
    assert wrong_accept.status_code == 403, wrong_accept.text

    accepted = await client.post(
        "/api/v1/auth/invitations/accept",
        headers=invitee_headers,
        json={"token": raw_token},
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["organization_id"] == organization_id
    assert accepted.json()["role"] == "viewer"

    me = await client.get("/api/v1/auth/me", headers=invitee_headers)
    assert me.status_code == 200, me.text
    membership = next(item for item in me.json()["organizations"] if item["id"] == organization_id)
    assert membership["role"] == "viewer"

    replay = await client.post(
        "/api/v1/auth/invitations/accept",
        headers=invitee_headers,
        json={"token": raw_token},
    )
    assert replay.status_code == 409, replay.text


async def test_invitation_duplicate_revocation_and_expiration(client: httpx.AsyncClient):
    owner = await register_user(client, "invite-admin")
    invitee = await register_user(client, "pending-user")
    organization_id = owner["organization_id"]
    owner_headers = auth_headers(owner)
    invitee_headers = auth_headers(invitee)

    first = await client.post(
        f"/api/v1/organizations/{organization_id}/invitations",
        headers=owner_headers,
        json={"email": invitee["email"], "role": "member", "expires_in_days": 1},
    )
    assert first.status_code == 201, first.text
    first_data = first.json()

    duplicate = await client.post(
        f"/api/v1/organizations/{organization_id}/invitations",
        headers=owner_headers,
        json={"email": invitee["email"], "role": "member", "expires_in_days": 1},
    )
    assert duplicate.status_code == 409, duplicate.text

    revoked = await client.delete(
        f"/api/v1/organizations/{organization_id}/invitations/{first_data['id']}",
        headers=owner_headers,
    )
    assert revoked.status_code == 204, revoked.text

    revoked_accept = await client.post(
        "/api/v1/auth/invitations/accept",
        headers=invitee_headers,
        json={"token": first_data["token"]},
    )
    assert revoked_accept.status_code == 409, revoked_accept.text

    second = await client.post(
        f"/api/v1/organizations/{organization_id}/invitations",
        headers=owner_headers,
        json={"email": invitee["email"], "role": "member", "expires_in_days": 1},
    )
    assert second.status_code == 201, second.text
    second_data = second.json()

    async with DatabaseContext() as db:
        stored_result = await db.execute(
            select(OrganizationInvitation).where(
                OrganizationInvitation.id == UUID(second_data["id"])
            )
        )
        stored = stored_result.scalar_one()
        stored.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        await db.commit()

    listed = await client.get(
        f"/api/v1/organizations/{organization_id}/invitations",
        headers=owner_headers,
    )
    assert listed.status_code == 200, listed.text
    expired = next(item for item in listed.json() if item["id"] == second_data["id"])
    assert expired["status"] == "expired"

    expired_accept = await client.post(
        "/api/v1/auth/invitations/accept",
        headers=invitee_headers,
        json={"token": second_data["token"]},
    )
    assert expired_accept.status_code == 409, expired_accept.text


async def test_manager_cannot_manage_privileged_roles_but_can_manage_members(
    client: httpx.AsyncClient,
):
    owner = await register_user(client, "boundary-owner")
    manager = await register_user(client, "boundary-manager")
    second_manager = await register_user(client, "boundary-second-manager")
    member = await register_user(client, "boundary-member")
    candidate = await register_user(client, "boundary-candidate")
    organization_id = owner["organization_id"]
    owner_headers = auth_headers(owner)
    manager_headers = auth_headers(manager)

    manager_added = await client.post(
        f"/api/v1/organizations/{organization_id}/members",
        headers=owner_headers,
        json={"email": manager["email"], "role": "manager"},
    )
    assert manager_added.status_code == 201, manager_added.text

    second_manager_added = await client.post(
        f"/api/v1/organizations/{organization_id}/members",
        headers=owner_headers,
        json={"email": second_manager["email"], "role": "manager"},
    )
    assert second_manager_added.status_code == 201, second_manager_added.text

    member_added = await client.post(
        f"/api/v1/organizations/{organization_id}/members",
        headers=owner_headers,
        json={"email": member["email"], "role": "member"},
    )
    assert member_added.status_code == 201, member_added.text

    privileged_add = await client.post(
        f"/api/v1/organizations/{organization_id}/members",
        headers=manager_headers,
        json={"email": candidate["email"], "role": "manager"},
    )
    assert privileged_add.status_code == 403, privileged_add.text

    privileged_update = await client.patch(
        f"/api/v1/organizations/{organization_id}/members/{second_manager_added.json()['id']}",
        headers=manager_headers,
        json={"role": "member"},
    )
    assert privileged_update.status_code == 403, privileged_update.text

    allowed_add = await client.post(
        f"/api/v1/organizations/{organization_id}/members",
        headers=manager_headers,
        json={"email": candidate["email"], "role": "member"},
    )
    assert allowed_add.status_code == 201, allowed_add.text

    allowed_update = await client.patch(
        f"/api/v1/organizations/{organization_id}/members/{member_added.json()['id']}",
        headers=manager_headers,
        json={"role": "viewer"},
    )
    assert allowed_update.status_code == 200, allowed_update.text
    assert allowed_update.json()["role"] == "viewer"


async def test_superuser_cannot_remove_or_demote_the_last_organization_admin(
    client: httpx.AsyncClient,
):
    owner = await register_user(client, "last-admin-owner")
    superuser = await register_user(client, "last-admin-superuser")
    organization_id = owner["organization_id"]
    owner_id = UUID(owner["session"]["user"]["id"])
    superuser_id = UUID(superuser["session"]["user"]["id"])

    async with DatabaseContext() as db:
        result = await db.execute(select(User).where(User.id == superuser_id))
        stored_superuser = result.scalar_one()
        stored_superuser.is_superuser = True
        await db.commit()

    superuser_headers = auth_headers(superuser)
    demoted = await client.patch(
        f"/api/v1/organizations/{organization_id}/members/{owner_id}",
        headers=superuser_headers,
        json={"role": "member"},
    )
    assert demoted.status_code == 409, demoted.text

    removed = await client.delete(
        f"/api/v1/organizations/{organization_id}/members/{owner_id}",
        headers=superuser_headers,
    )
    assert removed.status_code == 409, removed.text
