from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256

from app.core.logger import llm_logger


@dataclass(slots=True)
class CacheEntry:
    response: str
    timestamp: datetime
    ttl_seconds: int

    def is_expired(self) -> bool:
        return datetime.now(UTC) >= self.timestamp + timedelta(seconds=self.ttl_seconds)


class LLMCache:
    """Small in-memory prompt cache intended to be replaced by Redis later."""

    def __init__(self, default_ttl_seconds: int = 300) -> None:
        self.default_ttl_seconds = default_ttl_seconds
        self._entries: dict[str, CacheEntry] = {}

    def build_key(self, prompt: str) -> str:
        return sha256(prompt.encode("utf-8")).hexdigest()

    def get(self, prompt: str) -> str | None:
        cache_key = self.build_key(prompt)
        entry = self._entries.get(cache_key)
        if entry is None:
            llm_logger.info("LLM cache miss", cache_key=cache_key)
            return None
        if entry.is_expired():
            self._entries.pop(cache_key, None)
            llm_logger.info("LLM cache miss", cache_key=cache_key, reason="expired")
            return None
        llm_logger.info("LLM cache hit", cache_key=cache_key)
        return entry.response

    def set(self, prompt: str, response: str, ttl_seconds: int | None = None) -> str:
        cache_key = self.build_key(prompt)
        self._entries[cache_key] = CacheEntry(
            response=response,
            timestamp=datetime.now(UTC),
            ttl_seconds=ttl_seconds or self.default_ttl_seconds,
        )
        return cache_key

    def clear(self) -> None:
        self._entries.clear()
