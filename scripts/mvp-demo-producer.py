#!/usr/bin/env python3
"""Controlled synthetic telemetry producer for the SentinelMonitorIA MVP demo.

The process emits harmless normal telemetry every 30-60 seconds and one
synthetic incident every 5-10 minutes. It never generates host load: the high
CPU and memory values are payload values consumed by the anomaly detector.

Required environment variables:
  SENTINEL_API_ENDPOINT  Backend base URL, for example http://alb.example
  SENTINEL_API_KEY       API key with only telemetry:write scope

Optional environment variables:
  SENTINEL_AGENT_ID      Stable agent identifier
  SENTINEL_HOSTNAME      Hostname shown in the agent inventory
  SENTINEL_AGENT_VERSION Producer version
  SENTINEL_NORMAL_MIN_SECONDS / SENTINEL_NORMAL_MAX_SECONDS
  SENTINEL_INCIDENT_MIN_SECONDS / SENTINEL_INCIDENT_MAX_SECONDS
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen


LOGGER = logging.getLogger("mvp-demo-producer")
DEFAULT_ENDPOINT = "http://sm-staging-alb-1278334952.us-east-1.elb.amazonaws.com"
USER_AGENT = "sentinel-mvp-demo-producer/1.0"


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_window(name: str, default: float, minimum: float, maximum: float) -> float:
    raw = os.getenv(name, str(default))
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum:g} and {maximum:g}")
    return value


def api_base(endpoint: str) -> str:
    """Accept either a backend base URL or the full telemetry endpoint."""
    normalized = endpoint.rstrip("/")
    marker = "/api/v1/telemetry"
    if normalized.endswith(marker):
        normalized = normalized[: -len(marker)]
    parts = urlsplit(normalized)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise ValueError("SENTINEL_API_ENDPOINT must be an HTTP(S) URL")
    return urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), "", "")).rstrip("/")


@dataclass(frozen=True)
class Config:
    endpoint: str
    api_key: str
    agent_id: str
    hostname: str
    agent_version: str
    normal_min_seconds: float
    normal_max_seconds: float
    incident_min_seconds: float
    incident_max_seconds: float

    @classmethod
    def from_environment(cls) -> "Config":
        endpoint = api_base(os.getenv("SENTINEL_API_ENDPOINT", DEFAULT_ENDPOINT))
        api_key = os.getenv("SENTINEL_API_KEY", "").strip()
        if not api_key:
            raise ValueError("SENTINEL_API_KEY is required")

        return cls(
            endpoint=endpoint,
            api_key=api_key,
            agent_id=os.getenv("SENTINEL_AGENT_ID", "ec2-test-redes-synthetic"),
            hostname=os.getenv("SENTINEL_HOSTNAME", "test-redes"),
            agent_version=os.getenv("SENTINEL_AGENT_VERSION", "mvp-demo-producer/1.0"),
            normal_min_seconds=parse_window("SENTINEL_NORMAL_MIN_SECONDS", 30, 30, 60),
            normal_max_seconds=parse_window("SENTINEL_NORMAL_MAX_SECONDS", 60, 30, 60),
            incident_min_seconds=parse_window("SENTINEL_INCIDENT_MIN_SECONDS", 300, 300, 600),
            incident_max_seconds=parse_window("SENTINEL_INCIDENT_MAX_SECONDS", 600, 300, 600),
        )

    @property
    def telemetry_url(self) -> str:
        return f"{self.endpoint}/api/v1/telemetry"


def request_json(
    method: str,
    url: str,
    *,
    token: str | None = None,
    payload: dict[str, Any] | None = None,
    timeout: float = 20,
) -> tuple[int | None, dict[str, Any] | None]:
    headers = {
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    }
    body = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read()
            if not raw:
                return response.status, None
            try:
                return response.status, json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return response.status, None
    except HTTPError as exc:
        # Do not log or return the response body: it could contain deployment
        # details, and the producer only needs the status for retry decisions.
        return exc.code, None
    except (TimeoutError, URLError, OSError) as exc:
        LOGGER.warning("request_failed method=%s path=%s error=%s", method, urlsplit(url).path, type(exc).__name__)
        return None, None


def metadata(config: Config, timestamp: str) -> dict[str, Any]:
    return {
        "agent_id": config.agent_id,
        "hostname": config.hostname,
        "timestamp": timestamp,
        "agent_version": config.agent_version,
        "platform": "linux",
        "architecture": "x86_64",
        "tags": {
            "environment": "mvp-demo",
            "synthetic": "true",
            "source": "continuous-demo",
        },
    }


def make_batch(config: Config, incident: bool) -> dict[str, Any]:
    timestamp = utc_iso()
    if incident:
        metrics = [
            {
                "name": "system.cpu.usage",
                "value": 96.0,
                "type": "gauge",
                "timestamp": timestamp,
                "labels": {"source": "synthetic-incident"},
                "unit": "percent",
            },
            {
                "name": "system.memory.usage",
                "value": 94.0,
                "type": "gauge",
                "timestamp": timestamp,
                "labels": {"source": "synthetic-incident"},
                "unit": "percent",
            },
        ]
        logs = [
            {
                "message": "Synthetic controlled incident: workload saturation threshold exceeded",
                "level": "error",
                "timestamp": timestamp,
                "service": "sentinel-demo-producer",
                "component": "synthetic-load",
                "metadata": {"controlled": True, "source": "continuous-demo"},
            }
        ]
        events = [
            {
                "type": "synthetic.incident",
                "source": "sentinel-demo-producer",
                "summary": "Controlled high-severity demo incident",
                "timestamp": timestamp,
                "severity": "high",
                "details": {
                    "controlled": True,
                    "cpu_percent": 96.0,
                    "memory_percent": 94.0,
                },
            }
        ]
    else:
        cpu = round(random.uniform(25.0, 55.0), 2)
        memory = round(random.uniform(35.0, 65.0), 2)
        metrics = [
            {
                "name": "system.cpu.usage",
                "value": cpu,
                "type": "gauge",
                "timestamp": timestamp,
                "labels": {"source": "synthetic-heartbeat"},
                "unit": "percent",
            },
            {
                "name": "system.memory.usage",
                "value": memory,
                "type": "gauge",
                "timestamp": timestamp,
                "labels": {"source": "synthetic-heartbeat"},
                "unit": "percent",
            },
        ]
        logs = [
            {
                "message": "Synthetic heartbeat: service operating within normal range",
                "level": "info",
                "timestamp": timestamp,
                "service": "sentinel-demo-producer",
                "component": "synthetic-heartbeat",
                "metadata": {"controlled": True, "source": "continuous-demo"},
            }
        ]
        events = [
            {
                "type": "synthetic.health.check",
                "source": "sentinel-demo-producer",
                "summary": "Synthetic service health check completed",
                "timestamp": timestamp,
                "severity": "info",
                "details": {"controlled": True, "source": "continuous-demo"},
            }
        ]

    return {
        "metadata": metadata(config, timestamp),
        "metrics": metrics,
        "logs": logs,
        "events": events,
        "batch_id": f"mvp-demo-{uuid.uuid4().hex}",
    }


def send_batch(config: Config, batch: dict[str, Any]) -> bool:
    incident = batch["metadata"]["tags"].get("source") == "continuous-demo" and batch["events"][0]["severity"] == "high"
    kind = "incident" if incident else "normal"
    for attempt in range(1, 4):
        status, _ = request_json("POST", config.telemetry_url, token=config.api_key, payload=batch)
        if status == 202:
            LOGGER.info(
                "telemetry_sent kind=%s status=202 batch_id=%s metrics=%d logs=%d events=%d",
                kind,
                batch["batch_id"],
                len(batch["metrics"]),
                len(batch["logs"]),
                len(batch["events"]),
            )
            return True
        if status in {401, 403}:
            LOGGER.error("telemetry_rejected kind=%s status=%s; stopping retries for this batch", kind, status)
            return False
        if status == 429 or (status is not None and status >= 500) or status is None:
            if attempt < 3:
                delay = 2 ** (attempt - 1)
                LOGGER.warning("telemetry_retry kind=%s status=%s attempt=%d delay_seconds=%d", kind, status or "network", attempt, delay)
                time.sleep(delay)
                continue
        LOGGER.error("telemetry_rejected kind=%s status=%s", kind, status or "network")
        return False
    return False


def probe_services(config: Config) -> None:
    for path in ("/health", "/api/v1/telemetry/health"):
        status, _ = request_json("GET", f"{config.endpoint}{path}")
        LOGGER.info("service_probe path=%s status=%s", path, status or "network")


def send_once(config: Config, incident: bool) -> int:
    success = send_batch(config, make_batch(config, incident))
    probe_services(config)
    return 0 if success else 1


def run_forever(config: Config) -> None:
    LOGGER.info(
        "producer_started endpoint=%s agent_id=%s normal_window=%g-%gs incident_window=%g-%gs",
        config.endpoint,
        config.agent_id,
        config.normal_min_seconds,
        config.normal_max_seconds,
        config.incident_min_seconds,
        config.incident_max_seconds,
    )
    send_once(config, incident=False)
    now = time.monotonic()
    next_normal = now + random.uniform(config.normal_min_seconds, config.normal_max_seconds)
    next_incident = now + random.uniform(config.incident_min_seconds, config.incident_max_seconds)

    while True:
        now = time.monotonic()
        if now >= next_incident:
            send_once(config, incident=True)
            now = time.monotonic()
            next_incident = now + random.uniform(config.incident_min_seconds, config.incident_max_seconds)
            next_normal = now + random.uniform(config.normal_min_seconds, config.normal_max_seconds)
        elif now >= next_normal:
            send_once(config, incident=False)
            next_normal = time.monotonic() + random.uniform(config.normal_min_seconds, config.normal_max_seconds)

        sleep_until = min(next_normal, next_incident)
        time.sleep(max(1.0, min(15.0, sleep_until - time.monotonic())))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="send exactly one batch and exit")
    parser.add_argument("--mode", choices=("normal", "incident"), default="normal", help="batch type for --once")
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(
        level=os.getenv("SENTINEL_LOG_LEVEL", "INFO").upper(),
        format="%(asctime)sZ %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    try:
        config = Config.from_environment()
        args = parse_args()
        if args.once:
            return send_once(config, incident=args.mode == "incident")
        run_forever(config)
    except KeyboardInterrupt:
        LOGGER.info("producer_stopped reason=signal")
        return 0
    except ValueError as exc:
        LOGGER.error("configuration_error=%s", exc)
        return 2
    except Exception:
        LOGGER.exception("producer_stopped reason=unexpected_error")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
