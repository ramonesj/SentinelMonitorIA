"""
SentinelMonitorIA FastAPI Application
Main entry point for the backend API
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import time
from typing import Dict, Any

from src.config.settings import Environment, settings
from src.config.logging import configure_logging, logger
from src.database.database import db_manager
from src.database.redis import redis_manager
from src.services.auth import auth_service
from src.services.telemetry import telemetry_service
from src.api.v1 import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application
    Handles startup and shutdown events
    """
    
    # Startup
    logger.info("Starting SentinelMonitorIA API")
    
    # Configure logging
    configure_logging()
    
    # Initialize database
    try:
        await db_manager.initialize()
        logger.info("Database initialized")
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise
    
    # Initialize Redis
    try:
        await redis_manager.initialize()
        logger.info("Redis initialized")
    except Exception as e:
        logger.error("Failed to initialize Redis", error=str(e))
        # Redis is optional for some features, don't crash if it fails
    
    # Start telemetry service
    try:
        await telemetry_service.start()
        logger.info("Telemetry service started")
    except Exception as e:
        logger.error("Failed to start telemetry service", error=str(e))
        # Telemetry service is important but not critical for API to start
    
    # Create database tables (for development)
    if settings.environment in [Environment.LOCAL, Environment.DEVELOPMENT]:
        try:
            await db_manager.create_tables()
            logger.info("Database tables created")
        except Exception as e:
            logger.warning("Failed to create database tables", error=str(e))

        try:
            async for db in db_manager.get_session():
                migrated_keys = await auth_service.migrate_legacy_api_keys(db)
                logger.info(
                    "API key storage migration checked",
                    migrated_keys=migrated_keys,
                )
                break
        except Exception as e:
            logger.warning("Failed to migrate legacy API keys", error=str(e))
    
    # Health check
    try:
        db_healthy = await db_manager.health_check()
        redis_healthy = await redis_manager.health_check()
        
        logger.info(
            "Startup health check",
            database=db_healthy,
            redis=redis_healthy
        )
    except Exception as e:
        logger.error("Startup health check failed", error=str(e))
    
    yield
    
    # Shutdown
    logger.info("Shutting down SentinelMonitorIA API")
    
    # Stop telemetry service
    try:
        await telemetry_service.stop()
        logger.info("Telemetry service stopped")
    except Exception as e:
        logger.error("Failed to stop telemetry service", error=str(e))
    
    # Close Redis connection
    try:
        await redis_manager.close()
        logger.info("Redis connection closed")
    except Exception as e:
        logger.error("Failed to close Redis connection", error=str(e))
    
    # Close database connections
    try:
        await db_manager.close()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error("Failed to close database connections", error=str(e))
    
    logger.info("Shutdown complete")


# Keep interactive API documentation available in staging while retaining the production default.
docs_enabled = settings.debug or settings.environment == Environment.STAGING


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
    docs_url="/api/v1/docs" if docs_enabled else None,
    redoc_url="/api/v1/redoc" if docs_enabled else None,
    openapi_url="/api/v1/openapi.json" if docs_enabled else None,
    lifespan=lifespan
)


# CORS middleware
if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"]
    )


