from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BusinessDNASchemaBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class BusinessDNAProfile(BusinessDNASchemaBase):
    company_name: str
    website: str
    industry: str | None = None
    company_type: str | None = None
    country: str | None = None
    business_summary: str | None = None
    estimated_company_size: str | None = None
    estimated_ai_maturity: str | None = None
    technology_signals: list[str] = Field(default_factory=list)
    digital_transformation_signals: list[str] = Field(default_factory=list)
    buying_personas: list[str] = Field(default_factory=list)
    use_cases: list[str] = Field(default_factory=list, alias="likely_use_cases")
    strengths: list[str] = Field(default_factory=list, alias="business_strengths")
    risks: list[str] = Field(default_factory=list, alias="business_risks")
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reasoning: str | None = None


class BusinessDNAExtractionResult(BusinessDNASchemaBase):
    profiles: list[BusinessDNAProfile] = Field(default_factory=list)


class BusinessDNAOutput(BusinessDNASchemaBase):
    profiles: list[BusinessDNAProfile] = Field(default_factory=list)
    profile_count: int = 0
    execution_time: float = 0.0
    queries: list[str] = Field(default_factory=list)


class BusinessDNADatabaseStatus(BusinessDNASchemaBase):
    saved: bool = False
    verified: bool = False
    table_name: str = "business_dna_results"
    rows: int = 0


class BusinessDNARunRequest(BusinessDNASchemaBase):
    mission_id: UUID


class BusinessDNARunResponse(BusinessDNASchemaBase):
    mission_id: str
    status: str
    business_dna: BusinessDNAOutput
    shared_memory: dict[str, Any] = Field(default_factory=dict)
    database_status: BusinessDNADatabaseStatus = Field(default_factory=BusinessDNADatabaseStatus)
    runtime: float = 0.0
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
