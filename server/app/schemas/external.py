from __future__ import annotations

from typing import Any, Literal

from pydantic import AnyUrl, BaseModel, ConfigDict, Field


class ExternalSchemaBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SearchResult(ExternalSchemaBase):
    title: str = ""
    url: str = ""
    content: str = ""
    score: float = 0.0
    source: str = ""


class SearchResponse(ExternalSchemaBase):
    provider: Literal["tavily"] = "tavily"
    query: str
    results: list[SearchResult] = Field(default_factory=list)
    status: Literal["ok", "empty", "error"] = "ok"
    latency_ms: float = 0.0
    error: str | None = None


class ScrapedPage(ExternalSchemaBase):
    title: str = ""
    description: str = ""
    content: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    links: list[str] = Field(default_factory=list)
    url: str = ""
    source: str = ""


class ScrapeResponse(ExternalSchemaBase):
    provider: Literal["firecrawl"] = "firecrawl"
    url: str
    page: ScrapedPage | None = None
    status: Literal["ok", "empty", "error"] = "ok"
    latency_ms: float = 0.0
    error: str | None = None


class UrlInput(ExternalSchemaBase):
    url: AnyUrl
