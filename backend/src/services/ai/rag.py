"""Local context and optional Bedrock Knowledge Base retrieval."""

import asyncio
import re
from typing import Any

import boto3

from src.config.logging import logger
from src.config.settings import settings


_SECRET_PATTERNS = (
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._-]+"),
    re.compile(r"(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}(?![A-Za-z0-9_-])"),
    re.compile(r"(?i)(password|secret|token|api[_-]?key)\s*[:=]\s*[^,\s]+"),
)


def redact_untrusted_text(value: str, max_length: int = 1200) -> str:
    """Remove common credential-shaped values before an LLM sees telemetry."""
    redacted = value
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted[:max_length]


class BatchContextProvider:
    """Dependency-free local context provider based on the current batch."""

    name = "local-batch"

    async def retrieve(self, query: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
        snippets: list[dict[str, Any]] = []
        for item in (payload.get("batch_data") or {}).get("logs", [])[:20]:
            snippets.append(
                {
                    "type": "log",
                    "text": redact_untrusted_text(str(item.get("message", ""))),
                    "level": item.get("level", "info"),
                    "service": item.get("service"),
                }
            )
        for item in (payload.get("batch_data") or {}).get("events", [])[:20]:
            snippets.append(
                {
                    "type": "event",
                    "text": redact_untrusted_text(str(item.get("summary", ""))),
                    "severity": item.get("severity", "info"),
                    "source": item.get("source"),
                }
            )
        return snippets[:40]


class BedrockKnowledgeBaseContextProvider:
    """Optional retrieval adapter for an existing Bedrock Knowledge Base."""

    name = "bedrock-knowledge-base"

    def __init__(self, knowledge_base_id: str, region: str | None):
        self.knowledge_base_id = knowledge_base_id
        self.client = boto3.client("bedrock-agent-runtime", region_name=region)

    async def retrieve(self, query: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
        if not query.strip():
            return []
        response = await asyncio.to_thread(
            self.client.retrieve,
            knowledgeBaseId=self.knowledge_base_id,
            retrievalQuery={"text": redact_untrusted_text(query, 800)},
            retrievalConfiguration={"vectorSearchConfiguration": {"numberOfResults": 5}},
        )
        snippets: list[dict[str, Any]] = []
        for result in response.get("retrievalResults", []):
            content = result.get("content", {})
            text = content.get("text") if isinstance(content, dict) else None
            if text:
                snippets.append(
                    {
                        "type": "knowledge-base",
                        "text": redact_untrusted_text(text),
                        "score": result.get("score"),
                        "location": result.get("location", {}).get("type"),
                    }
                )
        return snippets


def build_context_provider() -> BatchContextProvider | BedrockKnowledgeBaseContextProvider:
    """Select local context or Bedrock retrieval from configuration."""
    if settings.ai_provider == "bedrock" and settings.ai_knowledge_base_id:
        try:
            return BedrockKnowledgeBaseContextProvider(settings.ai_knowledge_base_id, settings.aws_region)
        except Exception as exc:
            logger.warning("Bedrock Knowledge Base unavailable; using batch context", error=str(exc))
    return BatchContextProvider()
