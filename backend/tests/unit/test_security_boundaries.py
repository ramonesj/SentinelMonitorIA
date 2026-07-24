import pytest
from fastapi import HTTPException, Response, status

from src.services.rate_limiter import RateLimiterService, redis_manager


@pytest.mark.asyncio
async def test_rate_limiter_raises_429_when_a_limit_is_exceeded(monkeypatch):
    limiter = RateLimiterService()

    async def exceeded_global(_ip_address):
        return False, 0, 17

    monkeypatch.setattr(limiter, "check_global_rate_limit", exceeded_global)

    with pytest.raises(HTTPException) as error:
        await limiter.enforce_rate_limit("127.0.0.1")

    assert error.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert error.value.detail["retry_after"] == 17
    assert "global" in error.value.detail["message"]


@pytest.mark.asyncio
async def test_rate_limiter_fails_open_when_redis_is_unavailable(monkeypatch):
    limiter = RateLimiterService()

    async def unavailable(*_args, **_kwargs):
        raise RuntimeError("redis unavailable")

    monkeypatch.setattr(redis_manager, "incr_rate_limit", unavailable)

    allowed, remaining, reset_in = await limiter.check_rate_limit("security-test", 5, 60)

    assert allowed is True
    assert remaining == 5
    assert reset_in == 60


@pytest.mark.asyncio
async def test_request_rate_limit_dependency_uses_client_ip_and_path(monkeypatch):
    from starlette.requests import Request

    from src.api.v1 import rate_limit

    calls = {}

    async def enforce_rate_limit(**kwargs):
        calls.update(kwargs)
        return {
            "global": {"allowed": True, "remaining": 98, "reset_in": 52}
        }

    monkeypatch.setattr(rate_limit.rate_limiter, "enforce_rate_limit", enforce_rate_limit)

    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/auth/me",
            "raw_path": b"/api/v1/auth/me",
            "query_string": b"",
            "headers": [],
            "client": ("203.0.113.10", 44321),
            "server": ("testserver", 80),
            "scheme": "http",
        }
    )

    response = Response()
    result = await rate_limit.enforce_request_rate_limit(request, response)

    assert result == {
        "global": {"allowed": True, "remaining": 98, "reset_in": 52}
    }
    assert response.headers["X-RateLimit-Remaining"] == "98"
    assert response.headers["X-RateLimit-Reset"] == "52"
    assert calls == {
        "ip_address": "203.0.113.10",
        "endpoint": "/api/v1/auth/me",
    }


@pytest.mark.asyncio
async def test_rate_limiter_uses_atomic_redis_increment(monkeypatch):
    limiter = RateLimiterService()
    calls = {}

    async def atomic_increment(key, period):
        calls.update({"key": key, "period": period})
        return 3, 47

    monkeypatch.setattr(redis_manager, "incr_rate_limit", atomic_increment)

    allowed, remaining, reset_in = await limiter.check_rate_limit("atomic", 5, 60)

    assert allowed is True
    assert remaining == 2
    assert reset_in == 47
    assert calls == {"key": "atomic", "period": 60}
