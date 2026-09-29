from __future__ import annotations

import asyncio
import time
from typing import Any, Protocol

import httpx

from app.core.config import settings
from app.core.logger import app_logger
from app.schemas.external import ScrapeResponse, ScrapedPage


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


class FirecrawlService:
    """Reusable async wrapper for Firecrawl page scraping."""

    provider = "firecrawl"
    base_url = "https://api.firecrawl.dev/v1/scrape"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        client: AsyncPostClient | None = None,
        timeout_seconds: float | None = None,
        max_retries: int = 2,
        backoff_seconds: float = 0.5,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.firecrawl_api_key
        self.client = client
        self.timeout_seconds = float(timeout_seconds or settings.request_timeout_seconds)
        self.max_retries = max(max_retries, 0)
        self.backoff_seconds = max(backoff_seconds, 0)

    async def scrape(self, url: str) -> ScrapeResponse:
        cleaned_url = url.strip()
        started = time.perf_counter()
        if not cleaned_url:
            return self._response(url=url, status="empty", started=started)
        if not self.api_key:
            return self._response(url=cleaned_url, status="error", started=started, error="FIRECRAWL_API_KEY is not configured.")

        payload = {
            "url": cleaned_url,
            "formats": ["markdown", "html", "links"],
            "onlyMainContent": True,
        }
        response_payload = await self._post_with_retries(cleaned_url, payload)
        if response_payload is None:
            return self._response(url=cleaned_url, status="error", started=started, error="Firecrawl scrape failed.")

        page = self._normalize_page(cleaned_url, response_payload)
        status = "ok" if page and (page.content or page.title or page.description) else "empty"
        return self._response(url=cleaned_url, page=page, status=status, started=started)

    async def scrape_multiple(self, urls: list[str]) -> list[ScrapeResponse]:
        return await asyncio.gather(*(self.scrape(url) for url in urls))

    async def _post_with_retries(self, url: str, payload: dict[str, Any]) -> dict[str, Any] | None:
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
                    url=url,
                    attempt=attempt + 1,
                    status="retrying" if attempt < self.max_retries else "error",
                    error=last_error,
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(self.backoff_seconds * (2**attempt))
        return None

    async def _client_post(self, payload: dict[str, Any]) -> Any:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.client is not None:
            return await self.client.post(self.base_url, json=payload, headers=headers, timeout=self.timeout_seconds)
        async with httpx.AsyncClient() as client:
            return await client.post(self.base_url, json=payload, headers=headers, timeout=self.timeout_seconds)

    def _normalize_page(self, url: str, payload: dict[str, Any]) -> ScrapedPage:
        data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
        metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
        links = data.get("links") if isinstance(data.get("links"), list) else []
        return ScrapedPage(
            title=str(data.get("title") or metadata.get("title") or ""),
            description=str(data.get("description") or metadata.get("description") or ""),
            content=str(data.get("markdown") or data.get("content") or data.get("html") or ""),
            metadata=metadata,
            links=[str(link) for link in links],
            url=str(data.get("url") or metadata.get("sourceURL") or url),
            source=self.provider,
        )

    def _response(
        self,
        *,
        url: str,
        started: float,
        page: ScrapedPage | None = None,
        status: str = "ok",
        error: str | None = None,
    ) -> ScrapeResponse:
        latency_ms = (time.perf_counter() - started) * 1000
        app_logger.info(
            "External provider request completed",
            provider=self.provider,
            url=url,
            latency=latency_ms,
            status=status,
        )
        return ScrapeResponse(
            url=url,
            page=page,
            status=status,  # type: ignore[arg-type]
            latency_ms=latency_ms,
            error=error,
        )
