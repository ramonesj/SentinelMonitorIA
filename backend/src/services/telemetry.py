"""
Telemetry service for SentinelMonitorIA
Handles telemetry ingestion, processing, and queue management
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from fastapi.encoders import jsonable_encoder
import json
from dataclasses import dataclass
from enum import Enum
import hashlib
import inspect

from src.config.settings import settings
from src.config.logging import logger
from src.models.telemetry import TelemetryBatch, Metric, LogEntry, Event
from src.models.organization import Organization, Agent
from src.services.queue_contract import QueueMessage, QueueType
from src.schemas.telemetry import TelemetryBatchSchema, TelemetryResponseSchema


class ProcessingStatus(str, Enum):
    """Processing status for telemetry batches"""

    RECEIVED = "received"
    VALIDATING = "validating"
    VALIDATED = "validated"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    RETRYING = "retrying"


class MockQueueProducer:
    """Mock queue producer for local development"""
    
    def __init__(self):
        self.queues: Dict[QueueType, List[QueueMessage]] = {
            queue_type: [] for queue_type in QueueType
        }
        self.queue_sizes: Dict[QueueType, int] = {
            QueueType.TELEMETRY: 10000,
            QueueType.METRICS: 5000,
            QueueType.LOGS: 5000,
            QueueType.EVENTS: 1000,
            QueueType.ALERTS: 1000,
            QueueType.DEAD_LETTER: 1000,
        }
        self.locks: Dict[QueueType, asyncio.Lock] = {
            queue_type: asyncio.Lock() for queue_type in QueueType
        }
        self.processing_tasks: Dict[str, asyncio.Task] = {}
        self._running = False
        
        # Statistics
        self.stats = {
            "messages_sent": 0,
            "messages_processed": 0,
            "messages_failed": 0,
            "queue_depths": {},
            "processing_times": [],
            "last_processed": None
        }
    
    async def start(self):
        """Start the queue processor"""
        if self._running:
            return
        
        self._running = True
        logger.info("Mock queue producer started")
        
        # Start background processing tasks
        for queue_type in [QueueType.TELEMETRY, QueueType.METRICS, QueueType.LOGS, QueueType.EVENTS]:
            task = asyncio.create_task(self._process_queue(queue_type))
            self.processing_tasks[queue_type.value] = task
    
    async def stop(self):
        """Stop the queue processor"""
        self._running = False
        
        # Wait for processing tasks to complete
        for task in self.processing_tasks.values():
            task.cancel()
        
        try:
            await asyncio.gather(*self.processing_tasks.values(), return_exceptions=True)
        except asyncio.CancelledError:
            pass
        
        logger.info("Mock queue producer stopped")
    
    async def send(
        self,
        queue_type: QueueType,
        data: Dict[str, Any],
        priority: int = 0
    ) -> str:
        """Send message to queue"""
        
        message_id = str(uuid4())
        message = QueueMessage(
            id=message_id,
            queue_type=queue_type,
            data=data,
            priority=priority
        )
        
        async with self.locks[queue_type]:
            # Check queue size
            if len(self.queues[queue_type]) >= self.queue_sizes[queue_type]:
                logger.warning(
                    f"Queue {queue_type.value} is full, dropping message",
                    queue_size=len(self.queues[queue_type]),
                    max_size=self.queue_sizes[queue_type]
                )
                raise Exception(f"Queue {queue_type.value} is full")
            
            # Add to queue
            self.queues[queue_type].append(message)
            self.stats["messages_sent"] += 1
            self.stats["queue_depths"][queue_type.value] = len(self.queues[queue_type])
        
        logger.debug(
            f"Message sent to queue {queue_type.value}",
            message_id=message_id,
            queue_size=len(self.queues[queue_type])
        )
        
        return message_id
    
    async def send_batch(
        self,
        queue_type: QueueType,
        items: List[Dict[str, Any]],
        priority: int = 0
    ) -> List[str]:
        """Send batch of messages to queue"""
        
        message_ids = []
        
        async with self.locks[queue_type]:
            for item in items:
                if len(self.queues[queue_type]) >= self.queue_sizes[queue_type]:
                    logger.warning(
                        f"Queue {queue_type.value} is full during batch send",
                        sent=len(message_ids),
                        failed=len(items) - len(message_ids)
                    )
                    break
                
                message_id = str(uuid4())
                message = QueueMessage(
                    id=message_id,
                    queue_type=queue_type,
                    data=item,
                    priority=priority
                )
                
                self.queues[queue_type].append(message)
                message_ids.append(message_id)
                self.stats["messages_sent"] += 1
            
            self.stats["queue_depths"][queue_type.value] = len(self.queues[queue_type])
        
        logger.debug(
            f"Batch sent to queue {queue_type.value}",
            batch_size=len(message_ids),
            queue_size=len(self.queues[queue_type])
        )
        
        return message_ids
    
    async def _process_queue(self, queue_type: QueueType):
        """Process messages from queue"""
        
        logger.info(f"Starting queue processor for {queue_type.value}")
        
        while self._running:
            try:
                # Get message from queue
                message = None
                
                async with self.locks[queue_type]:
                    if self.queues[queue_type]:
                        # Get highest priority message
                        self.queues[queue_type].sort(key=lambda m: (-m.priority, m.created_at))
                        message = self.queues[queue_type].pop(0)
                        self.stats["queue_depths"][queue_type.value] = len(self.queues[queue_type])
                
                if message:
                    # Process message
                    start_time = datetime.utcnow()
                    
                    try:
                        await self._process_message(queue_type, message)
                        
                        processing_time = (datetime.utcnow() - start_time).total_seconds()
                        self.stats["processing_times"].append(processing_time)
                        self.stats["messages_processed"] += 1
                        self.stats["last_processed"] = datetime.utcnow()
                        
                        logger.debug(
                            f"Message processed from {queue_type.value}",
                            message_id=message.id,
                            processing_time=processing_time
                        )
                        
                    except Exception as e:
                        # Handle processing failure
                        self.stats["messages_failed"] += 1
                        
                        if message.retry_count < message.max_retries:
                            # Retry message
                            message.retry_count += 1
                            async with self.locks[queue_type]:
                                self.queues[queue_type].insert(0, message)
                                self.stats["queue_depths"][queue_type.value] = len(self.queues[queue_type])
                            
                            logger.warning(
                                f"Message processing failed, retrying",
                                message_id=message.id,
                                queue_type=queue_type.value,
                                retry_count=message.retry_count,
                                error=str(e)
                            )
                        else:
                            # Move to dead letter queue
                            await self.send(QueueType.DEAD_LETTER, {
                                "original_queue": queue_type.value,
                                "original_message": message.to_dict(),
                                "error": str(e),
                                "failed_at": datetime.utcnow().isoformat()
                            })
                            
                            logger.error(
                                f"Message processing failed after max retries",
                                message_id=message.id,
                                queue_type=queue_type.value,
                                error=str(e)
                            )
                
                # Sleep to prevent busy waiting
                await asyncio.sleep(0.1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Queue processor error for {queue_type.value}", error=str(e))
                await asyncio.sleep(1)
    
    async def _process_message(self, queue_type: QueueType, message: QueueMessage):
        """Process a single message"""
        
        # Simulate processing time
        await asyncio.sleep(0.01)
        
        # Process based on queue type
        if queue_type == QueueType.TELEMETRY:
            # Telemetry processing
            data = message.data
            logger.info(
                "Processing telemetry batch",
                batch_id=data.get("batch_id"),
                organization_id=data.get("organization_id"),
                event_count=data.get("event_count", 0)
            )
        
        elif queue_type == QueueType.METRICS:
            # Metrics processing
            pass
        
        elif queue_type == QueueType.LOGS:
            # Logs processing
            pass
        
        elif queue_type == QueueType.EVENTS:
            # Events processing
            pass
        
        elif queue_type == QueueType.ALERTS:
            # Alerts processing
            pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        
        stats = self.stats.copy()
        
        # Calculate average processing time
        if stats["processing_times"]:
            avg_time = sum(stats["processing_times"]) / len(stats["processing_times"])
            stats["avg_processing_time_seconds"] = avg_time
            # Keep only last 100 processing times
            stats["processing_times"] = stats["processing_times"][-100:]
        else:
            stats["avg_processing_time_seconds"] = 0
        
        # Add current queue depths
        stats["current_queue_depths"] = {
            queue_type.value: len(self.queues[queue_type])
            for queue_type in QueueType
        }
        
        return stats
    
    async def clear_queue(self, queue_type: QueueType):
        """Clear all messages from queue"""
        async with self.locks[queue_type]:
            self.queues[queue_type].clear()
            self.stats["queue_depths"][queue_type.value] = 0
        
        logger.info(f"Queue {queue_type.value} cleared")


class TelemetryService:
    """Service for handling telemetry ingestion and processing"""
    
    def __init__(self):
        if settings.queue_provider.lower() == "redis":
            from src.services.redis_streams import RedisStreamQueueProducer

            self.queue_producer = RedisStreamQueueProducer()
        else:
            self.queue_producer = MockQueueProducer()
        self.batch_size = settings.telemetry_batch_size
        self.buffer_size = settings.telemetry_buffer_size
        self.flush_interval = settings.telemetry_flush_interval
        
        # Statistics
        self.stats = {
            "batches_received": 0,
            "events_processed": 0,
            "avg_processing_time_ms": 0,
            "success_rate": 1.0,
            "last_batch_at": None
        }
    
    async def start(self):
        """Start telemetry service"""
        await self.queue_producer.start()
        logger.info("Telemetry service started")
    
    async def stop(self):
        """Stop telemetry service"""
        await self.queue_producer.stop()
        logger.info("Telemetry service stopped")
    
    async def process_telemetry_batch(
        self,
        db: AsyncSession,
        batch_data: TelemetryBatchSchema,
        organization_id: UUID,
        agent_id: UUID,
        token_id: Optional[UUID] = None
    ) -> TelemetryResponseSchema:
        """Process telemetry batch"""
        
        start_time = datetime.utcnow()
        
        try:
            # Generate batch ID if not provided
            batch_id = batch_data.batch_id or self._generate_batch_id(batch_data)
            
            # Validate organization and agent
            organization, agent = await self._validate_organization_and_agent(
                db, organization_id, agent_id
            )
            
            # Calculate batch size
            total_items = len(batch_data.metrics) + len(batch_data.logs) + len(batch_data.events)
            
            # Check organization limits
            if not await self._check_organization_limits(db, organization, total_items):
                raise Exception(f"Organization {organization_id} has exceeded daily limit")
            
            # Create telemetry batch record
            batch_record = TelemetryBatch(
                batch_id=batch_id,
                organization_id=organization_id,
                agent_id=agent_id,
                source_type=self._determine_source_type(batch_data),
                status=ProcessingStatus.RECEIVED.value,
                event_count=total_items,
                total_size_bytes=self._calculate_batch_size(batch_data),
                ingestion_latency_ms=0,  # Will be updated later
                metadata_json={
                    "token_id": str(token_id) if token_id else None,
                    "agent_version": batch_data.metadata.agent_version,
                    "platform": batch_data.metadata.platform,
                    "architecture": batch_data.metadata.architecture,
                    "tags": batch_data.metadata.tags,
                }
            )
            
            db.add(batch_record)
            await db.flush()  # Get the ID
            
            # Update agent last seen
            agent.last_seen_at = datetime.utcnow()
            agent.last_telemetry_at = datetime.utcnow()
            agent.total_events_sent += total_items
            
            queue_data = {
                "batch_id": str(batch_record.id),
                "organization_id": str(organization_id),
                "agent_id": str(agent_id),
                "batch_data": jsonable_encoder(batch_data),
                "received_at": datetime.utcnow().isoformat()
            }

            # Commit the batch before publishing so a fast worker can always
            # resolve it from PostgreSQL. If publishing fails, keep the
            # durable batch record marked as failed for diagnosis/retry.
            batch_record.status = ProcessingStatus.PROCESSING.value
            await db.commit()

            try:
                await self.queue_producer.send(QueueType.TELEMETRY, queue_data)
            except Exception as queue_error:
                batch_record.status = ProcessingStatus.FAILED.value
                batch_record.error_message = str(queue_error)[:2000]
                await db.commit()
                raise

            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Update statistics
            self._update_stats(total_items, processing_time, True)
            
            # Create response
            response = TelemetryResponseSchema(
                status="success",
                message="Telemetry batch received and queued for processing",
                batch_id=batch_id,
                received_at=datetime.utcnow(),
                processed_items={
                    "metrics": len(batch_data.metrics),
                    "logs": len(batch_data.logs),
                    "events": len(batch_data.events)
                },
                errors=[],
                latency_ms=processing_time
            )
            
            logger.info(
                "Telemetry batch processed successfully",
                batch_id=batch_id,
                organization_id=str(organization_id),
                agent_id=str(agent_id),
                total_items=total_items,
                processing_time_ms=processing_time
            )
            
            return response
            
        except Exception as e:
            # Update statistics
            self._update_stats(0, 0, False)
            
            logger.error(
                "Failed to process telemetry batch",
                organization_id=str(organization_id),
                agent_id=str(agent_id),
                error=str(e)
            )
            
            # Create error response
            return TelemetryResponseSchema(
                status="error",
                message=f"Failed to process telemetry batch: {str(e)}",
                batch_id=batch_id if 'batch_id' in locals() else "unknown",
                received_at=datetime.utcnow(),
                processed_items={
                    "metrics": 0,
                    "logs": 0,
                    "events": 0
                },
                errors=[str(e)],
                latency_ms=(datetime.utcnow() - start_time).total_seconds() * 1000
            )
    
    async def _validate_organization_and_agent(
        self,
        db: AsyncSession,
        organization_id: UUID,
        agent_id: UUID
    ) -> Tuple[Organization, Agent]:
        """Validate organization and agent"""
        
        # Get organization
        organization = await db.execute(
            select(Organization).where(
                (Organization.id == organization_id) &
                (Organization.is_active == True) &
                (Organization.deleted_at.is_(None))
            )
        )
        organization = organization.scalar_one_or_none()
        
        if not organization:
            raise Exception(f"Organization {organization_id} not found or inactive")
        
        # Get agent
        agent = await db.execute(
            select(Agent).where(
                (Agent.id == agent_id) &
                (Agent.organization_id == organization_id) &
                (Agent.is_active == True)
            )
        )
        agent = agent.scalar_one_or_none()
        
        if not agent:
            raise Exception(f"Agent {agent_id} not found or inactive")
        
        return organization, agent
    
    async def _check_organization_limits(
        self,
        db: AsyncSession,
        organization: Organization,
        new_events: int
    ) -> bool:
        """Check if organization is within limits"""
        
        # Check max agents
        active_agents = await db.execute(
            select(func.count(Agent.id)).where(
                (Agent.organization_id == organization.id) &
                (Agent.is_active == True)
            )
        )
        active_agent_count = active_agents.scalar()
        
        if active_agent_count > organization.max_agents:
            return False
        
        # Check daily event limit (simplified - in production would check actual counts)
        # For now, just check if we're within the limit
        if new_events > organization.max_events_per_day:
            return False
        
        return True
    
    def _generate_batch_id(self, batch_data: TelemetryBatchSchema) -> str:
        """Generate unique batch ID"""
        data_string = json.dumps(batch_data.dict(), sort_keys=True)
        hash_object = hashlib.sha256(data_string.encode())
        return f"batch_{hash_object.hexdigest()[:16]}"
    
    def _determine_source_type(self, batch_data: TelemetryBatchSchema) -> str:
        """Determine the primary source type of the batch"""
        if batch_data.metrics:
            return "metrics"
        elif batch_data.logs:
            return "logs"
        elif batch_data.events:
            return "events"
        else:
            return "mixed"
    
    def _calculate_batch_size(self, batch_data: TelemetryBatchSchema) -> int:
        """Calculate approximate batch size in bytes"""
        data_string = json.dumps(jsonable_encoder(batch_data))
        return len(data_string.encode('utf-8'))
    
    def _update_stats(self, items_processed: int, processing_time_ms: float, success: bool):
        """Update service statistics"""
        self.stats["batches_received"] += 1
        self.stats["events_processed"] += items_processed
        
        # Update average processing time
        if self.stats["batches_received"] > 0:
            old_avg = self.stats["avg_processing_time_ms"]
            new_avg = old_avg + (processing_time_ms - old_avg) / self.stats["batches_received"]
            self.stats["avg_processing_time_ms"] = new_avg
        
        # Update success rate
        total_batches = self.stats["batches_received"]
        if success:
            successful_batches = total_batches
        else:
            successful_batches = total_batches - 1
        
        if total_batches > 0:
            self.stats["success_rate"] = successful_batches / total_batches
        
        self.stats["last_batch_at"] = datetime.utcnow()
    
    async def _get_queue_stats(self) -> Dict[str, Any]:
        """Normalize sync mock and async Redis queue statistics."""
        queue_stats = self.queue_producer.get_stats()
        if inspect.isawaitable(queue_stats):
            queue_stats = await queue_stats
        return queue_stats

    async def get_queue_status(self) -> Dict[str, Any]:
        """Return provider-neutral queue depth information."""
        stats = await self._get_queue_stats()
        depths = stats.get("current_queue_depths", {})
        max_size = getattr(self.queue_producer, "queue_sizes", {})
        queues = {}
        for queue_type in QueueType:
            depth = int(depths.get(queue_type.value, 0))
            limit = int(max_size.get(queue_type, 10000))
            queues[queue_type.value] = {
                "depth": depth,
                "max_size": limit,
                "utilization": depth / limit if limit else 0,
                "healthy": depth / limit < 0.9 if limit else True,
            }
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "queues": queues,
            "queue_producer_running": bool(getattr(self.queue_producer, "_running", False)),
            "provider": settings.queue_provider,
        }

    async def get_dead_letters(self, limit: int = 50) -> Dict[str, Any]:
        """Return provider-neutral dead-letter inspection data."""
        list_dead_letters = getattr(self.queue_producer, "list_dead_letters", None)
        if not list_dead_letters:
            raise RuntimeError("Dead-letter inspection requires QUEUE_PROVIDER=redis")
        return {
            "status": "success",
            "provider": settings.queue_provider,
            "entries": await list_dead_letters(limit),
        }

    async def replay_dead_letter(self, stream_id: str) -> Dict[str, Any]:
        """Replay one Redis dead-letter entry without deleting its audit record."""
        replay = getattr(self.queue_producer, "replay_dead_letter", None)
        if not replay:
            raise RuntimeError("Dead-letter replay requires QUEUE_PROVIDER=redis")
        return await replay(stream_id)

    async def get_service_stats(self) -> Dict[str, Any]:
        """Get telemetry service statistics"""
        queue_stats = await self._get_queue_stats()
        
        stats = {
            "telemetry_service": self.stats,
            "queue_producer": queue_stats,
            "configuration": {
                "batch_size": self.batch_size,
                "buffer_size": self.buffer_size,
                "flush_interval": self.flush_interval,
            }
        }
        
        return stats
    
    async def health_check(self) -> Dict[str, Any]:
        """Check provider-neutral telemetry queue health."""
        try:
            queue_status = await self.get_queue_status()
            queue_health = queue_status["queues"]
            all_queues_healthy = all(info["healthy"] for info in queue_health.values())
            return {
                "status": "healthy" if all_queues_healthy else "degraded",
                "timestamp": datetime.utcnow().isoformat(),
                "queues": queue_health,
                "stats": self.stats,
                "queue_producer_running": queue_status["queue_producer_running"],
                "provider": queue_status["provider"],
            }
        except Exception as e:
            logger.error("Telemetry service health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
            }


# Global telemetry service instance
telemetry_service = TelemetryService()