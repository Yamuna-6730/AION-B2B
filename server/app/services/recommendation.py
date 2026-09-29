from __future__ import annotations

import time
from typing import Any
from uuid import uuid4

from app.agents.base.task import AgentTask
from app.agents.recommendation.recommendation_agent import RecommendationAgent
from app.core.logger import app_logger
from app.schemas.recommendations import RecommendationDatabaseStatus, RecommendationOutput, RecommendationRunResponse
from app.supabase.repositories.business_dna_repository import BusinessDNARepository
from app.supabase.repositories.market_discovery_repository import MarketDiscoveryRepository
from app.supabase.repositories.mission_repository import MissionRepository
from app.supabase.repositories.recommendation_repository import RecommendationRepository


class RecommendationService:
    """Application service for running the Recommendation pipeline."""

    def __init__(
        self,
        *,
        agent: RecommendationAgent | None = None,
        mission_repository: MissionRepository | None = None,
        market_repository: MarketDiscoveryRepository | None = None,
        business_dna_repository: BusinessDNARepository | None = None,
        recommendation_repository: RecommendationRepository | None = None,
    ) -> None:
        self.agent = agent or RecommendationAgent()
        self.mission_repository = mission_repository or MissionRepository()
        self.market_repository = market_repository or MarketDiscoveryRepository()
        self.business_dna_repository = business_dna_repository or BusinessDNARepository()
        self.recommendation_repository = recommendation_repository or RecommendationRepository()

    async def run(self, mission_id: str) -> RecommendationRunResponse:
        started = time.perf_counter()

        # Load mission
        mission = await self.mission_repository.get_mission(mission_id)

        # Load both upstream results
        market_rows = await self.market_repository.list_by_mission(mission_id)
        business_dna_rows = await self.business_dna_repository.list_by_mission(mission_id)

        app_logger.info(
            "Recommendation service loaded upstream data",
            mission_id=mission_id,
            market_rows=len(market_rows),
            dna_rows=len(business_dna_rows),
        )

        market_discovery_memory = self._build_market_memory(market_rows)
        business_dna_memory = self._build_dna_memory(business_dna_rows)

        shared_memory: dict[str, Any] = dict(mission.get("shared_memory") or {})
        shared_memory.update({
            "market_discovery": market_discovery_memory,
            "business_dna": business_dna_memory,
        })

        task = AgentTask(
            mission_id=mission_id,
            task_id=f"recommendation_{uuid4().hex}",
            agent_name=self.agent.name,
            objective=str(mission.get("objective") or ""),
            context={
                "mission": mission,
                "strategy": mission.get("strategy") or {},
                "icp": mission.get("icp") or {},
                "market_discovery": market_discovery_memory,
                "business_dna": business_dna_memory,
                "shared_memory": shared_memory,
            },
        )

        response = await self.agent.run(task)
        output = RecommendationOutput.model_validate(response.output)

        # Persist
        saved_rows = await self.recommendation_repository.save_results(mission_id, output.companies)
        database_status = RecommendationDatabaseStatus(
            saved=bool(saved_rows),
            verified=(len(saved_rows) == len(output.companies)),
            table_name=self.recommendation_repository.table_name,
            rows=len(saved_rows),
        )
        if len(saved_rows) < len(output.companies):
            database_status.verified = False
            app_logger.warning(
                "Recommendation persistence mismatch",
                expected=len(output.companies),
                saved=len(saved_rows),
                mission_id=mission_id,
            )

        # Update shared memory
        shared_memory["recommendations"] = self._shared_memory_payload(output)
        if hasattr(self.mission_repository, "update_shared_memory"):
            await self.mission_repository.update_shared_memory(mission_id, shared_memory)

        # Update mission metadata
        await self._update_mission_metadata(mission_id, mission, output, database_status)

        runtime = time.perf_counter() - started
        app_logger.info("Recommendation service completed", mission_id=mission_id, runtime=runtime)

        return RecommendationRunResponse(
            mission_id=mission_id,
            status="COMPLETED",
            recommendations=output,
            shared_memory=shared_memory,
            database_status=database_status,
            runtime=runtime,
        )

    def _build_market_memory(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        companies = []
        for row in rows:
            metadata = row.get("firecrawl_metadata") or {}
            company = metadata.get("company") if isinstance(metadata, dict) else None
            if not isinstance(company, dict):
                company = {"company_name": row.get("title"), "website": row.get("url"), "summary": row.get("snippet")}
            companies.append({
                "company_name": company.get("company_name"),
                "website": company.get("website"),
                "summary": company.get("summary"),
                "industry": company.get("industry"),
                "country": company.get("country"),
                "products": company.get("products") or [],
                "services": company.get("services") or [],
                "technologies": company.get("technologies") or [],
                "use_cases": company.get("use_cases") or [],
                "evidence": company.get("evidence") or [],
            })
        return {"companies": companies, "company_count": len(companies)}

    def _build_dna_memory(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        profiles = []
        for row in rows:
            profiles.append({
                "company_name": row.get("company_name"),
                "website": row.get("website"),
                "industry": row.get("industry"),
                "company_type": row.get("company_type"),
                "country": row.get("country"),
                "business_summary": row.get("business_summary"),
                "estimated_company_size": row.get("estimated_company_size"),
                "estimated_ai_maturity": row.get("estimated_ai_maturity"),
                "technology_signals": row.get("technology_signals") or [],
                "digital_transformation_signals": row.get("digital_transformation_signals") or [],
                "buying_personas": row.get("buying_personas") or [],
                "use_cases": row.get("use_cases") or [],
                "strengths": row.get("strengths") or [],
                "risks": row.get("risks") or [],
                "evidence": row.get("evidence") or [],
                "confidence": row.get("confidence") or 0.0,
                "reasoning": row.get("reasoning"),
            })
        return {"profiles": profiles, "profile_count": len(profiles)}

    def _shared_memory_payload(self, output: RecommendationOutput) -> dict[str, Any]:
        return {
            "companies": [c.model_dump(mode="json") for c in output.companies],
            "company_count": output.company_count,
            "execution_time": output.execution_time,
        }

    async def _update_mission_metadata(
        self,
        mission_id: str,
        mission: dict[str, Any],
        output: RecommendationOutput,
        database_status: RecommendationDatabaseStatus,
    ) -> None:
        metadata = dict(mission.get("metadata") or {})
        metadata["recommendations"] = {
            "completed": True,
            "company_count": output.company_count,
            "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "table": "recommendation_results",
        }
        await self.mission_repository.update_metadata(mission_id, metadata)
