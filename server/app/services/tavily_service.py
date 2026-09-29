from __future__ import annotations

import asyncio
import time
from typing import Any, Protocol

import httpx

from app.core.config import settings
from app.core.logger import app_logger
from app.schemas.external import SearchResponse, SearchResult


class AsyncPostClient(Protocol):
    async def post(
        self,
        url: str,
        *,
        json: dict[str, Any],
        headers: dict[str, str],
        timeout: float,
    ) -> Any:
        ...


class TavilyService:
    """Reusable async wrapper for Tavily search data collection."""

    provider = "tavily"
    base_url = "https://api.tavily.com/search"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        client: AsyncPostClient | None = None,
        timeout_seconds: float | None = None,
        max_retries: int = 2,
        backoff_seconds: float = 0.5,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.tavily_api_key
        self.client = client
        self.timeout_seconds = float(timeout_seconds or settings.request_timeout_seconds)
        self.max_retries = max(max_retries, 0)
        self.backoff_seconds = max(backoff_seconds, 0)

    async def search(self, query: str) -> SearchResponse:
        cleaned_query = query.strip()
        started = time.perf_counter()
        if not cleaned_query:
            return self._response(query=query, status="empty", started=started)
        if not self.api_key:
            return self._response(query=cleaned_query, status="error", started=started, error="TAVILY_API_KEY is not configured.")

        payload = {
            "api_key": self.api_key,
            "query": cleaned_query,
            "search_depth": "advanced",
            "include_answer": False,
            "include_raw_content": False,
            "max_results": 10,
        }
        response_payload = await self._post_with_retries(cleaned_query, payload)
        if response_payload is None:
            return self._response(query=cleaned_query, status="error", started=started, error="Tavily search failed.")

        results = [self._normalize_result(item) for item in response_payload.get("results", []) if isinstance(item, dict)]
        status = "ok" if results else "empty"
        return self._response(query=cleaned_query, results=results, status=status, started=started)

    async def search_multiple(self, queries: list[str]) -> list[SearchResponse]:
        return await asyncio.gather(*(self.search(query) for query in queries))

    async def search_company(self, company_name: str) -> SearchResponse:
        return await self.search(f"{company_name.strip()} company overview business signals")

    async def search_news(self, company_name: str) -> SearchResponse:
        return await self.search(f"{company_name.strip()} latest company news")

    async def _post_with_retries(self, query: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        last_error: str | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = await self._client_post(payload)
                if hasattr(response, "raise_for_status"):
                    response.raise_for_status()
                data = response.json()
                return data if isinstance(data, dict) else None
            except Exception as exc:
                last_error = str(exc)
                app_logger.warning(
                    "External provider request failed",
                    provider=self.provider,
                    query=query,
                    attempt=attempt + 1,
                    status="retrying" if attempt < self.max_retries else "error",
                    error=last_error,
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(self.backoff_seconds * (2**attempt))
        return None

    async def _client_post(self, payload: dict[str, Any]) -> Any:
        headers = {"Content-Type": "application/json"}
        if self.client is not None:
            return await self.client.post(self.base_url, json=payload, headers=headers, timeout=self.timeout_seconds)
        async with httpx.AsyncClient() as client:
            return await client.post(self.base_url, json=payload, headers=headers, timeout=self.timeout_seconds)

    def _normalize_result(self, item: dict[str, Any]) -> SearchResult:
        return SearchResult(
            title=str(item.get("title") or ""),
            url=str(item.get("url") or ""),
            content=str(item.get("content") or item.get("raw_content") or ""),
            score=float(item.get("score") or 0.0),
            source=self.provider,
        )

    def _response(
        self,
        *,
        query: str,
        started: float,
        results: list[SearchResult] | None = None,
        status: str = "ok",
        error: str | None = None,
    ) -> SearchResponse:
        latency_ms = (time.perf_counter() - started) * 1000
        app_logger.info(
            "External provider request completed",
            provider=self.provider,
            query=query,
            latency=latency_ms,
            status=status,
        )
        return SearchResponse(
            query=query,
            results=results or [],
            status=status,  # type: ignore[arg-type]
            latency_ms=latency_ms,
            error=error,
        )
