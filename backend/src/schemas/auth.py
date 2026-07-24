"""
Pydantic schemas for authentication and authorization
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, EmailStr, validator, SecretStr
from enum import Enum


class UserRole(str, Enum):
    """User roles"""
    ADMIN = "admin"
    MANAGER = "manager"
    MEMBER = "member"
    VIEWER = "viewer"
    GUEST = "guest"


class TokenType(str, Enum):
    """Token types"""
    ACCESS = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"
    SESSION = "session"


class UserCreateSchema(BaseModel):
    """Schema for user creation"""
    
    email: EmailStr = Field(
        ...,
        description="User email address"
    )
    
    username: str = Field(
        ...,
        description="Username",
        min_length=3,
        max_length=100,
        pattern="^[a-zA-Z0-9_.-]+$",
        examples=["john.doe", "admin", "user123"]
    )
    
    password: SecretStr = Field(
        ...,
        description="Password",
        min_length=8,
        examples=["Str0ngP@ssw0rd!"]
    )
    
    full_name: Optional[str] = Field(
        default=None,
        description="Full name",
        max_length=255,
        examples=["John Doe", "Jane Smith"]
    )
    
    timezone: str = Field(
        default="UTC",
        description="Timezone",
        max_length=50,
        examples=["UTC", "America/New_York", "Europe/London"]
    )
    
    locale: str = Field(
        default="en-US",
        description="Locale",
        max_length=10,
        examples=["en-US", "es-ES", "fr-FR"]
    )
    
    @validator("username")
    def validate_username(cls, v):
        """Validate username"""
        if not v or not v.strip():
            raise ValueError("Username cannot be empty")
        
        # Check for reserved usernames
        reserved = ["admin", "root", "system", "support", "info", "noreply"]
        if v.lower() in reserved:
            raise ValueError(f"Username '{v}' is reserved")
        
        return v.strip()
    
    @validator("password")
    def validate_password_strength(cls, v):
        """Validate password strength"""
        password = v.get_secret_value()
        
        # Check length
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        # Check for uppercase
        if not any(c.isupper() for c in password):
            raise ValueError("Password must contain at least one uppercase letter")
        
        # Check for lowercase
        if not any(c.islower() for c in password):
            raise ValueError("Password must contain at least one lowercase letter")
        
        # Check for digit
        if not any(c.isdigit() for c in password):
            raise ValueError("Password must contain at least one digit")
        
        # Check for special character
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in password):
            raise ValueError("Password must contain at least one special character")
        
        return v


class UserUpdateSchema(BaseModel):
    """Schema for user update"""
    
    full_name: Optional[str] = Field(
        default=None,
        description="Full name",
        max_length=255
    )
    
    timezone: Optional[str] = Field(
        default=None,
        description="Timezone",
        max_length=50
    )
    
    locale: Optional[str] = Field(
        default=None,
        description="Locale",
        max_length=10
    )
    
    is_active: Optional[bool] = Field(
        default=None,
        description="Whether user is active"
    )
    
    is_verified: Optional[bool] = Field(
        default=None,
        description="Whether user is verified"
    )
    
    @validator("timezone")
    def validate_timezone(cls, v):
        """Validate timezone"""
        if v is not None and v not in ["UTC", "America/New_York", "Europe/London"]:
            # In production, you'd validate against pytz.all_timezones
            raise ValueError(f"Invalid timezone: {v}")
        return v


class UserResponseSchema(BaseModel):
    """Schema for user response"""
    
    id: UUID = Field(
        ...,
        description="User ID"
    )
    
    email: EmailStr = Field(
        ...,
        description="User email"
    )
    
    username: str = Field(
        ...,
        description="Username"
    )
    
    full_name: Optional[str] = Field(
        default=None,
        description="Full name"
    )
    
    is_active: bool = Field(
        ...,
        description="Whether user is active"
    )
    
    is_verified: bool = Field(
        ...,
        description="Whether user is verified"
    )
    
    is_superuser: bool = Field(
        ...,
        description="Whether user is superuser"
    )
    
    timezone: str = Field(
        ...,
        description="Timezone"
    )
    
    locale: str = Field(
        ...,
        description="Locale"
    )
    
    created_at: datetime = Field(
        ...,
        description="When user was created"
    )
    
    updated_at: datetime = Field(
        ...,
        description="When user was last updated"
    )
    
    last_login: Optional[datetime] = Field(
        default=None,
        description="Last login timestamp"
    )
    
    organizations: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="User organizations"
    )


class LoginRequestSchema(BaseModel):
    """Schema for login request"""
    
    username: str = Field(
        ...,
        description="Username or email"
    )
    
    password: SecretStr = Field(
        ...,
        description="Password"
    )
    
    remember_me: bool = Field(
        default=False,
        description="Remember me flag"
    )
    
    @validator("username")
    def validate_username(cls, v):
        """Validate username"""
        if not v or not v.strip():
            raise ValueError("Username cannot be empty")
        return v.strip()


class TokenCreateSchema(BaseModel):
    """Schema for token creation"""
    
    name: str = Field(
        ...,
        description="Token name",
        min_length=1,
        max_length=100,
        examples=["Production API", "Development Token", "CI/CD Pipeline"]
    )
    
    description: Optional[str] = Field(
        default=None,
        description="Token description"
    )
    
    expires_in_days: Optional[int] = Field(
        default=None,
        description="Token expiration in days",
        ge=1,
        le=365,
        examples=[7, 30, 90]
    )
    
    organization_id: Optional[UUID] = Field(
        default=None,
        description="Organization ID (for organization-scoped tokens)"
    )
    
    rate_limit_requests: Optional[int] = Field(
        default=100,
        description="Rate limit requests per period",
        ge=1,
        le=10000
    )
    
    rate_limit_period: Optional[int] = Field(
        default=60,
        description="Rate limit period in seconds",
        ge=1,
        le=3600
    )

    scopes: List[str] = Field(
        default_factory=lambda: ["telemetry:write"],
        description="Permissions granted to this API key",
        min_length=1,
    )
    
    @validator("scopes")
    def validate_scopes(cls, v):
        """Keep API-key permissions explicit and limited to known capabilities."""
        allowed = {"telemetry:write", "telemetry:read"}
        normalized = sorted({scope.strip().lower() for scope in v if scope.strip()})
        if not normalized or any(scope not in allowed for scope in normalized):
            raise ValueError("Unsupported API key scope")
        return normalized

    @validator("name")
    def validate_name(cls, v):
        """Validate token name"""
        if not v or not v.strip():
            raise ValueError("Token name cannot be empty")
        return v.strip()


class TokenRotateSchema(BaseModel):
    """Optional overrides used when rotating an API key."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = None
    expires_in_days: Optional[int] = Field(default=None, ge=1, le=365)
    scopes: Optional[List[str]] = Field(default=None, min_length=1)

    @validator("scopes")
    def validate_scopes(cls, v):
        if v is None:
            return v
        allowed = {"telemetry:write", "telemetry:read"}
        normalized = sorted({scope.strip().lower() for scope in v if scope.strip()})
        if not normalized or any(scope not in allowed for scope in normalized):
            raise ValueError("Unsupported API key scope")
        return normalized


