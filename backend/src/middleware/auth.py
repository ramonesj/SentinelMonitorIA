"""Compatibility authentication dependencies for older API routers.

The active v1 auth routes use ``src.api.v1.auth`` directly. This module
remains as a compatibility facade and delegates API-key validation to the
same persistent AuthenticationService; it does not accept development-only
test tokens.
"""

from typing import Any, Dict, Optional, Tuple
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logging import logger
from src.database.database import get_db_session
from src.models.organization import Organization
from src.models.user import Token, User, UserOrganization
from src.services.auth import auth_service
from src.services.rate_limiter import rate_limiter


class JWTBearer(HTTPBearer):
    """Bearer dependency retained for older routers."""

    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)

    async def __call__(
        self, request: Request
    ) -> Optional[HTTPAuthorizationCredentials]:
        credentials = await super().__call__(request)
        if credentials and credentials.scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid authentication scheme",
            )
        return credentials


class AuthenticationMiddleware:
    """Compatibility facade backed by the active authentication service."""

    public_paths = {
        "/api/v1/health",
        "/api/v1/metrics",
        "/api/v1/docs",
        "/api/v1/redoc",
        "/api/v1/openapi.json",
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/refresh",
    }

    async def authenticate(
        self,
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = None,
        db: Optional[AsyncSession] = None,
    ) -> Tuple[
        Optional[User],
        Optional[Organization],
        Optional[Token],
        Dict[str, Any],
    ]:
        """Resolve a user or API key using the canonical auth service."""
        endpoint = request.url.path
        ip_address = request.client.host if request.client else "unknown"

        if endpoint in self.public_paths or endpoint.startswith(("/docs", "/redoc")):
            return None, None, None, {}

        token = credentials.credentials if credentials else None
        if not token:
            authorization = request.headers.get("authorization", "")
            if not authorization.lower().startswith("bearer "):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authorization header missing",
                )
            token = authorization[7:].strip()

        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing",
            )

        payload = auth_service.decode_token(token)
        token_type = payload.get("type")

        if token_type == "api_key":
            if db is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Database session required for API key validation",
                )
            user, organization, token_obj = await auth_service.validate_api_token(
                db, token
            )
            rate_limit_info = await rate_limiter.enforce_rate_limit(
                ip_address=ip_address,
                organization_id=organization.id if organization else None,
                token_id=token_obj.id,
                token_limit=token_obj.rate_limit_requests,
                token_period=token_obj.rate_limit_period,
                endpoint=endpoint,
            )
            return user, organization, token_obj, rate_limit_info

        if token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="An access token is required",
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )

        try:
            user = User(
                id=UUID(user_id),
                username=payload.get("username", "unknown"),
                email=payload.get("email", "unknown"),
                is_superuser=payload.get("is_superuser", False),
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token subject",
            ) from exc

        rate_limit_info = await rate_limiter.enforce_rate_limit(
            ip_address=ip_address,
            endpoint=endpoint,
        )
        logger.debug(
            "JWT token authenticated",
            user_id=user_id,
            endpoint=endpoint,
            ip_address=ip_address,
        )
        return user, None, None, rate_limit_info

    async def require_authentication(
        self,
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = None,
        db: Optional[AsyncSession] = None,
    ) -> Tuple[User, Dict[str, Any]]:
        user, _, _, rate_limit_info = await self.authenticate(request, credentials, db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
        return user, rate_limit_info

    async def require_superuser(
        self,
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = None,
        db: Optional[AsyncSession] = None,
    ) -> Tuple[User, Dict[str, Any]]:
        user, rate_limit_info = await self.require_authentication(
            request, credentials, db
        )
        if not user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Superuser privileges required",
            )
        return user, rate_limit_info

    async def require_organization_access(
        self,
        request: Request,
        organization_id: UUID,
        credentials: Optional[HTTPAuthorizationCredentials] = None,
        db: Optional[AsyncSession] = None,
    ) -> Tuple[User, Organization, Dict[str, Any]]:
        user, organization, token, rate_limit_info = await self.authenticate(
            request, credentials, db
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
        if db is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database session required for organization access",
            )

        if token and token.organization_id and token.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Token not authorized for this organization",
            )

        if not user.is_superuser:
            membership = await db.execute(
                select(UserOrganization).where(
                    (UserOrganization.user_id == user.id)
                    & (UserOrganization.organization_id == organization_id)
                )
            )
            if not membership.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User is not a member of this organization",
                )

        organization_result = await db.execute(
            select(Organization).where(
                (Organization.id == organization_id)
                & (Organization.is_active == True)
            )
        )
        organization = organization_result.scalar_one_or_none()
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found or inactive",
            )
        return user, organization, rate_limit_info

    def create_auth_headers(self, rate_limit_info: Dict[str, Any]) -> Dict[str, str]:
        headers = {
            "X-Authenticated-User": "true",
            "Cache-Control": "no-store",
            "Pragma": "no-cache",
        }
        global_info = (rate_limit_info or {}).get("global")
        if global_info:
            headers.update(
                {
                    "X-RateLimit-Limit": str(global_info.get("limit", "unknown")),
                    "X-RateLimit-Remaining": str(
                        global_info.get("remaining", "unknown")
                    ),
                    "X-RateLimit-Reset": str(
                        global_info.get("reset_in", "unknown")
                    ),
                }
            )
        return headers


# Kept for compatibility with older imports. It is not registered globally.
auth_middleware = AuthenticationMiddleware()


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(JWTBearer()),
    db: AsyncSession = Depends(get_db_session),
) -> Tuple[User, Dict[str, Any]]:
    return await auth_middleware.require_authentication(request, credentials, db)


async def get_current_superuser(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(JWTBearer()),
    db: AsyncSession = Depends(get_db_session),
) -> Tuple[User, Dict[str, Any]]:
    return await auth_middleware.require_superuser(request, credentials, db)


async def get_current_organization(
    request: Request,
    organization_id: UUID,
    credentials: HTTPAuthorizationCredentials = Depends(JWTBearer()),
    db: AsyncSession = Depends(get_db_session),
) -> Tuple[User, Organization, Dict[str, Any]]:
    return await auth_middleware.require_organization_access(
        request, organization_id, credentials, db
    )


async def validate_api_token(
    token: str,
    organization_id: Optional[UUID] = None,
    db: Optional[AsyncSession] = None,
) -> Tuple[User, Optional[Organization], Token]:
    """Compatibility wrapper around persistent API-key validation."""
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database session required for API token validation",
        )
    return await auth_service.validate_api_token(db, token, organization_id)
