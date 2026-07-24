"""Authentication API for local and production-ready JWT flows."""

from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.database import get_db_session
from src.api.v1.rate_limit import (
    enforce_registration_rate_limit,
    enforce_request_rate_limit,
)
from src.services.auth import auth_service
from src.services.organizations import accept_organization_invitation, require_member_manager
from src.models.organization import Organization
from src.models.user import Token, User, UserOrganization
from src.schemas.auth import (
    AuthResponseSchema,
    OrganizationInvitationAcceptResponseSchema,
    OrganizationInvitationAcceptSchema,
    LoginRequestSchema,
    PasswordChangeSchema,
    TokenCreateSchema,
    TokenResponseSchema,
    TokenRotateSchema,
    UserCreateSchema,
    UserResponseSchema,
)


router = APIRouter(prefix="/auth", tags=["authentication"])
bearer_scheme = HTTPBearer(auto_error=True)


class RegisterRequestSchema(UserCreateSchema):
    """Local registration payload with an initial organization."""

    organization_name: str = Field(default="Sentinel Local", min_length=3, max_length=255)
    organization_slug: str = Field(
        default="sentinel-local",
        min_length=3,
        max_length=100,
        pattern=r"^[a-z0-9-]+$",
    )


class RefreshRequestSchema(BaseModel):
    """Refresh token payload."""

    refresh_token: str = Field(..., min_length=20)


async def _load_user(db: AsyncSession, user_id: UUID) -> Optional[User]:
    result = await db.execute(
        select(User)
        .options(selectinload(User.organizations).selectinload(UserOrganization.organization))
        .where(User.id == user_id)
    )
    return result.scalar_one_or_none()


def _serialize_user(user: User) -> UserResponseSchema:
    organizations = []
    for membership in user.organizations or []:
        organization = membership.organization
        if organization:
            organizations.append(
                {
                    "id": str(organization.id),
                    "name": organization.name,
                    "slug": organization.slug,
                    "role": membership.role,
                    "is_active": organization.is_active,
                }
            )

    return UserResponseSchema(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        is_active=user.is_active,
        is_verified=user.is_verified,
        is_superuser=user.is_superuser,
        timezone=user.timezone,
        locale=user.locale,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login=user.last_login,
        organizations=organizations,
    )


def _auth_response(user: User, access_token: str, refresh_token: str) -> AuthResponseSchema:
    return AuthResponseSchema(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=auth_service.access_token_expire_minutes * 60,
        user=_serialize_user(user),
    )