class TokenResponseSchema(BaseModel):
    """Schema for token response"""
    
    token: str = Field(
        ...,
        description="Authentication token"
    )
    
    token_type: str = Field(
        ...,
        description="Token type"
    )
    
    name: str = Field(
        ...,
        description="Token name"
    )
    
    expires_at: Optional[datetime] = Field(
        default=None,
        description="Token expiration timestamp"
    )
    
    created_at: datetime = Field(
        ...,
        description="When token was created"
    )
    
    rate_limit_requests: int = Field(
        ...,
        description="Rate limit requests per period"
    )
    
    rate_limit_period: int = Field(
        ...,
        description="Rate limit period in seconds"
    )
    
    organization_id: Optional[UUID] = Field(
        default=None,
        description="Organization ID"
    )

    scopes: List[str] = Field(
        default_factory=lambda: ["telemetry:write"],
        description="Permissions granted to this API key",
    )
    
    warning: Optional[str] = Field(
        default=None,
        description="Security warning"
    )
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TokenValidationSchema(BaseModel):
    """Schema for token validation"""
    
    token: str = Field(
        ...,
        description="Token to validate"
    )
    
    organization_id: Optional[UUID] = Field(
        default=None,
        description="Organization ID to validate against"
    )
    
    @validator("token")
    def validate_token(cls, v):
        """Validate token"""
        if not v or not v.strip():
            raise ValueError("Token cannot be empty")
        return v.strip()


