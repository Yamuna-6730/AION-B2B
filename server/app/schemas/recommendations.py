from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RecommendationSchemaBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ScoredCompany(RecommendationSchemaBase):
    company_name: str
    website: str
    priority_score: float = Field(default=0.0, ge=0.0, le=1.0)
    priority: str = "MEDIUM"  # HIGH / MEDIUM / LOW
    rank: int = 0
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    why_selected: str | None = None
    strengths: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    recommended_personas: list[str] = Field(default_factory=list)
    recommended_use_cases: list[str] = Field(default_factory=list)
    next_action: str | None = None
    scoring_breakdown: dict[str, float] = Field(default_factory=dict, alias="score_breakdown")


class RecommendationExtractionResult(RecommendationSchemaBase):
    companies: list[ScoredCompany] = Field(default_factory=list)


class RecommendationOutput(RecommendationSchemaBase):
    companies: list[ScoredCompany] = Field(default_factory=list)
    company_count: int = 0
    execution_time: float = 0.0


class RecommendationDatabaseStatus(RecommendationSchemaBase):
    saved: bool = False
    verified: bool = False
    table_name: str = "recommendation_results"
    rows: int = 0


class RecommendationRunRequest(RecommendationSchemaBase):
    mission_id: UUID


class RecommendationRunResponse(RecommendationSchemaBase):
    mission_id: str
    status: str
    recommendations: RecommendationOutput
    shared_memory: dict[str, Any] = Field(default_factory=dict)
    database_status: RecommendationDatabaseStatus = Field(default_factory=RecommendationDatabaseStatus)
    runtime: float = 0.0
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
