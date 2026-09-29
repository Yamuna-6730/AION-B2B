from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from app.llm.models import LLMRequest, LLMResponse


class BaseLLM(ABC):
    """Abstract provider contract for every LLM backend."""

    provider_name: str
    model_name: str

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate raw model output for a provider-neutral request."""

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Return provider health information without raising on expected failures."""

    @abstractmethod
    async def count_tokens(self, prompt: str) -> int:
        """Count prompt tokens using provider-native accounting when available."""

    @abstractmethod
    async def validate_output(self, output: str, schema: type[BaseModel] | None = None) -> bool:
        """Validate raw output at the provider boundary when needed."""
