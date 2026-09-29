from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.external import SearchResult


class HiringIntelligence(BaseModel):
    company: str | None = None
    roles: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    hiring_signals: list[str] = Field(default_factory=list)
    technology_signals: list[str] = Field(default_factory=list)
    expansion_signals: list[str] = Field(default_factory=list)
    sources: list[SearchResult] = Field(default_factory=list)
    researched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    confidence: float = 0.0


class FundingEvent(BaseModel):
    round: str | None = None
    amount: str | None = None
    investors: list[str] = Field(default_factory=list)
    date: str | None = None
    source_url: str | None = None


class FundingIntelligence(BaseModel):
    company: str | None = None
    funding_events: list[FundingEvent] = Field(default_factory=list)
    latest_round: str | None = None
    investors: list[str] = Field(default_factory=list)
    total_known_funding: str | None = None
    expansion_signals: list[str] = Field(default_factory=list)
    sources: list[SearchResult] = Field(default_factory=list)
    researched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    confidence: float = 0.0
