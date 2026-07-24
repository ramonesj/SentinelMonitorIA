import asyncio
import os
from uuid import uuid4

import asyncpg
import httpx
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

BASE_URL = os.getenv("SENTINEL_TEST_BASE_URL", "http://localhost:8000")


async def fetch_batch_counts(batch_id: str) -> tuple[str | None, int, int, int]:
    connection = await asyncpg.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        user=os.getenv("POSTGRES_USER", "sentinel"),
        password=os.getenv("POSTGRES_PASSWORD", "sentinel123"),
        database=os.getenv("POSTGRES_DB", "sentinelmonitoria"),
    )
    try:
        batch = await connection.fetchrow(
            "SELECT id, status FROM telemetrybatch WHERE batch_id = $1",
            batch_id,
        )
        if not batch:
            return None, 0, 0, 0
        metric_count = await connection.fetchval(
            "SELECT count(*) FROM metric WHERE batch_id = $1", batch["id"]
        )
        log_count = await connection.fetchval(
            "SELECT count(*) FROM logentry WHERE batch_id = $1", batch["id"]
        )
        event_count = await connection.fetchval(
            "SELECT count(*) FROM event WHERE batch_id = $1", batch["id"]
        )
        return batch["status"], metric_count, log_count, event_count
    finally:
        await connection.close()


@pytest.mark.skipif(
    os.getenv("QUEUE_PROVIDER", "mock").lower() != "redis",
    reason="Redis worker integration requires QUEUE_PROVIDER=redis",
)
async def test_redis_worker_persists_complete_telemetry_batch() -> None:
    suffix = uuid4().hex[:12]
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as client:
        registration = await client.post(
            "/api/v1/auth/register",
            json={
                "username": f"worker-{suffix}",
                "email": f"worker-{suffix}@example.com",
                "password": "LocalSmoke!2026",
                "full_name": "Redis Worker Integration",
                "organization_name": f"Redis Worker Org {suffix}",
                "organization_slug": f"redis-worker-{suffix}",
                "timezone": "UTC",
                "locale": "en-US",
            },
        )
        assert registration.status_code == 201, registration.text
        access_token = registration.json()["access_token"]
        organization_id = registration.json()["user"]["organizations"][0]["id"]
        access_headers = {"Authorization": f"Bearer {access_token}"}

        dead_letter_response = await client.get(
            "/api/v1/telemetry/dead-letter",
            headers=access_headers,
        )
        assert dead_letter_response.status_code == 200, dead_letter_response.text
        assert dead_letter_response.json()["status"] == "success"
        assert isinstance(dead_letter_response.json()["entries"], list)

        key_response = await client.post(
            "/api/v1/auth/api-keys",
            headers=access_headers,
            json={
                "name": "Redis worker integration key",
                "organization_id": organization_id,
                "scopes": ["telemetry:write"],
            },
        )
        assert key_response.status_code == 201, key_response.text
        api_key = key_response.json()["token"]

        batch_id = f"redis-worker-batch-{suffix}"
        payload = {
            "metadata": {
                "agent_id": f"redis-worker-agent-{suffix}",
                "hostname": "redis-worker-host",
                "agent_version": "1.0.0",
                "platform": "windows",
                "architecture": "amd64",
                "tags": {"suite": "redis-worker"},
            },
            "metrics": [
                {
                    "name": "worker.metric",
                    "value": 12.5,
                    "type": "gauge",
                    "labels": {"source": "pytest"},
                    "unit": "count",
                }
            ],
            "logs": [
                {
                    "message": "worker integration log",
                    "level": "info",
                    "service": "pytest",
                    "component": "worker",
                }
            ],
            "events": [
                {
                    "type": "worker.integration",
                    "source": "pytest",
                    "summary": "Redis worker integration event",
                    "severity": "info",
                    "details": {"batch": batch_id},
                }
            ],
            "batch_id": batch_id,
        }
        ingestion = await client.post(
            "/api/v1/telemetry",
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
        )
        assert ingestion.status_code == 202, ingestion.text

    for _ in range(30):
        status, metric_count, log_count, event_count = await fetch_batch_counts(batch_id)
        if status == "processed":
            assert metric_count == 1
            assert log_count == 1
            assert event_count == 1
            return
        await asyncio.sleep(1)

    pytest.fail("TelemetryBatch was not processed by the Redis worker within 30 seconds")
