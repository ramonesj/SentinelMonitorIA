"""Shared rate-limit dependencies for active v1 routes."""

from typing import Any, Dict

from fastapi import Request, Response

from src.services.rate_limiter import rate_limiter


async def enforce_request_rate_limit(
    request: Request,
    response: Response,
) -> Dict[str, Any]:
    """Apply the IP and endpoint limits to one HTTP request.

    API-key telemetry ingestion keeps its specialized organization, agent,
    token, and endpoint checks in the telemetry router. This dependency covers
    the canonical JWT routes without applying a second limit to telemetry.
    """
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_info = await rate_limiter.enforce_rate_limit(
        ip_address=client_ip,
        endpoint=request.url.path,
    )
    response.headers.update(
        rate_limiter.create_rate_limit_headers(rate_limit_info, "global")
    )
    return rate_limit_info


async def enforce_registration_rate_limit(
    request: Request,
    response: Response,
) -> Dict[str, Any]:
    """Apply the global IP limit to registration without a shared endpoint bucket."""
    client_ip = request.client.host if request.client else "unknown"
    rate_limit_info = await rate_limiter.enforce_rate_limit(ip_address=client_ip)
    response.headers.update(
        rate_limiter.create_rate_limit_headers(rate_limit_info, "global")
    )
    return rate_limit_info
