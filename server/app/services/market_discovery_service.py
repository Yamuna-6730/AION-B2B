from __future__ import annotations

import time
from typing import Any
from uuid import uuid4

from app.agents.base.task import AgentTask
from app.agents.market_discovery import MarketDiscoveryAgent
from app.core.logger import app_logger
from app.schemas.market_discovery import MarketDiscoveryDatabaseStatus, MarketDiscoveryOutput, MarketDiscoveryRunResponse
from app.supabase.repositories.market_discovery_repository import MarketDiscoveryRepository
from app.supabase.repositories.mission_repository import MissionRepository


class MarketDiscoveryService:
    """Application service for running market discovery infrastructure workflows."""

    def __init__(
        self,
        *,
        agent: MarketDiscoveryAgent | None = None,
        mission_repository: MissionRepository | None = None,
        market_repository: MarketDiscoveryRepository | None = None,
    ) -> None:
        self.agent = agent or MarketDiscoveryAgent()
        self.mission_repository = mission_repository or MissionRepository()
        self.market_repository = market_repository or MarketDiscoveryRepository()

    async def run(self, mission_id: str) -> MarketDiscoveryRunResponse:
        started = time.perf_counter()
        mission = await self.mission_repository.get_mission(mission_id)
        shared_memory: dict[str, Any] = {}
        task = AgentTask(
            mission_id=mission_id,
            task_id=f"market_{uuid4().hex}",
            agent_name=self.agent.name,
            objective=str(mission.get("objective") or ""),
            context={
                "mission": mission,
                "strategy": mission.get("strategy") or {},
                "icp": mission.get("icp") or {},
                "shared_memory": shared_memory,
            },
        )
        response = await self.agent.run(task)
        output = MarketDiscoveryOutput.model_validate(response.output)
        shared_memory["market_discovery"] = self._shared_memory_payload(output)
        if hasattr(self.mission_repository, "update_shared_memory"):
            await self.mission_repository.update_shared_memory(mission_id, shared_memory)
        saved_rows = await self.market_repository.save_results(mission_id, output.companies)
        
        database_status = MarketDiscoveryDatabaseStatus(
            saved=bool(saved_rows),
            verified=(len(saved_rows) == len(output.companies)),
            table_name=self.market_repository.table_name,
            rows=len(saved_rows),
        )

        # If saved count is less than expected, log a warning but do not raise
        if len(saved_rows) < len(output.companies):
            database_status.verified = False
            app_logger.warning(
                "Market discovery persistence mismatch",
                expected=len(output.companies),
                saved=len(saved_rows),
                mission_id=mission_id,
            )

        # Logs
        app_logger.info("Supabase Insert Count", count=len(output.companies))
        app_logger.info("Supabase Verification Count", count=len(saved_rows))
        
        await self._update_mission_metadata(mission_id, mission, output, database_status)
        runtime = time.perf_counter() - started
        
        app_logger.info("Shared Memory Updated", mission_id=mission_id)
        app_logger.info("Mission Updated", mission_id=mission_id)
        app_logger.info("Completed", mission_id=mission_id, runtime=runtime)
        
        return MarketDiscoveryRunResponse(
            mission_id=mission_id,
            status="COMPLETED",
            companies=output.companies,
            market_discovery=output,
            shared_memory=shared_memory,
            runtime=runtime,
            saved_company_count=len(saved_rows),
            database_status=database_status,
        )

    def _shared_memory_payload(self, output: MarketDiscoveryOutput) -> dict[str, Any]:
        return {
            "companies": [company.model_dump(mode="json") for company in output.companies],
            "raw_tavily_results": output.raw_tavily_results,
            "scraped_pages": output.scraped_pages,
            "queries": output.queries or output.search_queries,
            "company_count": output.company_count or output.total_companies,
            "execution_time": output.execution_time,
        }

    async def _update_mission_metadata(
        self,
        mission_id: str,
        mission: dict[str, Any],
        output: MarketDiscoveryOutput,
        database_status: MarketDiscoveryDatabaseStatus,
    ) -> None:
        metadata = dict(mission.get("metadata") or {})
        
        # Merge metadata.market_discovery exactly
        metadata["market_discovery"] = {
            "completed": True,
            "company_count": output.total_companies,
            "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "table": "market_discovery_results",
        }
        
        await self.mission_repository.update_metadata(mission_id, metadata)

