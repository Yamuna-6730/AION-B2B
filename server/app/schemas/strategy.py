from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class StrategySchemaBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class MissionStatus(StrEnum):
    CREATED = "CREATED"
    STRATEGY_RUNNING = "STRATEGY_RUNNING"
    STRATEGY_COMPLETED = "STRATEGY_COMPLETED"
    STRATEGY_FAILED = "STRATEGY_FAILED"
    PLANNER_RUNNING = "PLANNER_RUNNING"
    PLANNER_COMPLETED = "PLANNER_COMPLETED"
    EXECUTING_AGENTS = "EXECUTING_AGENTS"
    EXECUTION_RUNNING = "EXECUTION_RUNNING"
    RECOMMENDATION_RUNNING = "RECOMMENDATION_RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class StrategyAnalyzeRequest(StrategySchemaBase):
    title: str = Field(
        min_length=1,
        examples=["Find AI Customers"],
    )
    objective: str = Field(
        min_length=1,
        examples=["We sell an Enterprise AI Platform. Find Manufacturing companies in Germany likely to purchase AI."],
    )


class MissionMetadata(StrategySchemaBase):
    source: str = "strategy_agent"
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    assumptions: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class ICPProfile(StrategySchemaBase):
    company_size: str
    revenue: str | None = None
    geography: list[str] = Field(default_factory=list)
    industry: str | None = None
    maturity_signals: list[str] = Field(default_factory=list)


class Persona(StrategySchemaBase):
    title: str
    seniority: str | None = None
    department: str | None = None
    pains: list[str] = Field(default_factory=list)
    buying_role: str | None = None


class BusinessTrigger(StrategySchemaBase):
    name: str
    description: str
    priority: int = Field(default=3, ge=1, le=5)


class QualificationRule(StrategySchemaBase):
    criterion: str
    operator: str = "matches"
    value: str
    rationale: str | None = None


class TechnologyPreference(StrategySchemaBase):
    technology: str
    category: str
    rationale: str | None = None


class RecommendedAgent(StrategySchemaBase):
    name: str
    reason: str
    priority: int = Field(default=3, ge=1, le=5)


class MissionIntelligence(StrategySchemaBase):
    mission_id: str = Field(default_factory=lambda: f"mission_{uuid4().hex}")
    title: str
    objective: str
    domain: str
    industry: str
    countries: list[str] = Field(default_factory=list)
    product: str
    product_category: str
    ideal_company_size: str
    estimated_revenue: str | None = None
    icp: ICPProfile
    target_personas: list[Persona] = Field(default_factory=list)
    technology_preferences: list[TechnologyPreference] = Field(default_factory=list)
    qualification_rules: list[QualificationRule] = Field(default_factory=list)
    business_triggers: list[BusinessTrigger] = Field(default_factory=list)
    recommended_agents: list[RecommendedAgent] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    metadata: MissionMetadata = Field(default_factory=MissionMetadata)


class StrategyOutput(StrategySchemaBase):
    mission: MissionIntelligence
    status: MissionStatus = MissionStatus.STRATEGY_COMPLETED
