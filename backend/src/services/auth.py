"""
Authentication service for SentinelMonitorIA
Handles JWT tokens, password hashing, and user authentication
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, Dict, Any
from uuid import UUID, uuid4
import hashlib
import json
import jwt
from passlib.context import CryptContext
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
import secrets

from src.config.settings import settings
from src.config.logging import logger
from src.models.user import User, Token, UserOrganization, JwtSession
from src.models.organization import Organization
from src.schemas.auth import (
    UserCreateSchema,
    LoginRequestSchema,
    TokenCreateSchema,
    TokenRotateSchema,
    TokenValidationSchema,
    PasswordChangeSchema,
    AuthResponseSchema,
    UserResponseSchema,
    TokenResponseSchema
)


class AuthenticationService:
    """Service for handling authentication and authorization"""
    
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.jwt_secret_key = settings.jwt_secret_key
        self.jwt_algorithm = settings.jwt_algorithm
        self.access_token_expire_minutes = settings.jwt_access_token_expire_minutes
        self.refresh_token_expire_days = settings.jwt_refresh_token_expire_days
        
        # Rate limiting configuration
        self.max_failed_attempts = 5
        self.lockout_minutes = 15
    
    # Password utilities
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Generate password hash"""
        return self.pwd_context.hash(password)

    @staticmethod
    def hash_api_token(token: str) -> str:
        """Return the database digest for an API key.

        API keys are high-entropy JWTs, so a SHA-256 digest is sufficient
        for lookup while keeping the usable credential out of PostgreSQL.
        """
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def is_api_token_digest(value: str) -> bool:
        """Return whether a stored value has the expected SHA-256 format."""
        if len(value) != 64:
            return False
        try:
            int(value, 16)
            return True
        except ValueError:
            return False

    async def persist_jwt_session(
        self,
        db: AsyncSession,
        token: str,
        user_id: UUID,
    ) -> JwtSession:
        """Persist a signed JWT so it can be revoked before expiration."""
        payload = jwt.decode(token, self.jwt_secret_key, algorithms=[self.jwt_algorithm])
        session = JwtSession(
            user_id=user_id,
            jti=payload["jti"],
            token_type=payload["type"],
            expires_at=datetime.utcfromtimestamp(float(payload["exp"])),
        )
        db.add(session)
        await db.flush()
        return session

    async def issue_token_pair(
        self,
        db: AsyncSession,
        token_data: Dict[str, Any],
    ) -> Tuple[str, str]:
        """Issue and persist an access/refresh pair atomically."""
        user_id = UUID(token_data["sub"])
        access_token = self.create_access_token(token_data)
        refresh_token = self.create_refresh_token(token_data)
        await self.persist_jwt_session(db, access_token, user_id)
        await self.persist_jwt_session(db, refresh_token, user_id)
        return access_token, refresh_token

    async def ensure_jwt_session_active(
        self,
        db: AsyncSession,
        payload: Dict[str, Any],
        expected_type: Optional[str] = None,
    ) -> JwtSession:
        """Reject JWTs that are unknown, revoked, expired, or of the wrong type."""
        if expected_type and payload.get("type") != expected_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

        jti = payload.get("jti")
        if not jti:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token session is not registered",
            )

        result = await db.execute(select(JwtSession).where(JwtSession.jti == jti))
        session = result.scalar_one_or_none()
        if not session or session.revoked_at is not None or session.expires_at <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked or is no longer valid",
            )
        return session

    async def revoke_jwt_session(
        self,
        db: AsyncSession,
        jti: str,
        replaced_by_jti: Optional[str] = None,
    ) -> bool:
        """Revoke one persisted JWT session."""
        result = await db.execute(select(JwtSession).where(JwtSession.jti == jti))
        session = result.scalar_one_or_none()
        if not session:
            return False
        if session.revoked_at is None:
            session.revoked_at = datetime.utcnow()
        if replaced_by_jti:
            session.replaced_by_jti = replaced_by_jti
        return True

    async def revoke_user_sessions(self, db: AsyncSession, user_id: UUID) -> int:
        """Revoke every access and refresh JWT issued to a user."""
        result = await db.execute(
            select(JwtSession).where(
                (JwtSession.user_id == user_id) &
                (JwtSession.revoked_at.is_(None))
            )
        )
        sessions = result.scalars().all()
        now = datetime.utcnow()
        for session in sessions:
            session.revoked_at = now
        return len(sessions)

    @staticmethod
    def decode_scopes(value: Optional[str]) -> list[str]:
        """Decode scopes while preserving telemetry access for legacy API keys."""
        if not value:
            return ["telemetry:write"]
        try:
            scopes = json.loads(value)
        except (TypeError, json.JSONDecodeError):
            scopes = [scope.strip() for scope in value.split(",")]
        return sorted({scope for scope in scopes if isinstance(scope, str) and scope.strip()}) or ["telemetry:write"]

    # Legacy API-key rows remain valid and are upgraded on first use.
    async def migrate_legacy_api_keys(self, db: AsyncSession) -> int:
        """Hash legacy API-key rows without changing their usable secrets."""
        result = await db.execute(
            select(Token).where(Token.token_type == "api_key")
        )
        tokens = result.scalars().all()
        migrated = 0
        for token in tokens:
            if not self.is_api_token_digest(token.token):
                token.token = self.hash_api_token(token.token)
                migrated += 1

        if migrated:
            await db.commit()
        return migrated

    # JWT utilities
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access",
            "jti": str(uuid4())
        })
        
        return jwt.encode(to_encode, self.jwt_secret_key, algorithm=self.jwt_algorithm)
    
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh",
            "jti": str(uuid4())
        })
        
        return jwt.encode(to_encode, self.jwt_secret_key, algorithm=self.jwt_algorithm)
    
    def create_api_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create API token (long-lived)"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=365)  # 1 year default
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "api_key",
            "jti": str(uuid4())
        })
        
        return jwt.encode(to_encode, self.jwt_secret_key, algorithm=self.jwt_algorithm)
    
    def decode_token(self, token: str) -> Dict[str, Any]:
        """Decode and validate JWT token"""
        try:
            payload = jwt.decode(
                token,
                self.jwt_secret_key,
                algorithms=[self.jwt_algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    # User operations
    async def create_user(
        self,
        db: AsyncSession,
        user_data: UserCreateSchema,
        is_superuser: bool = False
    ) -> User:
        """Create new user"""
        
        # Check if user already exists
        existing_user = await db.execute(
            select(User).where(
                (User.email == user_data.email) | (User.username == user_data.username)
            )
        )
        existing_user = existing_user.scalar_one_or_none()
        
        if existing_user:
            if existing_user.email == user_data.email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )
        
        # Create user
        hashed_password = self.get_password_hash(user_data.password.get_secret_value())
        
        user = User(
            email=user_data.email,
            username=user_data.username,
            full_name=user_data.full_name,
            hashed_password=hashed_password,
            is_superuser=is_superuser,
            timezone=user_data.timezone,
            locale=user_data.locale
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        logger.info("User created successfully", user_id=str(user.id), username=user.username)
        
        return user
    
    async def authenticate_user(
        self,
        db: AsyncSession,
        login_data: LoginRequestSchema,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[User, str, str]:
        """Authenticate user and return tokens"""
        
        # Find user by username or email
        user = await db.execute(
            select(User).where(
                (User.username == login_data.username) | (User.email == login_data.username)
            )
        )
        user = user.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled"
            )
        
        # Check if account is locked
        if user.is_locked:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account is locked due to too many failed login attempts"
            )
        
        # Verify password
        if not self.verify_password(login_data.password.get_secret_value(), user.hashed_password):
            # Increment failed attempts
            user.failed_login_attempts += 1
            
            # Lock account if max attempts reached
            if user.failed_login_attempts >= self.max_failed_attempts:
                user.locked_until = datetime.utcnow() + timedelta(minutes=self.lockout_minutes)
                logger.warning(
                    "User account locked",
                    user_id=str(user.id),
                    username=user.username,
                    ip_address=ip_address
                )
            
            await db.commit()
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Reset failed attempts on successful login
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login = datetime.utcnow()
        
        await db.commit()
        
        # Create tokens
        token_data = {
            "sub": str(user.id),
            "username": user.username,
            "email": user.email,
            "is_superuser": user.is_superuser
        }
        
        access_token, refresh_token = await self.issue_token_pair(db, token_data)
        await db.commit()

        logger.info(
            "User authenticated successfully",
            user_id=str(user.id),
            username=user.username,
            ip_address=ip_address
        )
        
        return user, access_token, refresh_token
    
    async def refresh_tokens(
        self,
        db: AsyncSession,
        refresh_token: str
    ) -> Tuple[str, str]:
        """Rotate a refresh token and reject replay of the old value."""
        try:
            payload = self.decode_token(refresh_token)
            session = await self.ensure_jwt_session_active(db, payload, "refresh")
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token",
                )

            user_result = await db.execute(select(User).where(User.id == UUID(user_id)))
            user = user_result.scalar_one_or_none()
            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found or inactive",
                )

            token_data = {
                "sub": str(user.id),
                "username": user.username,
                "email": user.email,
                "is_superuser": user.is_superuser,
            }
            access_token, new_refresh_token = await self.issue_token_pair(db, token_data)
            new_payload = self.decode_token(new_refresh_token)
            session.revoked_at = datetime.utcnow()
            session.replaced_by_jti = new_payload["jti"]
            await db.commit()

            logger.info("Tokens refreshed successfully", user_id=str(user.id), username=user.username)
            return access_token, new_refresh_token
        except HTTPException:
            raise
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired",
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

    async def create_api_key(
        self,
        db: AsyncSession,
        user_id: UUID,
        token_data: TokenCreateSchema,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> TokenResponseSchema:
        """Create API key for user"""
        
        # Get user
        user = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = user.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Validate organization if provided
        organization = None
        if token_data.organization_id:
            organization = await db.execute(
                select(Organization).where(Organization.id == token_data.organization_id)
            )
            organization = organization.scalar_one_or_none()
            
            if not organization:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Organization not found"
                )

            membership_result = await db.execute(
                select(UserOrganization).where(
                    (UserOrganization.user_id == user.id) &
                    (UserOrganization.organization_id == organization.id)
                )
            )
            if not membership_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User is not a member of this organization"
                )
        
        # Create token data
        jwt_data = {
            "sub": str(user.id),
            "username": user.username,
            "type": "api_key",
            "name": token_data.name,
            "org": str(token_data.organization_id) if token_data.organization_id else None,
            "scopes": token_data.scopes,
        }
        
        # Set expiration
        expires_delta = None
        expires_at = None
        
        if token_data.expires_in_days:
            expires_delta = timedelta(days=token_data.expires_in_days)
            expires_at = datetime.utcnow() + expires_delta
        
        # Create JWT token
        token_string = self.create_api_token(jwt_data, expires_delta)
        token_digest = self.hash_api_token(token_string)

        # Store only the digest. The usable key is returned once and is not
        # persisted in PostgreSQL.
        token = Token(
            user_id=user.id,
            organization_id=token_data.organization_id,
            token=token_digest,
            token_type="api_key",
            name=token_data.name,
            description=token_data.description,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
            rate_limit_requests=token_data.rate_limit_requests,
            rate_limit_period=token_data.rate_limit_period,
            scopes=json.dumps(token_data.scopes),
        )
        
        db.add(token)
        await db.commit()
        await db.refresh(token)
        
        logger.info(
            "API key created",
            user_id=str(user.id),
            token_id=str(token.id),
            name=token_data.name
        )
        
        # Create response
        response = TokenResponseSchema(
            token=token_string,
            token_type="api_key",
            name=token.name,
            expires_at=token.expires_at,
            created_at=token.created_at,
            rate_limit_requests=token.rate_limit_requests,
            rate_limit_period=token.rate_limit_period,
            organization_id=token.organization_id,
            scopes=token_data.scopes,
            warning="Store this token securely. It will not be shown again."
        )
        
        return response
    
    async def validate_api_token(
        self,
        db: AsyncSession,
        token_string: str,
        organization_id: Optional[UUID] = None,
        required_scope: Optional[str] = None,
    ) -> Tuple[User, Optional[Organization], Token]:
        """Validate an API key, its organization, and an optional permission."""
        try:
            payload = self.decode_token(token_string)
            if payload.get("type") != "api_key":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type",
                )

            token_digest = self.hash_api_token(token_string)
            token_result = await db.execute(
                select(Token).where(
                    (Token.is_active == True) &
                    (Token.revoked_at.is_(None)) &
                    ((Token.token == token_digest) | (Token.token == token_string))
                )
            )
            token = token_result.scalar_one_or_none()
            if not token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token not found or inactive",
                )
            if token.is_expired:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired",
                )

            scopes = self.decode_scopes(token.scopes)
            if required_scope and required_scope not in scopes:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="API key is missing the required scope",
                )

            user_result = await db.execute(
                select(User).where(
                    (User.id == token.user_id) &
                    (User.is_active == True)
                )
            )
            user = user_result.scalar_one_or_none()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found or inactive",
                )

            organization = None
            if token.organization_id:
                organization_result = await db.execute(
                    select(Organization).where(
                        (Organization.id == token.organization_id) &
                        (Organization.is_active == True)
                    )
                )
                organization = organization_result.scalar_one_or_none()
                if not organization:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Organization not found or inactive",
                    )
                if organization_id and organization.id != organization_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Token not authorized for this organization",
                    )

            if token.token == token_string:
                token.token = token_digest
            if not token.scopes:
                token.scopes = json.dumps(scopes)
            token.last_used_at = datetime.utcnow()
            await db.commit()
            return user, organization, token
        except HTTPException:
            raise
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

    
    async def change_password(
        self,
        db: AsyncSession,
        user_id: UUID,
        password_data: PasswordChangeSchema
    ) -> bool:
        """Change user password"""
        
        # Get user
        user = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = user.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Verify current password
        if not self.verify_password(password_data.current_password.get_secret_value(), user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Hash new password
        new_hashed_password = self.get_password_hash(password_data.new_password.get_secret_value())
        
        # Update password
        await db.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                hashed_password=new_hashed_password,
                password_changed_at=datetime.utcnow(),
                failed_login_attempts=0,
                locked_until=None
            )
        )
        
        await self.revoke_user_sessions(db, user_id)
        await db.commit()
        
        return True
    
    async def rotate_api_key(
        self,
        db: AsyncSession,
        user_id: UUID,
        token_id: UUID,
        rotate_data: TokenRotateSchema,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> TokenResponseSchema:
        """Issue a replacement key and explicitly revoke the previous key."""
        result = await db.execute(
            select(Token).where(
                (Token.id == token_id) &
                (Token.user_id == user_id) &
                (Token.token_type == "api_key") &
                (Token.is_active == True)
            )
        )
        previous = result.scalar_one_or_none()
        if not previous:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Active API key not found",
            )

        expires_in_days = rotate_data.expires_in_days
        if expires_in_days is None and previous.expires_at:
            remaining = (previous.expires_at - datetime.now(timezone.utc)).total_seconds()
            expires_in_days = max(1, int(remaining / 86400) + 1)

        replacement_data = TokenCreateSchema(
            name=rotate_data.name or previous.name or "Rotated API key",
            description=rotate_data.description if rotate_data.description is not None else previous.description,
            expires_in_days=expires_in_days,
            organization_id=previous.organization_id,
            rate_limit_requests=previous.rate_limit_requests,
            rate_limit_period=previous.rate_limit_period,
            scopes=rotate_data.scopes or self.decode_scopes(previous.scopes),
        )
        replacement = await self.create_api_key(
            db,
            user_id,
            replacement_data,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        replacement_result = await db.execute(
            select(Token).where(
                (Token.user_id == user_id) &
                (Token.token == self.hash_api_token(replacement.token))
            )
        )
        replacement_token = replacement_result.scalar_one()
        previous.is_active = False
        previous.revoked_at = datetime.utcnow()
        previous.replaced_by_id = replacement_token.id
        await db.commit()
        return replacement

    async def revoke_token(
        self,
        db: AsyncSession,
        user_id: UUID,
        token_id: UUID
    ) -> bool:
        """Revoke (disable) token"""
        
        # Get token
        token = await db.execute(
            select(Token).where(
                (Token.id == token_id) &
                (Token.user_id == user_id)
            )
        )
        token = token.scalar_one_or_none()
        
        if not token:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Token not found"
            )
        
        # Disable token
        token.is_active = False
        token.revoked_at = datetime.utcnow()
        await db.commit()
        
        logger.info("Token revoked", user_id=str(user_id), token_id=str(token_id))
        
        return True
    
    async def get_user_tokens(
        self,
        db: AsyncSession,
        user_id: UUID
    ) -> list[Token]:
        """Get all tokens for user"""
        
        tokens = await db.execute(
            select(Token).where(
                (Token.user_id == user_id) &
                (Token.is_active == True)
            ).order_by(Token.created_at.desc())
        )
        
        return tokens.scalars().all()
    
    # Helper methods
    def create_auth_response(
        self,
        user: User,
        access_token: str,
        refresh_token: str
    ) -> AuthResponseSchema:
        """Create authentication response"""
        
        user_response = UserResponseSchema(
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
            organizations=[]
        )
        
        return AuthResponseSchema(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=self.access_token_expire_minutes * 60,
            user=user_response
        )


# Global authentication service instance
auth_service = AuthenticationService()