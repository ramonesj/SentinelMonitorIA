"""LLM adapters for rules-only, Ollama, and Amazon Bedrock modes."""

import asyncio
from typing import Any

import boto3
import httpx

from src.config.logging import logger
from src.config.settings import settings


class RulesOnlyProvider:
    """No-network provider used by default and safe without a model."""

    name = "rules"
    model_name = None

    async def generate(self, prompt: str) -> str:
        return ""


class OllamaProvider:
    """Local Ollama HTTP adapter; prompts are never logged."""

    name = "ollama"

    def __init__(self, base_url: str, model_name: str):
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name

    async def generate(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=settings.ai_request_timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": settings.ai_temperature,
                        "num_predict": settings.ai_max_output_tokens,
                    },
                },
            )
            response.raise_for_status()
            body = response.json()
        return str(body.get("response", "")).strip()


class BedrockProvider:
    """Amazon Bedrock Converse adapter using the ECS task IAM role."""

    name = "bedrock"

    def __init__(self, model_name: str, region: str | None):
        self.model_name = model_name
        self.client = boto3.client("bedrock-runtime", region_name=region)

    async def generate(self, prompt: str) -> str:
        converse = getattr(self.client, "converse", None)
        if converse is None:
            raise RuntimeError("Installed boto3 does not expose Bedrock Converse")
        response: dict[str, Any] = await asyncio.to_thread(
            converse,
            modelId=self.model_name,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={
                "temperature": settings.ai_temperature,
                "maxTokens": settings.ai_max_output_tokens,
            },
        )
        content = response.get("output", {}).get("message", {}).get("content", [])
        text_parts = [item.get("text", "") for item in content if isinstance(item, dict)]
        return "\n".join(part for part in text_parts if part).strip()


def build_llm_provider() -> RulesOnlyProvider | OllamaProvider | BedrockProvider:
    """Build the configured provider without making a network call."""
    if settings.ai_provider == "ollama":
        return OllamaProvider(settings.ai_ollama_base_url, settings.ai_model_name)
    if settings.ai_provider == "bedrock":
        if not settings.ai_model_id:
            logger.warning("AI_PROVIDER=bedrock but AI_MODEL_ID is empty; using rules only")
            return RulesOnlyProvider()
        return BedrockProvider(settings.ai_model_id, settings.aws_region)
    return RulesOnlyProvider()
