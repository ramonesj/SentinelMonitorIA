"""
Configuration settings for SentinelMonitorIA Backend
Uses pydantic-settings for environment variable management
"""

import json
from typing import Optional, List
from enum import Enum
from pydantic import PostgresDsn, RedisDsn, validator
from pydantic_settings import BaseSettings


class Environment(str, Enum):
    """Application environments"""
    LOCAL = "local"
    DEVELOPMENT = "development"
    LOCAL_PRODUCTION = "local-production"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """Log levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    app_name: str = "SentinelMonitorIA"
    app_version: str = "1.0.0"
    app_description: str = "Observability and AIOps Platform"
    environment: Environment = Environment.LOCAL
    debug: bool = False
    log_level: LogLevel = LogLevel.INFO
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4
    api_reload: bool = True
    # Keep this as a string so pydantic-settings does not JSON-decode the
    # dotenv value before the application can normalize comma-separated input.
    api_cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def cors_origins(self) -> List[str]:
        """Return CORS origins from JSON or comma-separated configuration."""
        value = self.api_cors_origins.strip()
        if not value:
            return []

        try:
            origins = json.loads(value) if value.startswith("[") else value.split(",")
        except json.JSONDecodeError:
            origins = value.split(",")

        return [origin.strip() for origin in origins if isinstance(origin, str) and origin.strip()]
    
    # Security
    secret_key: str = "development-secret-key-change-in-production"
    jwt_secret_key: str = "development-jwt-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    
    # Database
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "sentinelmonitoria"
    postgres_user: str = "sentinel"
    postgres_password: str = "sentinel123"
    
    @property
    def database_url(self) -> str:
        """Build PostgreSQL DSN"""
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    @property
    def sync_database_url(self) -> str:
        """Build synchronous PostgreSQL DSN for migrations"""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    redis_db: int = 0
    redis_stream_prefix: str = "sentinel:stream"
    redis_stream_max_length: int = 10000
    redis_stream_consumer_group: str = "sentinel-telemetry-workers"
    telemetry_stale_batch_seconds: int = 3600
    redis_dead_letter_replay_key: str = "sentinel:stream:dead_letter:replayed"
    
    @property
    def redis_url(self) -> str:
        """Build Redis DSN"""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    # Telemetry Processing
    telemetry_batch_size: int = 1000
    telemetry_buffer_size: int = 10000
    telemetry_flush_interval: int = 5  # seconds
    
    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_period: int = 60  # seconds
    rate_limit_organization_requests: int = 1000
    
    # Queue Configuration
    queue_provider: str = "mock"  # mock, sqs, redis
    mock_queue_max_size: int = 10000
    ai_analysis_consumer_group: str = "sentinel-ai-analysis-workers"
    notification_consumer_group: str = "sentinel-notification-workers"

    # Intelligence and RAG
    ai_provider: str = "rules"  # rules, ollama, bedrock
    ai_model_id: Optional[str] = None
    ai_model_name: str = "llama3.2"
    ai_ollama_base_url: str = "http://localhost:11434"
    ai_knowledge_base_id: Optional[str] = None
    ai_log_archive_bucket: Optional[str] = None
    ai_temperature: float = 0.2
    ai_max_output_tokens: int = 500
    ai_max_findings: int = 20
    ai_request_timeout_seconds: int = 30
    ai_enable_actions: bool = False
    anomaly_cpu_threshold: float = 90.0
    anomaly_memory_threshold: float = 90.0

    # Chatbot conversation
    chat_provider: str = "rules"  # rules now; lex_bedrock is a future AWS adapter
    chat_context_alert_limit: int = 20
    chat_max_message_length: int = 2000
    chat_enable_actions: bool = False

    # Notifications
    notification_channels: str = "log"
    notification_webhook_url: Optional[str] = None
    notification_webhook_secret: Optional[str] = None
    notification_slack_webhook_url: Optional[str] = None
    notification_discord_webhook_url: Optional[str] = None
    notification_teams_webhook_url: Optional[str] = None
    notification_email_to: Optional[str] = None
    notification_request_timeout_seconds: int = 15
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_email: Optional[str] = None
    smtp_use_tls: bool = True
    alert_websocket_poll_seconds: int = 2

    @property
    def notification_channel_list(self) -> List[str]:
        """Return normalized notification channels without empty values."""
        return [
            channel.strip().lower()
            for channel in self.notification_channels.split(",")
            if channel.strip()
        ] or ["log"]

    # AWS Configuration
    aws_region: Optional[str] = None
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_session_token: Optional[str] = None
    
    # SQS Configuration (reserved for a future managed queue provider)
    sqs_telemetry_queue_url: Optional[str] = None
    sqs_alerts_queue_url: Optional[str] = None
    sqs_dead_letter_queue_url: Optional[str] = None
    
    # Health Checks
    health_check_timeout: int = 5  # seconds
    health_check_retries: int = 3
    
    # Validation
    @validator("environment", pre=True)
    def validate_environment(cls, v):
        if isinstance(v, str):
            v = v.lower()
            if v not in [e.value for e in Environment]:
                raise ValueError(f"Invalid environment: {v}")
        return v
    
    @validator("debug")
    def validate_debug(cls, v, values):
        if values.get("environment") in [Environment.PRODUCTION, Environment.LOCAL_PRODUCTION] and v:
            raise ValueError("Debug mode should be disabled in production-like environments")
        return v

    @validator("api_reload")
    def validate_reload(cls, v, values):
        if values.get("environment") in [Environment.PRODUCTION, Environment.LOCAL_PRODUCTION] and v:
            raise ValueError("API reload must be disabled in production-like environments")
        return v

    @validator("secret_key", "jwt_secret_key")
    def validate_secret(cls, v, values):
        environment = values.get("environment")
        insecure_values = {
            "development-secret-key-change-in-production",
            "development-jwt-secret-change-in-production",
            "change-me",
            "changeme",
        }
        if environment in [Environment.PRODUCTION, Environment.LOCAL_PRODUCTION]:
            if not v or v in insecure_values or len(v) < 32:
                raise ValueError("Strong SECRET_KEY and JWT_SECRET_KEY values are required")
        return v

    @validator("redis_password")
    def validate_redis_password(cls, v, values):
        if values.get("environment") in [Environment.PRODUCTION, Environment.LOCAL_PRODUCTION] and not v:
            raise ValueError("REDIS_PASSWORD is required in production-like environments")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
