import pytest

from src.database.redis import redis_manager
from src.services.rate_limiter import rate_limiter


@pytest.fixture(autouse=True)
async def reset_rate_limit_state():
    """Isolate live-server integration cases without touching other Redis data."""
    await redis_manager.initialize()
    await rate_limiter.reset_all_rate_limits()
    yield
    await rate_limiter.reset_all_rate_limits()
    await redis_manager.close()