async def get_current_user_record(
    request: Request,
    response: Response,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """Resolve an active user from an access JWT."""
    await enforce_request_rate_limit(request, response)
    payload = auth_service.decode_token(credentials.credentials)
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="An access token is required",
        )

    await auth_service.ensure_jwt_session_active(db, payload, "access")

    try:
        user_id = UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        ) from exc

    user = await _load_user(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return user


@router.post(
    "/register",
    response_model=AuthResponseSchema,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(enforce_registration_rate_limit)],
)
async def register(
    request: Request,
    register_data: RegisterRequestSchema,
    db: AsyncSession = Depends(get_db_session),
):
    """Create a local user and attach it to an initial organization."""
    user = await auth_service.create_user(db, register_data)

    organization_result = await db.execute(
        select(Organization).where(Organization.slug == register_data.organization_slug)
    )
    organization = organization_result.scalar_one_or_none()
    if not organization:
        organization = Organization(
            name=register_data.organization_name,
            slug=register_data.organization_slug,
            email=register_data.email,
            timezone=register_data.timezone,
            locale=register_data.locale,
        )
        db.add(organization)
        await db.flush()

    membership = UserOrganization(
        user_id=user.id,
        organization_id=organization.id,
        role="admin",
        permissions="{}",
    )
    db.add(membership)
    await db.commit()

    authenticated_user, access_token, refresh_token = await auth_service.authenticate_user(
        db,
        LoginRequestSchema(username=register_data.username, password=register_data.password),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    loaded_user = await _load_user(db, authenticated_user.id)
    return _auth_response(loaded_user or authenticated_user, access_token, refresh_token)


@router.post(
    "/login",
    response_model=AuthResponseSchema,
    dependencies=[Depends(enforce_request_rate_limit)],
)
async def login(
    request: Request,
    login_data: LoginRequestSchema,
    db: AsyncSession = Depends(get_db_session),
):
    """Authenticate with username or email and issue access/refresh JWTs."""
    user, access_token, refresh_token = await auth_service.authenticate_user(
        db,
        login_data,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    loaded_user = await _load_user(db, user.id)
    return _auth_response(loaded_user or user, access_token, refresh_token)


@router.post(
    "/refresh",
    dependencies=[Depends(enforce_request_rate_limit)],
)
async def refresh(
    refresh_data: RefreshRequestSchema,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """Rotate access and refresh tokens."""
    access_token, new_refresh_token = await auth_service.refresh_tokens(db, refresh_data.refresh_token)
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": auth_service.access_token_expire_minutes * 60,
    }


@router.get("/me", response_model=UserResponseSchema)
async def current_user(user: User = Depends(get_current_user_record)):
    """Return the authenticated user and organization memberships."""
    return _serialize_user(user)


@router.post("/logout")
async def logout(
    user: User = Depends(get_current_user_record),
    db: AsyncSession = Depends(get_db_session),
):
    """Revoke all JWT sessions for the authenticated user."""
    revoked = await auth_service.revoke_user_sessions(db, user.id)
    await db.commit()
    return {
        "status": "success",
        "message": f"Session closed for {user.username}",
        "revoked_sessions": revoked,
    }


@router.post("/change-password")
async def change_password(
    password_data: PasswordChangeSchema,
    user: User = Depends(get_current_user_record),
    db: AsyncSession = Depends(get_db_session),
):
    """Change the authenticated user's password."""
    await auth_service.change_password(db, user.id, password_data)
    return {"status": "success", "message": "Password changed successfully"}


@router.post("/api-keys", response_model=TokenResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    token_data: TokenCreateSchema,
    request: Request,
    user: User = Depends(get_current_user_record),
    db: AsyncSession = Depends(get_db_session),
):
    """Create a long-lived API key for telemetry agents."""
    if token_data.organization_id:
        await require_member_manager(db, user, token_data.organization_id)
    return await auth_service.create_api_key(
        db,
        user.id,
        token_data,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.get("/api-keys")
async def list_api_keys(
    user: User = Depends(get_current_user_record),
    db: AsyncSession = Depends(get_db_session),
):
    """List API key metadata without exposing token values."""
    tokens = await auth_service.get_user_tokens(db, user.id)
    return {
        "status": "success",
        "tokens": [
            {
                "id": str(token.id),
                "name": token.name,
                "token_type": token.token_type,
                "created_at": token.created_at,
                "expires_at": token.expires_at,
                "last_used_at": token.last_used_at,
                "is_active": token.is_active,
                "organization_id": str(token.organization_id) if token.organization_id else None,
                "scopes": auth_service.decode_scopes(token.scopes),
            }
            for token in tokens
        ],
    }


@router.delete("/api-keys/{token_id}")
async def revoke_api_key(
    token_id: UUID,
    user: User = Depends(get_current_user_record),
    db: AsyncSession = Depends(get_db_session),
):
    """Revoke an API key owned by the authenticated user."""
    await auth_service.revoke_token(db, user.id, token_id)
    return {"status": "success", "message": "API key revoked"}


@router.post("/api-keys/{token_id}/rotate", response_model=TokenResponseSchema)
async def rotate_api_key(
    token_id: UUID,
    rotate_data: TokenRotateSchema,
    request: Request,
    user: User = Depends(get_current_user_record),
    db: AsyncSession = Depends(get_db_session),
):
    """Create a replacement API key and revoke the previous one immediately."""
    return await auth_service.rotate_api_key(
        db,
        user.id,
        token_id,
        rotate_data,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.post(
    "/invitations/accept",
    response_model=OrganizationInvitationAcceptResponseSchema,
)
async def accept_invitation(
    invitation_data: OrganizationInvitationAcceptSchema,
    user: User = Depends(get_current_user_record),
    db: AsyncSession = Depends(get_db_session),
):
    """Accept a one-time invitation for the authenticated matching email."""
    _, organization, membership = await accept_organization_invitation(
        db,
        invitation_data.token,
        user,
    )
    return OrganizationInvitationAcceptResponseSchema(
        organization_id=organization.id,
        organization_name=organization.name,
        role=membership.role,
        status="accepted",
    )
