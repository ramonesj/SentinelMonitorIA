"""Organization membership and role-based access helpers."""

from datetime import datetime, timedelta, timezone
import hashlib
import json
import secrets
from typing import Optional, Sequence
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.organization import Organization, OrganizationInvitation
from src.models.user import User, UserOrganization
from src.schemas.auth import UserRole


ROLE_ORDER = {
    UserRole.GUEST.value: 10,
    UserRole.VIEWER.value: 20,
    UserRole.MEMBER.value: 30,
    UserRole.MANAGER.value: 40,
    UserRole.ADMIN.value: 50,
}
MANAGER_ROLES = {UserRole.ADMIN.value, UserRole.MANAGER.value}


def role_value(role: UserRole | str) -> str:
    """Normalize enum and persisted role values to a string."""
    return role.value if isinstance(role, UserRole) else role


async def get_active_organization(
    db: AsyncSession,
    organization_id: UUID,
) -> Organization:
    result = await db.execute(
        select(Organization).where(
            (Organization.id == organization_id) &
            (Organization.is_active == True)
        )
    )
    organization = result.scalar_one_or_none()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found or inactive",
        )
    return organization


async def get_membership(
    db: AsyncSession,
    user_id: UUID,
    organization_id: UUID,
) -> Optional[UserOrganization]:
    result = await db.execute(
        select(UserOrganization)
        .options(selectinload(UserOrganization.user))
        .where(
            (UserOrganization.user_id == user_id) &
            (UserOrganization.organization_id == organization_id)
        )
    )
    return result.scalar_one_or_none()


async def require_organization_membership(
    db: AsyncSession,
    user: User,
    organization_id: UUID,
) -> Optional[UserOrganization]:
    """Require an active organization and a membership for the current user."""
    await get_active_organization(db, organization_id)
    if user.is_superuser:
        return None

    membership = await get_membership(db, user.id, organization_id)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of this organization",
        )
    return membership


async def require_member_manager(
    db: AsyncSession,
    user: User,
    organization_id: UUID,
) -> Optional[UserOrganization]:
    """Require admin or manager membership for membership mutations."""
    membership = await require_organization_membership(db, user, organization_id)
    if user.is_superuser:
        return membership
    if membership.role not in MANAGER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or manager role required",
        )
    return membership


def assert_target_role_allowed(
    actor_role: Optional[str],
    target_role: str,
    actor_is_superuser: bool = False,
) -> None:
    """Prevent managers from assigning or changing privileged roles."""
    if actor_is_superuser or actor_role == UserRole.ADMIN.value:
        return
    if actor_role != UserRole.MANAGER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or manager role required",
        )
    if ROLE_ORDER.get(target_role, 0) >= ROLE_ORDER[UserRole.MANAGER.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Managers can only manage roles below manager",
        )


async def list_organization_members(
    db: AsyncSession,
    organization_id: UUID,
) -> Sequence[UserOrganization]:
    await get_active_organization(db, organization_id)
    result = await db.execute(
        select(UserOrganization)
        .options(selectinload(UserOrganization.user))
        .where(UserOrganization.organization_id == organization_id)
        .order_by(UserOrganization.joined_at.asc())
    )
    return result.scalars().all()


async def add_organization_member(
    db: AsyncSession,
    organization_id: UUID,
    email: str,
    role: UserRole | str,
    actor: User,
) -> UserOrganization:
    actor_membership = await require_member_manager(db, actor, organization_id)
    normalized_role = role_value(role)
    assert_target_role_allowed(
        actor_membership.role if actor_membership else None,
        normalized_role,
        actor.is_superuser,
    )

    user_result = await db.execute(
        select(User).where(func.lower(User.email) == email.lower())
    )
    target_user = user_result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un usuario registrado con ese email",
        )
    if not target_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario está inactivo",
        )

    existing = await get_membership(db, target_user.id, organization_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El usuario ya pertenece a esta organización",
        )

    membership = UserOrganization(
        user_id=target_user.id,
        organization_id=organization_id,
        role=normalized_role,
        permissions="{}",
    )
    db.add(membership)
    await db.commit()
    await db.refresh(membership)
    membership.user = target_user
    return membership


