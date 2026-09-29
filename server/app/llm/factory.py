from __future__ import annotations

from app.core.config import settings
from app.llm.base import BaseLLM
from app.llm.exceptions import ProviderError
from app.llm.providers.gemini import GeminiProvider


class LLMFactory:
    """Factory for provider-neutral LLM construction."""

    def create(self, provider: str | None = None) -> BaseLLM:
        selected_provider = (provider or settings.llm_provider).strip().lower()
        if selected_provider == "gemini":
            return GeminiProvider(
                api_key=settings.google_api_key,
                model_name=settings.llm_model,
            )
        raise ProviderError(f"Unsupported LLM provider: {selected_provider}")
