"""
Rate limiting service for SentinelMonitorIA
Uses Redis for distributed rate limiting
"""

from typing import Optional, Tuple, Dict, Any
from datetime import timedelta
from uuid import UUID
from fastapi import HTTPException, status
from src.config.settings import settings
from src.config.logging import logger
from src.database.redis import redis_manager


class RateLimiterService:
    """Service for handling rate limiting"""
    
    def __init__(self):
        self.global_limit = settings.rate_limit_requests
        self.global_period = settings.rate_limit_period
        self.organization_limit = settings.rate_limit_organization_requests
    
    async def check_rate_limit(
        self,
        key: str,
        limit: int,
        period: int
    ) -> Tuple[bool, int, int]:
        """
        Check rate limit for a key
        
        Returns:
            tuple[allowed, remaining, reset_in]
        """
        
        try:
            # Create rate limit key
            rate_key = f"rate_limit:{key}"
            
            # Get current count
            current = await redis_manager.get(rate_key, 0)
            if isinstance(current, str):
                current = int(current)
            
            # Increment if not at limit
            if current < limit:
                await redis_manager.set(
                    rate_key,
                    current + 1,
                    expire=timedelta(seconds=period)
                )
                remaining = limit - (current + 1)
            else:
                remaining = 0
            
            # Get TTL
            ttl = await redis_manager.client.ttl(rate_key)
            if ttl < 0:
                ttl = period
            
            allowed = current < limit
            
            logger.debug(
                "Rate limit check",
                key=key,
                current=current,
                limit=limit,
                allowed=allowed,
                remaining=remaining,
                ttl=ttl
            )
            
            return allowed, remaining, ttl
            
        except Exception as e:
            logger.error("Rate limit check failed", key=key, error=str(e))
            # Allow request if rate limiting fails
            return True, limit, period
    
    async def check_global_rate_limit(self, ip_address: str) -> Tuple[bool, int, int]:
        """Check global rate limit by IP address"""
        key = f"global:ip:{ip_address}"
        return await self.check_rate_limit(key, self.global_limit, self.global_period)
    
    async def check_organization_rate_limit(
        self,
        organization_id: UUID,
        agent_id: Optional[str] = None
    ) -> Tuple[bool, int, int]:
        """Check organization rate limit"""
        if agent_id:
            key = f"org:{organization_id}:agent:{agent_id}"
        else:
            key = f"org:{organization_id}"
        
        return await self.check_rate_limit(key, self.organization_limit, self.global_period)
    
    async def check_token_rate_limit(
        self,
        token_id: UUID,
        limit: int,
        period: int
    ) -> Tuple[bool, int, int]:
        """Check rate limit for specific token"""
        key = f"token:{token_id}"
        return await self.check_rate_limit(key, limit, period)
    
    async def check_endpoint_rate_limit(
        self,
        endpoint: str,
        organization_id: Optional[UUID] = None,
        agent_id: Optional[str] = None
    ) -> Tuple[bool, int, int]:
        """Check rate limit for specific endpoint"""
        if organization_id:
            if agent_id:
                key = f"endpoint:{endpoint}:org:{organization_id}:agent:{agent_id}"
            else:
                key = f"endpoint:{endpoint}:org:{organization_id}"
        else:
            key = f"endpoint:{endpoint}"
        
        # Default endpoint limits
        endpoint_limits = {
            "/api/v1/telemetry": 100,  # 100 requests per minute
            "/api/v1/metrics": 10,     # 10 requests per minute
            "/api/v1/logs": 50,        # 50 requests per minute
        }
        
        limit = endpoint_limits.get(endpoint, 10)
        return await self.check_rate_limit(key, limit, 60)  # 60 seconds
    
    async def enforce_rate_limit(
        self,
        ip_address: str,
        organization_id: Optional[UUID] = None,
        token_id: Optional[UUID] = None,
        token_limit: Optional[int] = None,
        token_period: Optional[int] = None,
        agent_id: Optional[str] = None,
        endpoint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enforce all applicable rate limits
        
        Returns rate limit information
        """
        
        rate_limit_info = {
            "global": {"allowed": True, "remaining": self.global_limit, "reset_in": self.global_period},
            "organization": None,
            "token": None,
            "endpoint": None,
        }
        
        # Check global rate limit
        global_allowed, global_remaining, global_reset = await self.check_global_rate_limit(ip_address)
        rate_limit_info["global"] = {
            "allowed": global_allowed,
            "remaining": global_remaining,
            "reset_in": global_reset
        }
        
        # Check organization rate limit
        if organization_id:
            org_allowed, org_remaining, org_reset = await self.check_organization_rate_limit(organization_id, agent_id)
            rate_limit_info["organization"] = {
                "allowed": org_allowed,
                "remaining": org_remaining,
                "reset_in": org_reset
            }
        
        # Check token rate limit
        if token_id and token_limit and token_period:
            token_allowed, token_remaining, token_reset = await self.check_token_rate_limit(token_id, token_limit, token_period)
            rate_limit_info["token"] = {
                "allowed": token_allowed,
                "remaining": token_remaining,
                "reset_in": token_reset
            }
        
        # Check endpoint rate limit
        if endpoint:
            endpoint_allowed, endpoint_remaining, endpoint_reset = await self.check_endpoint_rate_limit(
                endpoint, organization_id, agent_id
            )
            rate_limit_info["endpoint"] = {
                "allowed": endpoint_allowed,
                "remaining": endpoint_remaining,
                "reset_in": endpoint_reset
            }
        
        # Check if any limit is exceeded
        all_allowed = all(
            info["allowed"]
            for info in rate_limit_info.values()
            if info is not None
        )
        
        if not all_allowed:
            # Find which limit was exceeded
            exceeded_limits = []
            for limit_type, info in rate_limit_info.items():
                if info and not info["allowed"]:
                    exceeded_limits.append(limit_type)
            
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "message": f"Rate limit exceeded for: {', '.join(exceeded_limits)}",
                    "retry_after": max(info["reset_in"] for info in rate_limit_info.values() if info),
                    "limits": rate_limit_info
                }
            )
        
        return rate_limit_info
    
    async def get_rate_limit_stats(self, key_prefix: str = "") -> Dict[str, Any]:
        """Get rate limiting statistics"""
        try:
            # Get all rate limit keys
            pattern = f"rate_limit:{key_prefix}*" if key_prefix else "rate_limit:*"
            
            # Note: aioredis doesn't have keys() method, we'll use scan instead
            # This is a simplified version
            keys = []
            cursor = 0
            
            # Scan for keys (simplified - in production use proper scan)
            async for key in redis_manager.client.scan_iter(match=pattern):
                keys.append(key)
            
            stats = {
                "total_keys": len(keys),
                "keys": keys[:10],  # Limit to first 10 keys
                "global_limit": self.global_limit,
                "global_period": self.global_period,
                "organization_limit": self.organization_limit,
            }
            
            # Get sample values
            sample_stats = []
            for key in keys[:5]:
                value = await redis_manager.get(key, 0)
                ttl = await redis_manager.client.ttl(key)
                sample_stats.append({
                    "key": key,
                    "value": value,
                    "ttl": ttl
                })
            
            stats["sample_stats"] = sample_stats
            
            return stats
            
        except Exception as e:
            logger.error("Failed to get rate limit stats", error=str(e))
            return {"error": str(e)}
    
    async def reset_rate_limit(self, key: str) -> bool:
        """Reset rate limit for a key"""
        try:
            await redis_manager.delete(f"rate_limit:{key}")
            logger.info("Rate limit reset", key=key)
            return True
        except Exception as e:
            logger.error("Failed to reset rate limit", key=key, error=str(e))
            return False
    
    async def reset_all_rate_limits(self, key_prefix: str = "") -> int:
        """Reset all rate limits (or with prefix)"""
        try:
            pattern = f"rate_limit:{key_prefix}*" if key_prefix else "rate_limit:*"
            
            # Scan and delete keys
            count = 0
            async for key in redis_manager.client.scan_iter(match=pattern):
                await redis_manager.client.delete(key)
                count += 1
            
            logger.warning("All rate limits reset", prefix=key_prefix, count=count)
            return count
            
        except Exception as e:
            logger.error("Failed to reset all rate limits", error=str(e))
            return 0
    
    # Utility methods for rate limit headers
    def create_rate_limit_headers(
        self,
        rate_limit_info: Dict[str, Any],
        limit_type: str = "global"
    ) -> Dict[str, str]:
        """Create rate limit headers for HTTP response"""
        
        if limit_type not in rate_limit_info or not rate_limit_info[limit_type]:
            return {}
        
        info = rate_limit_info[limit_type]
        
        headers = {
            "X-RateLimit-Limit": str(self.global_limit if limit_type == "global" else self.organization_limit),
            "X-RateLimit-Remaining": str(info["remaining"]),
            "X-RateLimit-Reset": str(info["reset_in"]),
        }
        
        if limit_type == "token" and "token" in rate_limit_info and rate_limit_info["token"]:
            token_info = rate_limit_info["token"]
            headers.update({
                "X-RateLimit-Token-Limit": str(token_info.get("limit", "unknown")),
                "X-RateLimit-Token-Remaining": str(token_info["remaining"]),
                "X-RateLimit-Token-Reset": str(token_info["reset_in"]),
            })
        
        if limit_type == "endpoint" and "endpoint" in rate_limit_info and rate_limit_info["endpoint"]:
            endpoint_info = rate_limit_info["endpoint"]
            headers.update({
                "X-RateLimit-Endpoint-Limit": str(endpoint_info.get("limit", "unknown")),
                "X-RateLimit-Endpoint-Remaining": str(endpoint_info["remaining"]),
                "X-RateLimit-Endpoint-Reset": str(endpoint_info["reset_in"]),
            })
        
        return headers


# Global rate limiter service instance
rate_limiter = RateLimiterService()