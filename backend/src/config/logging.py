"""
Structured logging configuration for SentinelMonitorIA
Uses structlog for JSON logging in production
"""

import logging
import sys
from typing import Dict, Any
from loguru import logger as loguru_logger
import structlog
from src.config.settings import Environment, settings


def configure_logging() -> None:
    """Configure application logging"""
    
    # Remove default handlers
    logging.getLogger().handlers.clear()
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if settings.environment == Environment.PRODUCTION
            else structlog.dev.ConsoleRenderer()
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure loguru for async context
    loguru_logger.remove()
    
    # Console logging configuration
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    if settings.environment == Environment.PRODUCTION:
        log_format = (
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level: <8} | "
            "{name}:{function}:{line} | "
            "{message}"
        )
    
    loguru_logger.add(
        sys.stdout,
        format=log_format,
        level=settings.log_level.upper(),
        colorize=settings.environment != Environment.PRODUCTION
    )
    
    # File logging for production
    if settings.environment == Environment.PRODUCTION:
        loguru_logger.add(
            "logs/app_{time:YYYY-MM-DD}.log",
            rotation="00:00",
            retention="30 days",
            compression="gz",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
            level="INFO",
            enqueue=True
        )
        
        loguru_logger.add(
            "logs/error_{time:YYYY-MM-DD}.log",
            rotation="00:00",
            retention="90 days",
            compression="gz",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
            level="ERROR",
            enqueue=True
        )
    
    # Set third-party loggers
    logging.getLogger("uvicorn.access").handlers = []
    logging.getLogger("uvicorn.error").handlers = []
    
    # Configure SQLAlchemy logging
    sqlalchemy_logger = logging.getLogger("sqlalchemy.engine")
    if settings.debug:
        sqlalchemy_logger.setLevel(logging.INFO)
    else:
        sqlalchemy_logger.setLevel(logging.WARNING)


def get_logger(name: str = "sentinelmonitoria") -> structlog.stdlib.BoundLogger:
    """Get a configured logger instance"""
    return structlog.get_logger(name)


# Application logger
logger = get_logger()


# Context processor for adding common fields
def add_context(**kwargs: Dict[str, Any]) -> structlog.stdlib.BoundLogger:
    """Add context to logger"""
    return logger.bind(**kwargs)