class TokenValidationResponseSchema(BaseModel):
    """Schema for token validation response"""
    
    valid: bool = Field(
        ...,
        description="Whether token is valid"
    )
    
    user_id: Optional[UUID] = Field(
        default=None,
        description="User ID (if valid)"
    )
    
    organization_id: Optional[UUID] = Field(
        default=None,
        description="Organization ID (if valid)"
    )
    
    token_type: Optional[str] = Field(
        default=None,
        description="Token type (if valid)"
    )
    
    expires_at: Optional[datetime] = Field(
        default=None,
        description="Token expiration (if valid)"
    )
    
    message: Optional[str] = Field(
        default=None,
        description="Validation message"
    )


class PasswordChangeSchema(BaseModel):
    """Schema for password change"""
    
    current_password: SecretStr = Field(
        ...,
        description="Current password"
    )
    
    new_password: SecretStr = Field(
        ...,
        description="New password"
    )
    
    @validator("new_password")
    def validate_new_password(cls, v, values):
        """Validate new password strength"""
        if "current_password" in values and v.get_secret_value() == values["current_password"].get_secret_value():
            raise ValueError("New password must be different from current password")
        
        return UserCreateSchema.validate_password_strength(v)


class AuthResponseSchema(BaseModel):
    """Schema for authentication response"""
    
    access_token: str = Field(
        ...,
        description="Access token"
    )
    
    refresh_token: str = Field(
        ...,
        description="Refresh token"
    )
    
    token_type: str = Field(
        default="bearer",
        description="Token type"
    )
    
    expires_in: int = Field(
        ...,
        description="Expiration in seconds"
    )
    
    user: UserResponseSchema = Field(
        ...,
        description="User information"
    )


class RateLimitSchema(BaseModel):
    """Schema for rate limiting"""
    
    key: str = Field(
        ...,
        description="Rate limit key"
    )
    
    limit: int = Field(
        ...,
        description="Request limit"
    )
    
    period: int = Field(
        ...,
        description="Time period in seconds"
    )
    
    remaining: int = Field(
        ...,
        description="Remaining requests"
    )
    
    reset_in: int = Field(
        ...,
        description="Seconds until reset"
    )


class OrganizationCreateSchema(BaseModel):
    """Schema for organization creation"""
    
    name: str = Field(
        ...,
        description="Organization name",
        min_length=3,
        max_length=255,
        examples=["Acme Corp", "Tech Solutions Inc", "Startup XYZ"]
    )
    
    slug: str = Field(
        ...,
        description="Organization slug",
        min_length=3,
        max_length=100,
        pattern="^[a-z0-9-]+$",
        examples=["acme-corp", "tech-solutions", "startup-xyz"]
    )
    
    description: Optional[str] = Field(
        default=None,
        description="Organization description"
    )
    
    email: Optional[EmailStr] = Field(
        default=None,
        description="Organization email"
    )
    
    website: Optional[str] = Field(
        default=None,
        description="Organization website"
    )
    
    timezone: str = Field(
        default="UTC",
        description="Timezone",
        max_length=50
    )
    
    locale: str = Field(
        default="en-US",
        description="Locale",
        max_length=10
    )
    
    @validator("slug")
    def validate_slug(cls, v):
        """Validate organization slug"""
        if not v or not v.strip():
            raise ValueError("Slug cannot be empty")
        
        # Check for reserved slugs
        reserved = ["admin", "api", "docs", "support", "status", "monitoring"]
        if v in reserved:
            raise ValueError(f"Slug '{v}' is reserved")
        
        return v.strip().lower()


class OrganizationResponseSchema(BaseModel):
    """Schema for organization response"""
    
    id: UUID = Field(
        ...,
        description="Organization ID"
    )
    
    name: str = Field(
        ...,
        description="Organization name"
    )
    
    slug: str = Field(
        ...,
        description="Organization slug"
    )
    
    description: Optional[str] = Field(
        default=None,
        description="Organization description"
    )
    
    is_active: bool = Field(
        ...,
        description="Whether organization is active"
    )
    
    subscription_tier: str = Field(
        ...,
        description="Subscription tier"
    )
    
    max_agents: int = Field(
        ...,
        description="Maximum number of agents"
    )
    
    max_events_per_day: int = Field(
        ...,
        description="Maximum events per day"
    )
    
    retention_days: int = Field(
        ...,
        description="Data retention in days"
    )
    
    created_at: datetime = Field(
        ...,
        description="When organization was created"
    )
    
    updated_at: datetime = Field(
        ...,
        description="When organization was last updated"
    )
    
    user_count: int = Field(
        ...,
        description="Number of users"
    )
    
    agent_count: int = Field(
        ...,
        description="Number of agents"
    )