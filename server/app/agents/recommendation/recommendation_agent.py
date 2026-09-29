from __future__ import annotations

import time
from typing import Any

from app.agents.base.base_agent import BaseAgent
from app.agents.base.enums import AgentState
from app.agents.base.response import AgentResponse
from app.agents.base.task import AgentTask
from app.core.exceptions import AionError
from app.core.logger import agent_logger
from app.llm import LLMManager, llm_manager
from app.schemas.recommendations import RecommendationExtractionResult, RecommendationOutput, ScoredCompany


class RecommendationAgentError(AionError):
    error_code = "RECOMMENDATION_AGENT_ERROR"


class RecommendationValidationError(RecommendationAgentError):
    status_code = 422
    error_code = "RECOMMENDATION_VALIDATION_ERROR"


class RecommendationAgent(BaseAgent):
    """Scores and ranks discovered companies against mission ICP to produce prioritised recommendations."""

    name = "recommendation"
    description = "Scores and ranks candidate companies against mission ICP and strategy, producing actionable recommendations."
    category = "recommendation"
    version = "0.1.0"
    priority = 4
    supported_inputs = ("mission", "strategy", "icp", "business_dna", "market_discovery", "shared_memory")
    supported_outputs = ("recommendations",)

    def __init__(self, *, ai_runtime: LLMManager | None = None) -> None:
        self.ai_runtime = ai_runtime or llm_manager

    async def initialize(self) -> None:
        return None

    async def validate(self, task: AgentTask) -> bool:
        if task.agent_name and task.agent_name != self.name:
            return False
        return bool(task.mission_id)

    async def run(self, task: AgentTask) -> AgentResponse:
        started = time.perf_counter()
        if not await self.validate(task):
            raise RecommendationValidationError("Recommendation agent requires a mission_id.")

        shared_memory = task.context.get("shared_memory") or {}
        mission = task.context.get("mission") or {}
        business_dna = task.context.get("business_dna") or shared_memory.get("business_dna") or {}
        market_discovery = task.context.get("market_discovery") or shared_memory.get("market_discovery") or {}

        profiles = business_dna.get("profiles") or []
        companies_raw = market_discovery.get("companies") or []

        agent_logger.info(
            "Recommendation agent started",
            mission_id=task.mission_id,
            profiles=len(profiles),
            market_companies=len(companies_raw),
        )

        if not profiles:
            agent_logger.warning(
                "Recommendation agent found no Business DNA profiles",
                mission_id=task.mission_id,
            )
            companies: list[ScoredCompany] = []
        else:
            memory_payload: dict[str, Any] = {
                "business_dna_profiles": profiles,
                "market_discovery_companies": companies_raw,
            }
            try:
                result = await self.ai_runtime.generate_json(
                    response_model=RecommendationExtractionResult,
                    system_role=(
                        "You are a B2B Sales Intelligence AI. Rank and score each company "
                        "based on ICP and mission fit. Return structured JSON only."
                    ),
                    mission=self._mission_context(mission),
                    memory=memory_payload,
                    agent_name=self.name,
                    expected_schema=RecommendationExtractionResult,
                    template_name="recommendation",
                    temperature=float(task.parameters.get("temperature", 0.0)),
                    top_p=0.95,
                    max_tokens=int(task.parameters.get("max_tokens", 8192)),
                    use_cache=False,
                )
                companies = result.companies if result else []
            except Exception as exc:
                agent_logger.error("Recommendation extraction failed", mission_id=task.mission_id, error=str(exc))
                companies = []
            if not companies:
                companies = self._fallback_recommendations(profiles)

        # Ensure clean ranking
        companies = self._rank_companies(companies)

        execution_time = time.perf_counter() - started
        output = RecommendationOutput(
            companies=companies,
            company_count=len(companies),
            execution_time=execution_time,
        )

        agent_logger.info(
            "Recommendation agent completed",
            mission_id=task.mission_id,
            companies=len(companies),
            execution_time=execution_time,
        )

        return AgentResponse(
            success=True,
            mission_id=task.mission_id,
            task_id=task.task_id,
            agent_name=self.name,
            status=AgentState.COMPLETED,
            confidence=self._average_confidence(companies),
            reasoning=f"Ranked {len(companies)} companies by ICP fit and mission alignment.",
            evidence=[],
            execution_time=execution_time,
            metadata={"company_count": len(companies)},
            output=output.model_dump(mode="json"),
        )

    async def summarize(self, response: AgentResponse) -> str:
        count = response.output.get("company_count", 0)
        return f"Produced recommendations for {count} companies."

    async def calculate_confidence(self, response: AgentResponse) -> float:
        return response.confidence

    async def cleanup(self) -> None:
        return None

    def _mission_context(self, mission: dict[str, Any]) -> str:
        parts = []
        if mission.get("objective"):
            parts.append(f"Objective: {mission['objective']}")
        strategy = mission.get("strategy") or {}
        if strategy.get("domain"):
            parts.append(f"Domain: {strategy['domain']}")
        if strategy.get("industry"):
            parts.append(f"Industry: {strategy['industry']}")
        if strategy.get("value_proposition"):
            parts.append(f"Value proposition: {strategy['value_proposition']}")
        icp = mission.get("icp") or {}
        if icp.get("company_size"):
            parts.append(f"Target company size: {icp['company_size']}")
        if icp.get("industries"):
            industries = icp["industries"]
            parts.append(f"Target industries: {', '.join(industries) if isinstance(industries, list) else industries}")
        if icp.get("target_personas"):
            personas = icp["target_personas"]
            parts.append(f"Target personas: {', '.join(personas) if isinstance(personas, list) else personas}")
        return "\n".join(parts) if parts else "General business recommendation mission."

    def _rank_companies(self, companies: list[ScoredCompany]) -> list[ScoredCompany]:
        sorted_companies = sorted(companies, key=lambda c: c.priority_score, reverse=True)
        for rank, company in enumerate(sorted_companies, start=1):
            company.rank = rank
            if company.priority_score >= 0.7:
                company.priority = "HIGH"
            elif company.priority_score >= 0.4:
                company.priority = "MEDIUM"
            else:
                company.priority = "LOW"
        return sorted_companies

    def _average_confidence(self, companies: list[ScoredCompany]) -> float:
        if not companies:
            return 0.0
        return round(sum(c.confidence for c in companies) / len(companies), 3)

    def _fallback_recommendations(self, profiles: list[Any]) -> list[ScoredCompany]:
        companies: list[ScoredCompany] = []
        for profile in profiles:
            if not isinstance(profile, dict):
                continue
            confidence = float(profile.get("confidence") or 0.35)
            companies.append(
                ScoredCompany(
                    company_name=str(profile.get("company_name") or "Unknown company"),
                    website=str(profile.get("website") or ""),
                    priority_score=min(max(confidence, 0.0), 1.0),
                    confidence=confidence,
                    why_selected="Fallback recommendation generated from Business DNA profile evidence.",
                    strengths=profile.get("strengths") or [],
                    risks=profile.get("risks") or [],
                    recommended_personas=profile.get("buying_personas") or [],
                    recommended_use_cases=profile.get("use_cases") or [],
                    next_action="Manually validate fit and enrich account research.",
                    scoring_breakdown={"profile_confidence": confidence},
                )
            )
        return companies
