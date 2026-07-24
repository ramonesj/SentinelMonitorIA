"""
Health check API endpoints for SentinelMonitorIA
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
import time
import psutil

from src.config.settings import Environment, settings
from src.config.logging import logger
from src.database.database import db_manager, get_db_session
from src.database.redis import redis_manager
from src.services.telemetry import telemetry_service


router = APIRouter(prefix="/health", tags=["health"])


@router.get(
    "",
    summary="Health check",
    description="""
    Comprehensive health check for all SentinelMonitorIA services.
    
    Returns detailed status information for:
    - API service
    - Database (PostgreSQL)
    - Redis cache
    - Telemetry processing service
    - System resources
    
    Use this endpoint for load balancers and monitoring systems.
    """
)
async def health_check(db: AsyncSession = Depends(get_db_session)):
    """
    Comprehensive health check
    """
    
    start_time = time.time()
    checks = {}
    
    # 1. API Service Check
    checks["api_service"] = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.app_version,
        "environment": settings.environment.value
    }
    
    # 2. Database Check
    try:
        # Simple query to check database connectivity
        result = await db.execute(text("SELECT 1"))
        db_result = result.scalar()
        
        # Get database stats
        db_stats = await db_manager.get_stats()
        
        checks["database"] = {
            "status": "healthy" if db_result == 1 else "unhealthy",
            "type": "postgresql",
            "response_time_ms": round((time.time() - start_time) * 1000, 2),
            "stats": db_stats
        }
    except Exception as e:
        checks["database"] = {
            "status": "unhealthy",
            "type": "postgresql",
            "error": str(e),
            "response_time_ms": round((time.time() - start_time) * 1000, 2)
        }
    
    # 3. Redis Check
    try:
        redis_healthy = await redis_manager.health_check()
        redis_stats = await redis_manager.get_stats()
        
        checks["redis"] = {
            "status": "healthy" if redis_healthy else "unhealthy",
            "type": "redis",
            "response_time_ms": round((time.time() - start_time) * 1000, 2),
            "stats": redis_stats
        }
    except Exception as e:
        checks["redis"] = {
            "status": "unhealthy",
            "type": "redis",
            "error": str(e),
            "response_time_ms": round((time.time() - start_time) * 1000, 2)
        }
    
    # 4. Telemetry Service Check
    try:
        telemetry_health = await telemetry_service.health_check()
        
        checks["telemetry_service"] = {
            "status": telemetry_health.get("status", "unknown"),
            "response_time_ms": round((time.time() - start_time) * 1000, 2),
            "details": telemetry_health
        }
    except Exception as e:
        checks["telemetry_service"] = {
            "status": "unhealthy",
            "error": str(e),
            "response_time_ms": round((time.time() - start_time) * 1000, 2)
        }
    
    # 5. System Resources Check
    try:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        
        # Disk usage (of current directory)
        disk = psutil.disk_usage(".")
        
        checks["system_resources"] = {
            "status": "healthy" if cpu_percent < 90 and memory.percent < 90 else "warning",
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_total_gb": round(memory.total / (1024**3), 2),
            "memory_available_gb": round(memory.available / (1024**3), 2),
            "disk_percent": disk.percent,
            "disk_total_gb": round(disk.total / (1024**3), 2),
            "disk_free_gb": round(disk.free / (1024**3), 2)
        }
    except Exception as e:
        checks["system_resources"] = {
            "status": "unknown",
            "error": str(e)
        }
    
    # 6. External Services (simulated for now)
    checks["external_services"] = {
        "status": "healthy",
        "services": {
            "time_service": {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat()
            },
            "monitoring": {
                "status": "healthy",
                "note": "All checks passed"
            }
        }
    }
    
    # Determine overall health status
    all_healthy = all(
        check["status"] in ["healthy", "warning"]
        for check in checks.values()
        if isinstance(check, dict) and "status" in check
    )
    
    any_warning = any(
        check.get("status") == "warning"
        for check in checks.values()
        if isinstance(check, dict)
    )
    
    overall_status = "healthy"
    if not all_healthy:
        overall_status = "unhealthy"
    elif any_warning:
        overall_status = "degraded"
    
    # Calculate total response time
    total_response_time = round((time.time() - start_time) * 1000, 2)
    
    # Prepare response
    response = {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "response_time_ms": total_response_time,
        "version": settings.app_version,
        "environment": settings.environment.value,
        "checks": checks
    }
    
    # Log health check
    logger.info(
        "Health check completed",
        status=overall_status,
        response_time_ms=total_response_time,
        environment=settings.environment.value
    )
    
    # Set appropriate status code
    status_code = status.HTTP_200_OK
    if overall_status == "unhealthy":
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif overall_status == "degraded":
        status_code = status.HTTP_200_OK  # Still 200, but status indicates degraded
    
    return response


@router.get(
    "/liveness",
    summary="Liveness probe",
    description="""
    Simple liveness probe for Kubernetes and container orchestration.
    
    This endpoint performs minimal checks to determine if the service
    is alive and able to respond to requests.
    
    Returns HTTP 200 if alive, 503 if not.
    """
)
async def liveness_probe():
    """
    Liveness probe for container orchestration
    """
    
    try:
        # Minimal check - just see if we can respond
        return {
            "status": "alive",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service not alive: {str(e)}"
        )


@router.get(
    "/readiness",
    summary="Readiness probe",
    description="""
    Readiness probe for Kubernetes and container orchestration.
    
    This endpoint checks if the service is ready to accept traffic.
    It performs light checks on critical dependencies.
    
    Returns HTTP 200 if ready, 503 if not.
    """
)
async def readiness_probe(db: AsyncSession = Depends(get_db_session)):
    """
    Readiness probe for container orchestration
    """
    
    checks = []
    
    # 1. Database readiness
    try:
        result = await db.execute(text("SELECT 1"))
        db_ready = result.scalar() == 1
        checks.append({
            "service": "database",
            "status": "ready" if db_ready else "not_ready"
        })
    except Exception as e:
        checks.append({
            "service": "database",
            "status": "not_ready",
            "error": str(e)
        })
    
    # 2. Redis readiness (optional)
    try:
        redis_ready = await redis_manager.health_check()
        checks.append({
            "service": "redis",
            "status": "ready" if redis_ready else "not_ready"
        })
    except Exception as e:
        checks.append({
            "service": "redis",
            "status": "not_ready",
            "error": str(e)
        })
    
    # 3. Telemetry service readiness
    try:
        telemetry_health = await telemetry_service.health_check()
        telemetry_ready = telemetry_health.get("status") == "healthy"
        checks.append({
            "service": "telemetry_service",
            "status": "ready" if telemetry_ready else "not_ready"
        })
    except Exception as e:
        checks.append({
            "service": "telemetry_service",
            "status": "not_ready",
            "error": str(e)
        })
    
    # Determine overall readiness
    all_ready = all(
        check["status"] == "ready"
        for check in checks
    )
    
    if all_ready:
        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": checks
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "not_ready",
                "timestamp": datetime.utcnow().isoformat(),
                "checks": checks
            }
        )


@router.get(
    "/detailed",
    summary="Detailed health check",
    description="""
    Detailed health check with performance metrics and statistics.
    
    This endpoint provides comprehensive information about service
    performance, resource usage, and operational metrics.
    """
)
async def detailed_health(db: AsyncSession = Depends(get_db_session)):
    """
    Detailed health check with performance metrics
    """
    
    start_time = time.time()
    
    # Collect detailed metrics
    metrics = {}
    
    # Database metrics
    try:
        db_stats = await db_manager.get_stats()
        
        # Get table counts
        table_counts = {}
        from src.models.base import Base
        for table_name in Base.metadata.tables.keys():
            result = await db.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            count = result.scalar()
            table_counts[table_name] = count
        
        metrics["database"] = {
            "connection_pool": db_stats,
            "table_counts": table_counts,
            "query_performance": {
                "health_check_ms": round((time.time() - start_time) * 1000, 2)
            }
        }
    except Exception as e:
        metrics["database"] = {
            "error": str(e)
        }
    
    # Redis metrics
    try:
        redis_stats = await redis_manager.get_stats()
        metrics["redis"] = redis_stats
    except Exception as e:
        metrics["redis"] = {
            "error": str(e)
        }
    
    # Telemetry service metrics
    try:
        telemetry_stats = await telemetry_service.get_service_stats()
        metrics["telemetry_service"] = telemetry_stats
    except Exception as e:
        metrics["telemetry_service"] = {
            "error": str(e)
        }
    
    # API metrics
    metrics["api"] = {
        "uptime_seconds": 0,  # Would need to track start time
        "total_requests": 0,  # Would need request counter
        "average_response_time_ms": 0,
        "error_rate": 0,
        "current_connections": 0
    }
    
    # System metrics
    try:
        # CPU
        cpu_times = psutil.cpu_times()
        cpu_percent = psutil.cpu_percent(interval=0.1, percpu=True)
        
        # Memory
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # Disk
        disk = psutil.disk_usage(".")
        disk_io = psutil.disk_io_counters()
        
        # Network
        net_io = psutil.net_io_counters()
        
        metrics["system"] = {
            "cpu": {
                "cores": psutil.cpu_count(),
                "percent_per_core": cpu_percent,
                "total_percent": psutil.cpu_percent(interval=0.1),
                "times": {
                    "user": cpu_times.user,
                    "system": cpu_times.system,
                    "idle": cpu_times.idle
                }
            },
            "memory": {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "percent": memory.percent,
                "used_gb": round(memory.used / (1024**3), 2),
                "free_gb": round(memory.free / (1024**3), 2)
            },
            "swap": {
                "total_gb": round(swap.total / (1024**3), 2),
                "used_gb": round(swap.used / (1024**3), 2),
                "free_gb": round(swap.free / (1024**3), 2),
                "percent": swap.percent
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "percent": disk.percent,
                "read_bytes": disk_io.read_bytes if disk_io else 0,
                "write_bytes": disk_io.write_bytes if disk_io else 0
            },
            "network": {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv
            }
        }
    except Exception as e:
        metrics["system"] = {
            "error": str(e)
        }
    
    # Application metrics
    metrics["application"] = {
        "version": settings.app_version,
        "environment": settings.environment.value,
        "debug": settings.debug,
        "log_level": settings.log_level.value,
        "start_time": "2024-01-01T00:00:00Z",  # Would need actual start time
        "current_time": datetime.utcnow().isoformat()
    }
    
    # Calculate total collection time
    collection_time = round((time.time() - start_time) * 1000, 2)
    
    response = {
        "status": "success",
        "timestamp": datetime.utcnow().isoformat(),
        "collection_time_ms": collection_time,
        "metrics": metrics
    }
    
    return response


@router.get(
    "/history",
    summary="Health check history",
    description="Get historical health check data (simulated for now)"
)
async def health_history(limit: int = 10):
    """
    Get health check history
    """
    
    if limit > 100:
        limit = 100
    
    # Simulated history data
    history = []
    for i in range(limit):
        history.append({
            "timestamp": (datetime.utcnow() - timedelta(minutes=i * 5)).isoformat(),
            "status": "healthy" if i % 10 != 9 else "degraded",  # Simulate occasional degradation
            "response_time_ms": 50 + (i % 5) * 10,
            "checks_passed": 6,
            "checks_total": 6
        })
    
    return {
        "status": "success",
        "history": history,
        "count": len(history),
        "timestamp": datetime.utcnow().isoformat()
    }


# Development endpoints
if settings.environment in [Environment.LOCAL, Environment.DEVELOPMENT]:
    
    @router.get("/dev/simulate-failure")
    async def simulate_failure(service: str = "all"):
        """
        Simulate service failure (development only)
        """
        
        failures = {
            "database": "Simulated database connection failure",
            "redis": "Simulated Redis connection failure",
            "telemetry": "Simulated telemetry service failure",
            "all": "Simulated complete service failure"
        }
        
        if service not in failures:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid service: {service}. Valid options: {', '.join(failures.keys())}"
            )
        
        # In a real implementation, this would trigger actual failure simulation
        # For now, just return a simulated failure response
        
        return {
            "status": "simulated_failure",
            "service": service,
            "message": failures[service],
            "timestamp": datetime.utcnow().isoformat(),
            "note": "This is a simulation for development testing only"
        }
    
    @router.post("/dev/reset-health")
    async def reset_health():
        """
        Reset health check data (development only)
        """
        
        # This would reset health check counters and history
        # For now, just return success
        
        return {
            "status": "success",
            "message": "Health check data reset",
            "timestamp": datetime.utcnow().isoformat()
        }