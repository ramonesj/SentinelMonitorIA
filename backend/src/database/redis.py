"""
Redis configuration and utilities for SentinelMonitorIA
Uses aioredis for async Redis connections
"""

from typing import Optional, Any, Union
import json
from datetime import timedelta
from redis import asyncio as redis_async
from src.config.settings import settings
from src.config.logging import logger


class RedisManager:
    """Redis manager for async connections and operations"""
    
    def __init__(self):
        self.client: Optional[redis_async.Redis] = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize Redis connection"""
        if self._initialized:
            return
        
        logger.info(
            "Initializing Redis connection",
            redis_host=settings.redis_host,
            redis_port=settings.redis_port,
            redis_tls=settings.redis_tls,
        )
        
        try:
            # Create Redis connection with certificate verification for TLS.
            connection_options = {
                "encoding": "utf-8",
                "decode_responses": True,
                "max_connections": 20,
                "socket_keepalive": True,
                "retry_on_timeout": True,
            }
            if settings.redis_tls:
                connection_options["ssl_cert_reqs"] = "required"

            self.client = redis_async.from_url(
                settings.redis_url,
                **connection_options,
            )
            
            # Test connection
            await self.client.ping()
            
            self._initialized = True
            
            logger.info("Redis connection initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize Redis connection", error=str(e))
            raise
    
    async def close(self) -> None:
        """Close Redis connection"""
        if self.client:
            await self.client.aclose()
            self._initialized = False
            logger.info("Redis connection closed")
    
    async def health_check(self) -> bool:
        """Check Redis health"""
        try:
            if not self.client:
                return False
            
            return bool(await self.client.ping())
        
        except Exception as e:
            logger.error("Redis health check failed", error=str(e))
            return False
    
    # Basic operations
    async def set(
        self,
        key: str,
        value: Union[str, dict, list, int, float],
        expire: Optional[timedelta] = None
    ) -> bool:
        """Set key-value pair"""
        if not self._initialized:
            await self.initialize()
        
        try:
            # Convert non-string values to JSON
            if not isinstance(value, str):
                value = json.dumps(value)
            
            if expire:
                return await self.client.setex(key, int(expire.total_seconds()), value)
            else:
                return await self.client.set(key, value)
        
        except Exception as e:
            logger.error("Redis set operation failed", key=key, error=str(e))
            raise
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get value by key"""
        if not self._initialized:
            await self.initialize()
        
        try:
            value = await self.client.get(key)
            
            if value is None:
                return default
            
            # Try to parse as JSON
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        
        except Exception as e:
            logger.error("Redis get operation failed", key=key, error=str(e))
            return default
    
    async def delete(self, key: str) -> bool:
        """Delete key"""
        if not self._initialized:
            await self.initialize()
        
        try:
            return await self.client.delete(key) > 0
        
        except Exception as e:
            logger.error("Redis delete operation failed", key=key, error=str(e))
            raise
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self._initialized:
            await self.initialize()
        
        try:
            return await self.client.exists(key) > 0
        
        except Exception as e:
            logger.error("Redis exists operation failed", key=key, error=str(e))
            raise
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set key expiration"""
        if not self._initialized:
            await self.initialize()
        
        try:
            return await self.client.expire(key, seconds)
        
        except Exception as e:
            logger.error("Redis expire operation failed", key=key, error=str(e))
            raise
    
    # Hash operations
    async def hset(self, key: str, field: str, value: Any) -> bool:
        """Set hash field"""
        if not self._initialized:
            await self.initialize()
        
        try:
            if not isinstance(value, str):
                value = json.dumps(value)
            
            return await self.client.hset(key, field, value)
        
        except Exception as e:
            logger.error("Redis hset operation failed", key=key, field=field, error=str(e))
            raise
    
    async def hget(self, key: str, field: str, default: Any = None) -> Any:
        """Get hash field"""
        if not self._initialized:
            await self.initialize()
        
        try:
            value = await self.client.hget(key, field)
            
            if value is None:
                return default
            
            # Try to parse as JSON
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        
        except Exception as e:
            logger.error("Redis hget operation failed", key=key, field=field, error=str(e))
            return default
    
    async def hgetall(self, key: str) -> dict:
        """Get all hash fields"""
        if not self._initialized:
            await self.initialize()
        
        try:
            result = await self.client.hgetall(key)
            
            # Parse JSON values
            parsed_result = {}
            for field, value in result.items():
                try:
                    parsed_result[field] = json.loads(value)
                except json.JSONDecodeError:
                    parsed_result[field] = value
            
            return parsed_result
        
        except Exception as e:
            logger.error("Redis hgetall operation failed", key=key, error=str(e))
            raise
    
    # List operations
    async def lpush(self, key: str, *values: Any) -> int:
        """Push values to list"""
        if not self._initialized:
            await self.initialize()
        
        try:
            # Convert values to strings
            str_values = []
            for value in values:
                if not isinstance(value, str):
                    str_values.append(json.dumps(value))
                else:
                    str_values.append(value)
            
            return await self.client.lpush(key, *str_values)
        
        except Exception as e:
            logger.error("Redis lpush operation failed", key=key, error=str(e))
            raise
    
    async def rpop(self, key: str, default: Any = None) -> Any:
        """Pop value from list"""
        if not self._initialized:
            await self.initialize()
        
        try:
            value = await self.client.rpop(key)
            
            if value is None:
                return default
            
            # Try to parse as JSON
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        
        except Exception as e:
            logger.error("Redis rpop operation failed", key=key, error=str(e))
            return default
    
    # Set operations
    async def sadd(self, key: str, *values: Any) -> int:
        """Add values to set"""
        if not self._initialized:
            await self.initialize()
        
        try:
            # Convert values to strings
            str_values = []
            for value in values:
                if not isinstance(value, str):
                    str_values.append(json.dumps(value))
                else:
                    str_values.append(value)
            
            return await self.client.sadd(key, *str_values)
        
        except Exception as e:
            logger.error("Redis sadd operation failed", key=key, error=str(e))
            raise
    
    async def smembers(self, key: str) -> set:
        """Get all set members"""
        if not self._initialized:
            await self.initialize()
        
        try:
            values = await self.client.smembers(key)
            
            # Parse JSON values
            parsed_values = set()
            for value in values:
                try:
                    parsed_values.add(json.loads(value))
                except json.JSONDecodeError:
                    parsed_values.add(value)
            
            return parsed_values
        
        except Exception as e:
            logger.error("Redis smembers operation failed", key=key, error=str(e))
            raise
    
    # Rate limiting operations
    async def incr_rate_limit(self, key: str, period: int) -> tuple[int, int]:
        """
        Increment rate limit counter
        
        Returns:
            tuple[current_count, ttl_seconds]
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Create rate limit key
            rate_key = f"rate_limit:{key}"
            
            # Increment counter
            current = await self.client.incr(rate_key)
            
            # Set expiry if first increment
            if current == 1:
                await self.client.expire(rate_key, period)
            
            # Get TTL
            ttl = await self.client.ttl(rate_key)
            
            return current, ttl
        
        except Exception as e:
            logger.error("Redis rate limit increment failed", key=key, error=str(e))
            raise
    
    # Utility functions
    async def flushdb(self) -> None:
        """Flush all databases (use with caution)"""
        if not self._initialized:
            await self.initialize()
        
        logger.warning("Flushing Redis database")
        await self.client.flushdb()
        logger.info("Redis database flushed")
    
    async def get_stats(self) -> dict:
        """Get Redis statistics"""
        try:
            if not self.client:
                return {"error": "Redis not initialized"}
            
            info = await self.client.info()
            
            stats = {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "0"),
                "total_connections_received": info.get("total_connections_received", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "uptime_in_seconds": info.get("uptime_in_seconds", 0),
            }
            
            return stats
        
        except Exception as e:
            logger.error("Failed to get Redis stats", error=str(e))
            return {"error": str(e)}


# Global Redis manager instance
redis_manager = RedisManager()


# Context manager for Redis operations
class RedisContext:
    """Context manager for Redis operations"""
    
    async def __aenter__(self) -> RedisManager:
        await redis_manager.initialize()
        return redis_manager
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass  # Don't close connection, reuse pool


# Dependency for FastAPI
async def get_redis() -> RedisManager:
    """Dependency for FastAPI to get Redis manager"""
    await redis_manager.initialize()
    return redis_manager