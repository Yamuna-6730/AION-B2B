from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MarketDiscoverySchemaBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class CompanyEvidence(MarketDiscoverySchemaBase):
    source: str
    url: str
    fact: str


class DiscoveredCompany(MarketDiscoverySchemaBase):
    company_name: str
    website: str
    summary: str | None = None
    industry: str | None = None
    country: str | None = None
    headquarters: str | None = None
    products: list[str] = Field(default_factory=list)
    services: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    customer_logos: list[str] = Field(default_factory=list)
    use_cases: list[str] = Field(default_factory=list)
    careers_page: str | None = None
    about_page: str | None = None
    evidence: list[CompanyEvidence] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CompanyExtractionResult(MarketDiscoverySchemaBase):
    companies: list[DiscoveredCompany] = Field(default_factory=list)



class MarketDiscoveryOutput(MarketDiscoverySchemaBase):
    companies: list[DiscoveredCompany] = Field(default_factory=list)
    search_queries: list[str] = Field(default_factory=list)
    queries: list[str] = Field(default_factory=list)
    raw_tavily_results: list[dict[str, Any]] = Field(default_factory=list)
    scraped_pages: list[dict[str, Any]] = Field(default_factory=list)
    total_companies: int = 0
    company_count: int = 0
    execution_time: float = 0.0


class MarketDiscoveryDatabaseStatus(MarketDiscoverySchemaBase):
    saved: bool = False
    verified: bool = False
    table_name: str = "market_discovery_results"
    rows: int = 0


class MarketDiscoveryRunRequest(MarketDiscoverySchemaBase):
    mission_id: UUID


class MarketDiscoveryRunResponse(MarketDiscoverySchemaBase):
    mission_id: str
    status: str
    companies: list[DiscoveredCompany] = Field(default_factory=list)
    market_discovery: MarketDiscoveryOutput
    shared_memory: dict[str, Any] = Field(default_factory=dict)
    runtime: float = 0.0
    saved_company_count: int = 0
    database_status: MarketDiscoveryDatabaseStatus = Field(default_factory=MarketDiscoveryDatabaseStatus)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
