from __future__ import annotations

import time
from typing import Any, TypeVar

from pydantic import BaseModel

from app.core.logger import llm_logger
from app.llm.base import BaseLLM
from app.llm.cache import LLMCache
from app.llm.factory import LLMFactory
from app.llm.models import LLMRequest, LLMResponse, PromptMetadata
from app.llm.parser import LLMParser
from app.llm.prompt_engine import PromptEngine

ModelT = TypeVar("ModelT", bound=BaseModel)


class LLMManager:
    """Single entry point for every agent-facing LLM interaction."""

    def __init__(
        self,
        *,
        provider: BaseLLM | None = None,
        factory: LLMFactory | None = None,
        prompt_engine: PromptEngine | None = None,
        parser: LLMParser | None = None,
        cache: LLMCache | None = None,
    ) -> None:
        self.provider = provider or (factory or LLMFactory()).create()
        self.prompt_engine = prompt_engine or PromptEngine()
        self.parser = parser or LLMParser()
        self.cache = cache or LLMCache()

    async def generate(
        self,
        *,
        system_role: str,
        mission: str,
        memory: str | dict[str, Any] | list[Any] | None,
        agent_name: str,
        expected_schema: type[BaseModel] | BaseModel | dict[str, Any] | str,
        template_name: str,
        temperature: float = 0.2,
        top_p: float = 0.95,
        max_tokens: int = 4096,
        use_cache: bool = True,
    ) -> LLMResponse:
        prompt = self.prompt_engine.build_prompt(
            system_role=system_role,
            mission=mission,
            memory=memory,
            agent_name=agent_name,
            expected_schema=expected_schema,
            template_name=template_name,
        )
        llm_logger.debug(
            "LLM manager built prompt",
            agent_name=agent_name,
            template_name=template_name,
            prompt=prompt,
        )
        cache_key = self.cache.build_key(prompt)
        metadata = PromptMetadata(
            agent_name=agent_name,
            template_name=template_name,
            provider=self.provider.provider_name,
            model=self.provider.model_name,
            cache_key=cache_key,
        )

        if use_cache:
            cached = self.cache.get(prompt)
            if cached is not None:
                metadata.cache_hit = True
                return LLMResponse(
                    output=cached,
                    provider=self.provider.provider_name,
                    model=self.provider.model_name,
                    latency_ms=0,
                    metadata=metadata,
                )

        started = time.perf_counter()
        response = await self.provider.generate(
            LLMRequest(
                prompt=prompt,
                system_instruction=system_role,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
            )
        )
        response.metadata = metadata
        if use_cache:
            self.cache.set(prompt, response.output)
        llm_logger.info(
            "LLM manager request completed",
            provider=response.provider,
            model=response.model,
            latency_ms=(time.perf_counter() - started) * 1000,
            tokens=response.token_usage.model_dump() if response.token_usage else None,
            cache_hit=False,
        )
        return response

    async def generate_json(
        self,
        *,
        response_model: type[ModelT],
        system_role: str,
        mission: str,
        memory: str | dict[str, Any] | list[Any] | None,
        agent_name: str,
        expected_schema: type[BaseModel] | BaseModel | dict[str, Any] | str,
        template_name: str,
        temperature: float = 0.2,
        top_p: float = 0.95,
        max_tokens: int = 4096,
        use_cache: bool = True,
    ) -> ModelT:
        response = await self.generate(
            system_role=system_role,
            mission=mission,
            memory=memory,
            agent_name=agent_name,
            expected_schema=expected_schema,
            template_name=template_name,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            use_cache=use_cache,
        )
        llm_logger.debug(
            "LLM manager raw response before parsing",
            agent_name=agent_name,
            template_name=template_name,
            output=response.output,
        )
        return self.parser.parse_json(response.output, response_model)

    async def health_check(self) -> dict[str, Any]:
        return await self.provider.health_check()


llm_manager = LLMManager()
