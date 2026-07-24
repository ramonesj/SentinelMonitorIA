"""Organization membership and role management API."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.auth import get_current_user_record
from src.database.database import get_db_session
from src.models.organization import OrganizationInvitation
from src.models.user import User, UserOrganization
from src.schemas.auth import (
    OrganizationMemberCreateSchema,
    OrganizationMemberResponseSchema,
    OrganizationMemberRoleSchema,
    OrganizationInvitationCreateSchema,
    OrganizationInvitationResponseSchema,
)
from src.services.organizations import (
    add_organization_member,
    list_organization_members,
    remove_organization_member,
    update_organization_member_role,
    require_organization_membership,
    create_organization_invitation,
    list_organization_invitations,
    revoke_organization_invitation,
)


router = APIRouter(prefix="/organizations", tags=["organizations"])


def serialize_member(membership: UserOrganization) -> OrganizationMemberResponseSchema:
    user = membership.user
    return OrganizationMemberResponseSchema(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        role=membership.role,
        is_active=user.is_active,
        joined_at=membership.joined_at,
    )


@router.get(
    "/{organization_id}/members",
    response_model=List[OrganizationMemberResponseSchema],
)
async def get_members(
    organization_id: UUID,
    user: User = Depends(get_current_user_record),
    db: AsyncSession = Depends(get_db_session),
):
    """List members for an organization the caller can access."""
    await require_organization_membership(db, user, organization_id)
    members = await list_organization_members(db, organization_id)
    return [serialize_member(member) for member in members]


@router.post(
    "/{organization_id}/members",
    response_model=OrganizationMemberResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def add_member(
    organization_id: UUID,
    member_data: OrganizationMemberCreateSchema,
    user: User = Depends(get_current_user_record),
    db: AsyncSession = Depends(get_db_session),
):
    """Add an existing active user to an organization."""
    membership = await add_organization_member(
        db,
        organization_id,
        str(member_data.email),
        member_data.role,
        user,
    )
    return serialize_member(membership)


@router.patch(
    "/{organization_id}/members/{member_id}",
    response_model=OrganizationMemberResponseSchema,
)
async def update_member(
    organization_id: UUID,
    member_id: UUID,
    member_data: OrganizationMemberRoleSchema,
    user: User = Depends(get_current_user_record),
    db: AsyncSession = Depends(get_db_session),
):
    """Change a member role according to the caller's organization role."""
    membership = await update_organization_member_role(
        db,
        organization_id,
        member_id,
        member_data.role,
        user,
    )
    return serialize_member(membership)


@router.delete(
    "/{organization_id}/members/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_member(
    organization_id: UUID,
    member_id: UUID,
    user: User = Depends(get_current_user_record),
    db: AsyncSession = Depends(get_db_session),
):
    """Remove a member while preserving the organization's last admin."""
    await remove_organization_member(db, organization_id, member_id, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def serialize_invitation(
    invitation: OrganizationInvitation,
    token: str | None = None,
) -> OrganizationInvitationResponseSchema:
    return OrganizationInvitationResponseSchema(
        id=invitation.id,
        email=invitation.email,
        role=invitation.role,
        status=invitation.status,
        expires_at=invitation.expires_at,
        created_at=invitation.created_at,
        accepted_at=invitation.accepted_at,
        revoked_at=invitation.revoked_at,
        token=token,
    )


@router.post(
    "/{organization_id}/invitations",
    response_model=OrganizationInvitationResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_invitation(
    organization_id: UUID,
    invitation_data: OrganizationInvitationCreateSchema,
    user: User = Depends(get_current_user_record),
    db: AsyncSession = Depends(get_db_session),
):
    """Create a one-time invitation for an organization member."""
    invitation, raw_token = await create_organization_invitation(
        db,
        organization_id,
        str(invitation_data.email),
        invitation_data.role,
        invitation_data.expires_in_days,
        user,
    )
    return serialize_invitation(invitation, raw_token)


@router.get(
    "/{organization_id}/invitations",
    response_model=List[OrganizationInvitationResponseSchema],
)
async def get_invitations(
    organization_id: UUID,
    user: User = Depends(get_current_user_record),
    db: AsyncSession = Depends(get_db_session),
):
    """List invitation metadata without exposing raw tokens."""
    await require_organization_membership(db, user, organization_id)
    invitations = await list_organization_invitations(db, organization_id)
    return [serialize_invitation(invitation) for invitation in invitations]


@router.delete(
    "/{organization_id}/invitations/{invitation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_invitation(
    organization_id: UUID,
    invitation_id: UUID,
    user: User = Depends(get_current_user_record),
    db: AsyncSession = Depends(get_db_session),
):
    """Revoke a pending organization invitation."""
    await revoke_organization_invitation(db, organization_id, invitation_id, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
