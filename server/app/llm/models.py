from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class TokenUsage(BaseModel):
    """Token accounting reported by an LLM provider."""

    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class PromptMetadata(BaseModel):
    """Metadata describing how a prompt was assembled and executed."""

    agent_name: str
    template_name: str
    provider: str
    model: str
    cache_key: str | None = None
    cache_hit: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class LLMRequest(BaseModel):
    """Provider-neutral request passed through the LLM runtime."""

    prompt: str
    system_instruction: str | None = None
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    top_p: float = Field(default=0.95, ge=0.0, le=1.0)
    max_tokens: int = Field(default=4096, gt=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    """Raw provider response with runtime metadata."""

    output: str
    provider: str
    model: str
    latency_ms: float
    token_usage: TokenUsage | None = None
    metadata: PromptMetadata | None = None