async def update_organization_member_role(
    db: AsyncSession,
    organization_id: UUID,
    target_user_id: UUID,
    role: UserRole | str,
    actor: User,
) -> UserOrganization:
    actor_membership = await require_member_manager(db, actor, organization_id)
    if actor.id == target_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes cambiar tu propio rol",
        )

    membership = await get_membership(db, target_user_id, organization_id)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Miembro no encontrado en esta organización",
        )

    normalized_role = role_value(role)
    assert_target_role_allowed(
        actor_membership.role if actor_membership else None,
        membership.role,
        actor.is_superuser,
    )
    assert_target_role_allowed(
        actor_membership.role if actor_membership else None,
        normalized_role,
        actor.is_superuser,
    )

    if membership.role == UserRole.ADMIN.value and normalized_role != UserRole.ADMIN.value:
        admin_count_result = await db.execute(
            select(func.count()).select_from(UserOrganization).where(
                (UserOrganization.organization_id == organization_id) &
                (UserOrganization.role == UserRole.ADMIN.value)
            )
        )
        if admin_count_result.scalar_one() <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La organización debe conservar al menos un administrador",
            )

    membership.role = normalized_role
    await db.commit()
    await db.refresh(membership)
    return membership


async def remove_organization_member(
    db: AsyncSession,
    organization_id: UUID,
    target_user_id: UUID,
    actor: User,
) -> None:
    actor_membership = await require_member_manager(db, actor, organization_id)
    if actor.id == target_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes retirarte a ti mismo de esta organización",
        )

    membership = await get_membership(db, target_user_id, organization_id)
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Miembro no encontrado en esta organización",
        )

    assert_target_role_allowed(
        actor_membership.role if actor_membership else None,
        membership.role,
        actor.is_superuser,
    )
    if membership.role == UserRole.ADMIN.value:
        admin_count_result = await db.execute(
            select(func.count()).select_from(UserOrganization).where(
                (UserOrganization.organization_id == organization_id) &
                (UserOrganization.role == UserRole.ADMIN.value)
            )
        )
        if admin_count_result.scalar_one() <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La organización debe conservar al menos un administrador",
            )

    await db.delete(membership)
    await db.commit()


INVITATION_PENDING = "pending"
INVITATION_ACCEPTED = "accepted"
INVITATION_EXPIRED = "expired"
INVITATION_REVOKED = "revoked"


