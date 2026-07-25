"""Contracts shared by local and Bedrock intelligence providers."""

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class Finding:
    """A deterministic or model-assisted observation about telemetry."""

    rule_id: str
    severity: str
    title: str
    description: str
    recommendation: str
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "recommendation": self.recommendation,
            "evidence": self.evidence,
        }


class LLMProvider(Protocol):
    """Minimal async contract for Ollama, Bedrock, or rules-only mode."""

    name: str
    model_name: str | None

    async def generate(self, prompt: str) -> str:
        """Generate an explanation from an untrusted, already-redacted context."""


class ContextProvider(Protocol):
    """Retrieve bounded context without allowing logs to become instructions."""

    name: str

    async def retrieve(self, query: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Return bounded context snippets."""
