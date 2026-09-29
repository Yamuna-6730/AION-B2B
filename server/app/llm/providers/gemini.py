from __future__ import annotations

import asyncio
import time
from typing import Any

from pydantic import BaseModel

from app.core.logger import llm_logger
from app.llm.base import BaseLLM
from app.llm.exceptions import AuthenticationError, ProviderError, RateLimitError
from app.llm.models import LLMRequest, LLMResponse, TokenUsage


class GeminiProvider(BaseLLM):
    """Google Gemini provider implementation."""

    provider_name = "gemini"

    def __init__(self, *, api_key: str | None, model_name: str) -> None:
        self.api_key = api_key
        self.model_name = model_name
        self._genai: Any | None = None

    async def generate(self, request: LLMRequest) -> LLMResponse:
        if not self.api_key:
            raise AuthenticationError("GOOGLE_API_KEY is required for Gemini.")

        started = time.perf_counter()
        try:
            genai = self._load_client()
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(
                self.model_name,
                system_instruction=request.system_instruction,
            )
            response = await model.generate_content_async(
                request.prompt,
                generation_config={
                    "temperature": request.temperature,
                    "top_p": request.top_p,
                    "max_output_tokens": request.max_tokens,
                    "response_mime_type": "application/json",
                },
            )
            output = self._extract_text(response)
            print("\n" + "=" * 80)
            print("GEMINI RAW RESPONSE")
            print("=" * 80)

            print(output)

            print("=" * 80 + "\n")
            
            llm_logger.debug(
                "Gemini raw response extracted",
                provider=self.provider_name,
                model=self.model_name,
                raw_response=repr(response),
                text=output,
            )
            latency_ms = (time.perf_counter() - started) * 1000
            token_usage = self._extract_usage(response)
            llm_logger.info(
                "LLM provider request completed",
                provider=self.provider_name,
                model=self.model_name,
                latency_ms=latency_ms,
                tokens=token_usage.model_dump() if token_usage else None,
            )
            return LLMResponse(
                output=output,
                provider=self.provider_name,
                model=self.model_name,
                latency_ms=latency_ms,
                token_usage=token_usage,
            )
        except AuthenticationError:
            raise
        except Exception as exc:
            message = str(exc).lower()
            if "rate" in message and "limit" in message:
                raise RateLimitError(str(exc)) from exc
            raise ProviderError(f"Gemini request failed: {exc}") from exc

    async def health_check(self) -> dict[str, Any]:
        started = time.perf_counter()
        try:
            if not self.api_key:
                return self._health_payload("unhealthy", started, error="missing GOOGLE_API_KEY")
            await self.count_tokens("health")
            return self._health_payload("ok", started)
        except Exception as exc:
            llm_logger.error(
                "LLM provider health check failed",
                provider=self.provider_name,
                model=self.model_name,
                error=str(exc),
            )
            return self._health_payload("unhealthy", started, error=str(exc))

    async def count_tokens(self, prompt: str) -> int:
        if not self.api_key:
            raise AuthenticationError("GOOGLE_API_KEY is required for Gemini.")
        genai = self._load_client()
        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(self.model_name)
        result = await asyncio.to_thread(model.count_tokens, prompt)
        return int(getattr(result, "total_tokens", 0))

    async def validate_output(self, output: str, schema: type[BaseModel] | None = None) -> bool:
        if schema is None:
            return bool(output.strip())
        try:
            schema.model_validate_json(output)
        except ValueError:
            return False
        return True

    def _load_client(self) -> Any:
        if self._genai is not None:
            return self._genai
        try:
            import google.generativeai as genai
        except ImportError as exc:
            raise ProviderError("google-generativeai is not installed.") from exc
        self._genai = genai
        return genai

    def _extract_text(self, response: Any) -> str:
        try:
            text = getattr(response, "text", None)
        except Exception as exc:
            llm_logger.error(
                "Gemini response text accessor failed",
                error=str(exc),
                raw_response=repr(response),
            )
            text = None
        if isinstance(text, str) and text.strip():
            return text
        candidate_text = self._extract_candidate_text(response)
        if candidate_text:
            return candidate_text
        llm_logger.error("Gemini response did not include text output", raw_response=repr(response))
        raise ProviderError("Gemini response did not include text output.")

    def _extract_candidate_text(self, response: Any) -> str | None:
        candidates = getattr(response, "candidates", None) or []
        parts: list[str] = []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            for part in getattr(content, "parts", None) or []:
                text = getattr(part, "text", None)
                if isinstance(text, str):
                    parts.append(text)
        output = "".join(parts).strip()
        if output:
            llm_logger.debug("Gemini response text extracted from candidate parts", text=output)
            return output
        return None

    def _extract_usage(self, response: Any) -> TokenUsage | None:
        usage = getattr(response, "usage_metadata", None)
        if usage is None:
            return None
        prompt_tokens = getattr(usage, "prompt_token_count", None)
        completion_tokens = getattr(usage, "candidates_token_count", None)
        total_tokens = getattr(usage, "total_token_count", None)
        return TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

    def _health_payload(
        self,
        status: str,
        started: float,
        *,
        error: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "provider": self.provider_name,
            "model": self.model_name,
            "status": status,
            "latency": round((time.perf_counter() - started) * 1000, 2),
        }
        if error:
            payload["error"] = error
        return payload