# Global exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    logger.warning(
        "Request validation error",
        path=request.url.path,
        errors=exc.errors(),
        client=request.client.host if request.client else "unknown"
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status": "error",
            "message": "Validation error",
            "errors": jsonable_encoder(exc.errors()),
            "path": request.url.path
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    logger.warning(
        "HTTP exception",
        path=request.url.path,
        status_code=exc.status_code,
        detail=exc.detail,
        client=request.client.host if request.client else "unknown"
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.detail,
            "path": request.url.path
        },
        headers=exc.headers if hasattr(exc, "headers") else {}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(
        "Unhandled exception",
        path=request.url.path,
        error=str(exc),
        client=request.client.host if request.client else "unknown",
        exc_info=True
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "message": "Internal server error",
            "path": request.url.path
        }
    )


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests"""
    start_time = time.time()
    
    # Get request details
    client_ip = request.client.host if request.client else "unknown"
    method = request.method
    path = request.url.path
    query_params = str(request.query_params)
    
    # Log request
    logger.info(
        "Request started",
        method=method,
        path=path,
        client_ip=client_ip,
        query_params=query_params if query_params != "" else None
    )
    
    # Process request
    response = await call_next(request)
    
    # Calculate processing time
    process_time = time.time() - start_time
    
    # Log response
    logger.info(
        "Request completed",
        method=method,
        path=path,
        status_code=response.status_code,
        process_time_ms=round(process_time * 1000, 2),
        client_ip=client_ip
    )
    
    # Add processing time header
    response.headers["X-Process-Time"] = str(process_time)
    
    return response


# Include API routers
app.include_router(api_router, prefix="/api/v1")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "description": settings.app_description,
        "environment": settings.environment.value,
        "documentation": "/api/v1/docs" if docs_enabled else None,
        "health": "/api/v1/health",
        "metrics": "/api/v1/metrics"
    }


# Health check endpoint
@app.get("/health")
async def health():
    """Health check endpoint"""
    # Check database health
    db_healthy = await db_manager.health_check()
    
    # Check Redis health
    redis_healthy = await redis_manager.health_check()
    
    # Check telemetry service health
    telemetry_health = await telemetry_service.health_check()
    
    # Overall health status
    overall_healthy = db_healthy and redis_healthy and telemetry_health.get("status") == "healthy"
    
    status_code = status.HTTP_200_OK if overall_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    
    response = {
        "status": "healthy" if overall_healthy else "unhealthy",
        "timestamp": time.time(),
        "services": {
            "database": {
                "healthy": db_healthy,
                "type": "postgresql"
            },
            "redis": {
                "healthy": redis_healthy,
                "type": "redis"
            },
            "telemetry_service": telemetry_health
        },
        "environment": settings.environment.value,
        "version": settings.app_version
    }
    
    return JSONResponse(
        content=jsonable_encoder(response),
        status_code=status_code
    )


# Metrics endpoint (Prometheus format)
@app.get("/metrics")
async def metrics():
    """Metrics endpoint in Prometheus format"""
    
    # Get database stats
    db_stats = await db_manager.get_stats()
    
    # Get Redis stats
    redis_stats = await redis_manager.get_stats()
    
    # Get telemetry service stats
    telemetry_stats = await telemetry_service.get_service_stats()
    
    # Format as Prometheus metrics
    metrics_lines = []
    
    # Application metrics
    metrics_lines.append("# HELP sentinel_api_info Application information")
    metrics_lines.append("# TYPE sentinel_api_info gauge")
    metrics_lines.append(f'sentinel_api_info{{version="{settings.app_version}", environment="{settings.environment.value}"}} 1')
    
    # Database metrics
    if "pool_size" in db_stats:
        metrics_lines.append("# HELP sentinel_db_connections Database connections")
        metrics_lines.append("# TYPE sentinel_db_connections gauge")
        metrics_lines.append(f"sentinel_db_connections{{type=\"total\"}} {db_stats.get('pool_size', 0)}")
        metrics_lines.append(f"sentinel_db_connections{{type=\"checked_out\"}} {db_stats.get('checked_out', 0)}")
        metrics_lines.append(f"sentinel_db_connections{{type=\"checked_in\"}} {db_stats.get('checked_in', 0)}")
        metrics_lines.append(f"sentinel_db_connections{{type=\"overflow\"}} {db_stats.get('overflow', 0)}")
    
    # Redis metrics
    if "connected_clients" in redis_stats:
        metrics_lines.append("# HELP sentinel_redis_connections Redis connections")
        metrics_lines.append("# TYPE sentinel_redis_connections gauge")
        metrics_lines.append(f"sentinel_redis_connections {redis_stats.get('connected_clients', 0)}")
    
    # Telemetry service metrics
    telemetry_service_stats = telemetry_stats.get("telemetry_service", {})
    if "batches_received" in telemetry_service_stats:
        metrics_lines.append("# HELP sentinel_telemetry_batches_received Total telemetry batches received")
        metrics_lines.append("# TYPE sentinel_telemetry_batches_received counter")
        metrics_lines.append(f"sentinel_telemetry_batches_received {telemetry_service_stats.get('batches_received', 0)}")
        
        metrics_lines.append("# HELP sentinel_telemetry_events_processed Total telemetry events processed")
        metrics_lines.append("# TYPE sentinel_telemetry_events_processed counter")
        metrics_lines.append(f"sentinel_telemetry_events_processed {telemetry_service_stats.get('events_processed', 0)}")
        
        metrics_lines.append("# HELP sentinel_telemetry_processing_time_ms Average processing time in milliseconds")
        metrics_lines.append("# TYPE sentinel_telemetry_processing_time_ms gauge")
        metrics_lines.append(f"sentinel_telemetry_processing_time_ms {telemetry_service_stats.get('avg_processing_time_ms', 0)}")
        
        metrics_lines.append("# HELP sentinel_telemetry_success_rate Telemetry processing success rate")
        metrics_lines.append("# TYPE sentinel_telemetry_success_rate gauge")
        metrics_lines.append(f"sentinel_telemetry_success_rate {telemetry_service_stats.get('success_rate', 0)}")
    
    # Queue metrics
    queue_stats = telemetry_stats.get("queue_producer", {})
    if "messages_sent" in queue_stats:
        metrics_lines.append("# HELP sentinel_queue_messages_sent Total messages sent to queue")
        metrics_lines.append("# TYPE sentinel_queue_messages_sent counter")
        metrics_lines.append(f"sentinel_queue_messages_sent {queue_stats.get('messages_sent', 0)}")
        
        metrics_lines.append("# HELP sentinel_queue_messages_processed Total messages processed from queue")
        metrics_lines.append("# TYPE sentinel_queue_messages_processed counter")
        metrics_lines.append(f"sentinel_queue_messages_processed {queue_stats.get('messages_processed', 0)}")
        
        metrics_lines.append("# HELP sentinel_queue_messages_failed Total messages failed processing")
        metrics_lines.append("# TYPE sentinel_queue_messages_failed counter")
        metrics_lines.append(f"sentinel_queue_messages_failed {queue_stats.get('messages_failed', 0)}")
    
    # Queue depths
    queue_depths = queue_stats.get("current_queue_depths", {})
    for queue_name, depth in queue_depths.items():
        metrics_lines.append(f"# HELP sentinel_queue_depth_current Current depth of {queue_name} queue")
        metrics_lines.append(f"# TYPE sentinel_queue_depth_current gauge")
        metrics_lines.append(f'sentinel_queue_depth_current{{queue="{queue_name}"}} {depth}')
    
    return "\n".join(metrics_lines)


# Development endpoints
if settings.environment in [Environment.LOCAL, Environment.DEVELOPMENT]:
    
    @app.get("/dev/stats")
    async def dev_stats():
        """Development statistics endpoint"""
        return {
            "database": await db_manager.get_stats(),
            "redis": await redis_manager.get_stats(),
            "telemetry_service": await telemetry_service.get_service_stats(),
            "settings": {
                "environment": settings.environment.value,
                "debug": settings.debug,
                "log_level": settings.log_level.value,
                "api_host": settings.api_host,
                "api_port": settings.api_port,
            }
        }
    
    @app.post("/dev/reset")
    async def dev_reset():
        """Reset development data (use with caution)"""
        # Clear database (for development only)
        await db_manager.drop_tables()
        await db_manager.create_tables()
        
        # Clear Redis
        await redis_manager.flushdb()
        
        # Clear telemetry service queues
        from src.services.telemetry import QueueType
        for queue_type in QueueType:
            await telemetry_service.queue_producer.clear_queue(queue_type)
        
        return {"status": "reset", "message": "Development data cleared"}
    
    @app.get("/dev/test-auth")
    async def dev_test_auth():
        """Test authentication endpoint for development"""
        return {
            "message": "Authentication test endpoint",
            "test_token": "test_development_token_12345",
            "note": "Use this token for testing API endpoints"
        }


if __name__ == "__main__":
    import uvicorn
    
    logger.info(
        "Starting SentinelMonitorIA API server",
        host=settings.api_host,
        port=settings.api_port,
        environment=settings.environment.value,
        debug=settings.debug
    )
    
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        workers=settings.api_workers,
        log_level=settings.log_level.value
    )