def hash_invitation_token(token: str) -> str:
    """Hash the raw invitation token before persisting it."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def create_organization_invitation(
    db: AsyncSession,
    organization_id: UUID,
    email: str,
    role: UserRole | str,
    expires_in_days: int,
    actor: User,
) -> tuple[OrganizationInvitation, str]:
    """Create a single-use invitation and return its raw token once."""
    actor_membership = await require_member_manager(db, actor, organization_id)
    normalized_role = role_value(role)
    assert_target_role_allowed(
        actor_membership.role if actor_membership else None,
        normalized_role,
        actor.is_superuser,
    )

    normalized_email = email.strip().lower()
    existing_user_result = await db.execute(
        select(User).where(func.lower(User.email) == normalized_email)
    )
    existing_user = existing_user_result.scalar_one_or_none()
    if existing_user and await get_membership(db, existing_user.id, organization_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El usuario ya pertenece a esta organización",
        )

    now = datetime.now(timezone.utc)
    pending_result = await db.execute(
        select(OrganizationInvitation).where(
            (OrganizationInvitation.organization_id == organization_id) &
            (func.lower(OrganizationInvitation.email) == normalized_email) &
            (OrganizationInvitation.status == INVITATION_PENDING)
        )
    )
    pending = pending_result.scalars().all()
    for invitation in pending:
        if invitation.expires_at > now:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe una invitación pendiente para este email",
            )
        invitation.status = INVITATION_EXPIRED

    raw_token = secrets.token_urlsafe(32)
    invitation = OrganizationInvitation(
        organization_id=organization_id,
        invited_by_user_id=actor.id,
        email=normalized_email,
        role=normalized_role,
        token_hash=hash_invitation_token(raw_token),
        status=INVITATION_PENDING,
        expires_at=now + timedelta(days=expires_in_days),
        created_by=actor.id,
        updated_by=actor.id,
    )
    db.add(invitation)
    await db.commit()
    await db.refresh(invitation)
    return invitation, raw_token


async def list_organization_invitations(
    db: AsyncSession,
    organization_id: UUID,
) -> Sequence[OrganizationInvitation]:
    """List invitation history and mark stale pending entries as expired."""
    await get_active_organization(db, organization_id)
    result = await db.execute(
        select(OrganizationInvitation)
        .where(OrganizationInvitation.organization_id == organization_id)
        .order_by(OrganizationInvitation.created_at.desc())
    )
    invitations = result.scalars().all()
    now = datetime.now(timezone.utc)
    changed = False
    for invitation in invitations:
        if invitation.status == INVITATION_PENDING and invitation.expires_at <= now:
            invitation.status = INVITATION_EXPIRED
            changed = True
    if changed:
        await db.commit()
    return invitations


async def revoke_organization_invitation(
    db: AsyncSession,
    organization_id: UUID,
    invitation_id: UUID,
    actor: User,
) -> None:
    """Revoke a pending invitation under organization RBAC."""
    actor_membership = await require_member_manager(db, actor, organization_id)
    result = await db.execute(
        select(OrganizationInvitation).where(
            (OrganizationInvitation.id == invitation_id) &
            (OrganizationInvitation.organization_id == organization_id)
        )
    )
    invitation = result.scalar_one_or_none()
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitación no encontrada",
        )
    if invitation.status != INVITATION_PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Sólo se pueden revocar invitaciones pendientes",
        )
    assert_target_role_allowed(
        actor_membership.role if actor_membership else None,
        invitation.role,
        actor.is_superuser,
    )
    invitation.status = INVITATION_REVOKED
    invitation.revoked_at = datetime.now(timezone.utc)
    invitation.updated_by = actor.id
    await db.commit()


async def accept_organization_invitation(
    db: AsyncSession,
    raw_token: str,
    user: User,
) -> tuple[OrganizationInvitation, Organization, UserOrganization]:
    """Consume a valid invitation for the authenticated matching email."""
    token_hash = hash_invitation_token(raw_token.strip())
    result = await db.execute(
        select(OrganizationInvitation).where(
            OrganizationInvitation.token_hash == token_hash
        )
    )
    invitation = result.scalar_one_or_none()
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitación inválida o inexistente",
        )

    now = datetime.now(timezone.utc)
    if invitation.status == INVITATION_PENDING and invitation.expires_at <= now:
        invitation.status = INVITATION_EXPIRED
        await db.commit()
    if invitation.status != INVITATION_PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"La invitación ya no está disponible ({invitation.status})",
        )
    if invitation.email.lower() != user.email.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La invitación no corresponde al email de la sesión actual",
        )

    organization = await get_active_organization(db, invitation.organization_id)
    existing = await get_membership(db, user.id, organization.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El usuario ya pertenece a esta organización",
        )

    membership = UserOrganization(
        user_id=user.id,
        organization_id=organization.id,
        role=invitation.role,
        permissions=json.dumps({}),
    )
    db.add(membership)
    invitation.status = INVITATION_ACCEPTED
    invitation.accepted_at = now
    invitation.accepted_by_user_id = user.id
    invitation.updated_by = user.id
    await db.commit()
    await db.refresh(membership)
    membership.user = user
    return invitation, organization, membership
