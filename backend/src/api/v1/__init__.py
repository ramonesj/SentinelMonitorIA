"""
API v1 Router for SentinelMonitorIA
Main router that includes all v1 API endpoints
"""

from fastapi import APIRouter

from src.api.v1 import alerts, chat, telemetry, health, auth, organizations

# Create main router
router = APIRouter()

# Include all API routers
router.include_router(telemetry.router)
router.include_router(health.router)
router.include_router(auth.router)
router.include_router(organizations.router)
router.include_router(alerts.router)
router.include_router(chat.router)

# Additional routers will be added here:
# - auth.router (authentication)
# - users.router (user management)
# - organizations.router (organization management)
# - agents.router (agent management)
# - metrics.router (metrics querying)
# - logs.router (logs querying)
# - events.router (events querying)
# - alerts.router (alert management)
# - ai.router (AI/ML operations)

__all__ = ["router"]