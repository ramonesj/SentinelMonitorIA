"""
Telemetry API endpoints for SentinelMonitorIA
Handles telemetry ingestion from agents
"""

from datetime import datetime
import inspect
from typing import Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import Environment, settings
from src.config.logging import logger
from src.database.database import get_db_session
from src.api.v1.auth import get_current_user_record
from src.services.auth import auth_service
from src.schemas.telemetry import (
    TelemetryBatchSchema,
    TelemetryResponseSchema,
    TelemetryHealthSchema
)
from src.services.telemetry import telemetry_service
from src.services.rate_limiter import rate_limiter


router = APIRouter(prefix="/telemetry", tags=["telemetry"])
security = HTTPBearer()


@router.post(
    "",
    response_model=TelemetryResponseSchema,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest telemetry batch",
    description="""
    Receive telemetry data from SentinelMonitorIA agents.
    
    This endpoint accepts batches of metrics, logs, and events.
    Data is validated, rate-limited, and queued for async processing.
    
    Authentication is required via API token or JWT token.
    """
)
async def ingest_telemetry(
    request: Request,
    batch_data: TelemetryBatchSchema,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Ingest telemetry batch from agent
    """
    
    # Get request information
    ip_address = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    # Extract token
    token = credentials.credentials
    
    try:
        # Validate the persisted JWT API key and resolve its organization.
        user, organization, token_obj = await auth_service.validate_api_token(
            db,
            token,
            required_scope="telemetry:write",
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        # Check if organization is required
        organization_id = None
        if token_obj.organization_id:
            organization_id = token_obj.organization_id
        elif organization:
            organization_id = organization.id
        
        if not organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization ID required for telemetry ingestion"
            )
        
        # Get agent ID from metadata
        agent_id_str = batch_data.metadata.agent_id
        
        # Find or create agent
        # For now, we'll use a placeholder - in production, you'd look up the agent
        from src.models.organization import Agent
        from sqlalchemy import select
        
        agent = await db.execute(
            select(Agent).where(
                (Agent.agent_id == agent_id_str) &
                (Agent.organization_id == organization_id)
            )
        )
        agent = agent.scalar_one_or_none()
        
        if not agent:
            # Create new agent
            agent = Agent(
                organization_id=organization_id,
                agent_id=agent_id_str,
                name=f"Agent: {batch_data.metadata.hostname}",
                hostname=batch_data.metadata.hostname,
                agent_version=batch_data.metadata.agent_version,
                platform=batch_data.metadata.platform or "unknown",
                architecture=batch_data.metadata.architecture or "unknown",
                configuration={},
                tags=batch_data.metadata.tags
            )
            db.add(agent)
            await db.flush()
        
        # Check rate limits
        rate_limit_info = await rate_limiter.enforce_rate_limit(
            ip_address=ip_address,
            organization_id=organization_id,
            token_id=token_obj.id,
            token_limit=token_obj.rate_limit_requests,
            token_period=token_obj.rate_limit_period,
            agent_id=agent_id_str,
            endpoint="/api/v1/telemetry"
        )
        
        # Process telemetry batch
        response = await telemetry_service.process_telemetry_batch(
            db=db,
            batch_data=batch_data,
            organization_id=organization_id,
            agent_id=agent.id,
            token_id=token_obj.id
        )
        
        # Update agent metrics
        total_items = len(batch_data.metrics) + len(batch_data.logs) + len(batch_data.events)
        agent.total_events_sent += total_items
        agent.last_seen_at = response.received_at
        
        await db.commit()
        
        # Log successful ingestion
        logger.info(
            "Telemetry batch ingested successfully",
            batch_id=response.batch_id,
            organization_id=str(organization_id),
            agent_id=str(agent.id),
            total_items=total_items,
            processing_time_ms=response.latency_ms or 0,
            client_ip=ip_address
        )
        
        # Add rate limit headers
        headers = rate_limiter.create_rate_limit_headers(rate_limit_info, "token")
        
        return JSONResponse(
            content=jsonable_encoder(response),
            status_code=status.HTTP_202_ACCEPTED,
            headers=headers
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Telemetry ingestion failed",
            error=str(e),
            client_ip=ip_address,
            user_agent=user_agent
        )
        
        # Create error response
        error_response = TelemetryResponseSchema(
            status="error",
            message=f"Failed to process telemetry batch: {str(e)}",
            batch_id=batch_data.batch_id or "unknown",
            received_at=datetime.utcnow(),
            processed_items={
                "metrics": 0,
                "logs": 0,
                "events": 0
            },
            errors=[str(e)],
            latency_ms=0
        )
        
        return JSONResponse(
            content=jsonable_encoder(error_response),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get(
    "/health",
    response_model=TelemetryHealthSchema,
    summary="Telemetry service health check",
    description="Check the health and status of the telemetry ingestion service"
)
async def telemetry_health():
    """
    Get telemetry service health status
    """
    
    health_info = await telemetry_service.health_check()
    
    return TelemetryHealthSchema(
        status=health_info["status"],
        timestamp=datetime.fromisoformat(health_info["timestamp"]),
        uptime_seconds=0,  # Would need to track service start time
        version="1.0.0",
        metrics=health_info.get("stats", {})
    )


@router.get(
    "/stats",
    summary="Telemetry service statistics",
    description="Get statistics about telemetry processing"
)
async def telemetry_stats():
    """
    Get telemetry service statistics
    """
    
    stats = await telemetry_service.get_service_stats()
    
    return {
        "status": "success",
        "timestamp": datetime.utcnow().isoformat(),
        "stats": stats
    }


@router.get(
    "/queues",
    summary="Queue status",
    description="Get status of processing queues",
    dependencies=[Depends(get_current_user_record)]  # Require an access JWT
)
async def queue_status():
    """Get provider-neutral queue status information."""
    return await telemetry_service.get_queue_status()


@router.get(
    "/dead-letter",
    summary="Inspect dead-letter entries",
    description="List retained Redis dead-letter entries without deleting them",
    dependencies=[Depends(get_current_user_record)],
)
async def dead_letter_status(limit: int = 50):
    """Inspect retained dead-letter entries with an authenticated access JWT."""
    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="limit must be between 1 and 100",
        )
    try:
        return await telemetry_service.get_dead_letters(limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post(
    "/dead-letter/{stream_id}/replay",
    summary="Replay a dead-letter entry",
    description="Requeue one retained dead-letter entry exactly once",
    dependencies=[Depends(get_current_user_record)],
)
async def replay_dead_letter(stream_id: str):
    """Requeue one DLQ entry while retaining its audit record."""
    try:
        return await telemetry_service.replay_dead_letter(stream_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post(
    "/test",
    summary="Test telemetry endpoint",
    description="Test endpoint for telemetry ingestion (development only)"
)
async def test_telemetry(
    request: Request,
    test_data: Dict[str, Any] = None
):
    """
    Test endpoint for telemetry ingestion (development only)
    """
    
    if settings.environment not in [Environment.LOCAL, Environment.DEVELOPMENT]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Test endpoint only available in development"
        )
    
    # Create test telemetry data
    if not test_data:
        from datetime import datetime, timedelta
        
        test_data = {
            "metadata": {
                "agent_id": "test_agent_001",
                "hostname": "test-server-01",
                "timestamp": datetime.utcnow().isoformat(),
                "agent_version": "1.0.0",
                "platform": "linux",
                "architecture": "x86_64",
                "tags": {"environment": "test", "region": "us-east-1"}
            },
            "metrics": [
                {
                    "name": "system.cpu.usage",
                    "value": 45.2,
                    "type": "gauge",
                    "timestamp": datetime.utcnow().isoformat(),
                    "labels": {"core": "0", "mode": "user"},
                    "unit": "percent"
                },
                {
                    "name": "system.memory.used_bytes",
                    "value": 8589934592,  # 8GB
                    "type": "gauge",
                    "timestamp": (datetime.utcnow() - timedelta(seconds=10)).isoformat(),
                    "labels": {"type": "used"},
                    "unit": "bytes"
                }
            ],
            "logs": [
                {
                    "message": "INFO: Application started successfully",
                    "level": "info",
                    "timestamp": datetime.utcnow().isoformat(),
                    "service": "api",
                    "component": "startup"
                },
                {
                    "message": "WARNING: High memory usage detected",
                    "level": "warning",
                    "timestamp": (datetime.utcnow() - timedelta(seconds=5)).isoformat(),
                    "service": "monitoring",
                    "component": "alerts"
                }
            ],
            "events": [
                {
                    "type": "system.health.check",
                    "source": "monitoring",
                    "summary": "System health check completed",
                    "timestamp": datetime.utcnow().isoformat(),
                    "severity": "info",
                    "details": {"check_type": "full", "duration_ms": 125}
                }
            ],
            "batch_id": f"test_batch_{datetime.utcnow().timestamp()}"
        }
    
    # Validate with schema
    try:
        batch_data = TelemetryBatchSchema(**test_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid test data: {str(e)}"
        )
    
    # Create test response
    response = TelemetryResponseSchema(
        status="success",
        message="Test telemetry batch processed successfully",
        batch_id=batch_data.batch_id or "test_batch",
        received_at=datetime.utcnow(),
        processed_items={
            "metrics": len(batch_data.metrics),
            "logs": len(batch_data.logs),
            "events": len(batch_data.events)
        },
        errors=[],
        latency_ms=50.5  # Simulated processing time
    )
    
    logger.info(
        "Test telemetry endpoint called",
        client_ip=request.client.host if request.client else "unknown",
        batch_id=response.batch_id
    )
    
    return response


# Development endpoints
if settings.environment in [Environment.LOCAL, Environment.DEVELOPMENT]:
    
    @router.post("/dev/reset-queues")
    async def reset_queues():
        """Reset all queues (development only)"""
        
        from src.services.telemetry import QueueType
        
        for queue_type in QueueType:
            result = telemetry_service.queue_producer.clear_queue(queue_type)
            if inspect.isawaitable(result):
                await result
        
        return {
            "status": "success",
            "message": "All queues cleared",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    @router.post("/dev/simulate-load")
    async def simulate_load(count: int = 100):
        """Simulate telemetry load (development only)"""
        
        if count > 1000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 1000 batches per simulation"
            )
        
        from datetime import datetime, timedelta
        import asyncio
        
        results = []
        
        for i in range(count):
            # Create test batch
            batch_data = TelemetryBatchSchema(
                metadata={
                    "agent_id": f"test_agent_{i % 10}",
                    "hostname": f"test-server-{i % 5}",
                    "timestamp": datetime.utcnow() - timedelta(seconds=i),
                    "agent_version": "1.0.0"
                },
                metrics=[
                    {
                        "name": f"test.metric.{j}",
                        "value": (i * 10) + j,
                        "type": "gauge",
                        "timestamp": datetime.utcnow() - timedelta(seconds=i + j),
                        "labels": {"iteration": str(i), "metric_index": str(j)}
                    }
                    for j in range(5)
                ],
                batch_id=f"simulated_batch_{i}_{datetime.utcnow().timestamp()}"
            )
            
            # Simulate processing (without actual processing)
            await asyncio.sleep(0.01)  # Simulate processing time
            
            results.append({
                "batch_id": batch_data.batch_id,
                "metrics_count": len(batch_data.metrics),
                "timestamp": datetime.utcnow().isoformat()
            })
        
        return {
            "status": "success",
            "simulated_batches": count,
            "results": results[:10],  # Return first 10 results
            "timestamp": datetime.utcnow().isoformat()
        }