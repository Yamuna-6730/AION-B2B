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
from app.schemas.business_dna import BusinessDNAExtractionResult, BusinessDNAOutput, BusinessDNAProfile


class BusinessDNAAgentError(AionError):
    error_code = "BUSINESS_DNA_AGENT_ERROR"


class BusinessDNAValidationError(BusinessDNAAgentError):
    status_code = 422
    error_code = "BUSINESS_DNA_VALIDATION_ERROR"


class BusinessDNAAgent(BaseAgent):
    """Transforms raw market discovery data into deep Business DNA company profiles."""

    name = "business_dna"
    description = "Produces structured Business DNA intelligence profiles for each discovered company."
    category = "intelligence"
    version = "0.1.0"
    priority = 3
    supported_inputs = ("mission", "strategy", "icp", "market_discovery", "shared_memory")
    supported_outputs = ("business_dna",)

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
            raise BusinessDNAValidationError("Business DNA agent requires a mission_id.")

        shared_memory = task.context.get("shared_memory") or {}
        mission = task.context.get("mission") or {}
        market_discovery = task.context.get("market_discovery") or shared_memory.get("market_discovery") or {}

        scraped_pages = market_discovery.get("scraped_pages") or []
        companies_raw = market_discovery.get("companies") or []
        queries = market_discovery.get("queries") or []

        agent_logger.info(
            "Business DNA started",
            mission_id=task.mission_id,
            scraped_pages=len(scraped_pages),
            companies_from_market=len(companies_raw),
        )

        profiles: list[BusinessDNAProfile] = []

        # Process each scraped page individually for maximum extraction quality
        for idx, page in enumerate(scraped_pages, start=1):
            url = page.get("url") if isinstance(page, dict) else None
            agent_logger.info("Business DNA processing page", index=idx, url=url)
            try:
                memory_payload: dict[str, Any] = {
                    "scraped_page": page,
                    "market_companies": companies_raw,
                }
                result = await self.ai_runtime.generate_json(
                    response_model=BusinessDNAExtractionResult,
                    system_role=(
                        "You are a Business Intelligence AI that extracts deep company profiles "
                        "from scraped website content. Return structured JSON only."
                    ),
                    mission=self._mission_context(mission),
                    memory=memory_payload,
                    agent_name=self.name,
                    expected_schema=BusinessDNAExtractionResult,
                    template_name="business_dna",
                    temperature=float(task.parameters.get("temperature", 0.0)),
                    top_p=0.95,
                    max_tokens=int(task.parameters.get("max_tokens", 4096)),
                    use_cache=False,
                )
                page_profiles = result.profiles if result else []
                for profile in page_profiles:
                    agent_logger.info(
                        "Business DNA profile extracted",
                        company=profile.company_name,
                        website=profile.website,
                        confidence=profile.confidence,
                    )
                profiles.extend(page_profiles)
            except Exception as exc:
                agent_logger.error("Business DNA page extraction failed", url=url, error=str(exc))
                continue

        # Deduplicate by website
        profiles = self._deduplicate_profiles(profiles)
        if not profiles and companies_raw:
            profiles = self._fallback_profiles(companies_raw)

        execution_time = time.perf_counter() - started
        output = BusinessDNAOutput(
            profiles=profiles,
            profile_count=len(profiles),
            execution_time=execution_time,
            queries=queries,
        )

        agent_logger.info(
            "Business DNA completed",
            mission_id=task.mission_id,
            profiles=len(profiles),
            execution_time=execution_time,
        )

        return AgentResponse(
            success=True,
            mission_id=task.mission_id,
            task_id=task.task_id,
            agent_name=self.name,
            status=AgentState.COMPLETED,
            confidence=self._average_confidence(profiles),
            reasoning=f"Generated {len(profiles)} Business DNA profiles from market discovery evidence.",
            evidence=[],
            execution_time=execution_time,
            metadata={"profile_count": len(profiles)},
            output=output.model_dump(mode="json"),
        )

    async def summarize(self, response: AgentResponse) -> str:
        count = response.output.get("profile_count", 0)
        return f"Generated {count} Business DNA intelligence profiles."

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
        icp = mission.get("icp") or {}
        if icp.get("company_size"):
            parts.append(f"Target company size: {icp['company_size']}")
        if icp.get("industries"):
            parts.append(f"Target industries: {', '.join(icp['industries']) if isinstance(icp['industries'], list) else icp['industries']}")
        return "\n".join(parts) if parts else "General business intelligence mission."

    def _deduplicate_profiles(self, profiles: list[BusinessDNAProfile]) -> list[BusinessDNAProfile]:
        seen: dict[str, BusinessDNAProfile] = {}
        for profile in profiles:
            key = (profile.website or "").strip().lower().rstrip("/")
            if not key:
                key = profile.company_name.strip().lower()
            if key not in seen:
                seen[key] = profile
        return list(seen.values())

    def _average_confidence(self, profiles: list[BusinessDNAProfile]) -> float:
        if not profiles:
            return 0.0
        return round(sum(p.confidence for p in profiles) / len(profiles), 3)

    def _fallback_profiles(self, companies: list[Any]) -> list[BusinessDNAProfile]:
        profiles: list[BusinessDNAProfile] = []
        for company in companies:
            if not isinstance(company, dict):
                continue
            profiles.append(
                BusinessDNAProfile(
                    company_name=str(company.get("company_name") or company.get("title") or "Unknown company"),
                    website=str(company.get("website") or company.get("url") or ""),
                    industry=company.get("industry"),
                    country=company.get("country"),
                    business_summary=company.get("summary"),
                    technology_signals=company.get("technologies") or [],
                    use_cases=company.get("use_cases") or [],
                    strengths=company.get("strengths") or ["Discovered from market evidence"],
                    risks=company.get("risks") or ["Requires manual validation because profile used fallback extraction"],
                    evidence=company.get("evidence") or [],
                    confidence=0.35,
                    reasoning="Fallback profile generated from market discovery evidence because Business DNA LLM extraction produced no profiles.",
                )
            )
        return self._deduplicate_profiles(profiles)
