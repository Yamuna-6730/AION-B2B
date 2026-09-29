from __future__ import annotations

import time
from typing import Any

from app.core.exceptions import AionError
from app.core.logger import app_logger
from app.schemas.missions import MissionOrchestratorResponse
from app.schemas.planner import PlannerRunResponse
from app.schemas.strategy import MissionStatus
from app.services.planner import PlannerService
from app.services.strategy_service import StrategyService
from app.supabase.repositories.mission_repository import MissionRepository


class MissionOrchestratorError(AionError):
    error_code = "MISSION_ORCHESTRATOR_ERROR"


class MissionOrchestratorService:
    def __init__(
        self,
        *,
        strategy_service: StrategyService | None = None,
        planner_service: PlannerService | None = None,
        mission_repository: MissionRepository | None = None,
    ) -> None:
        self.strategy_service = strategy_service or StrategyService()
        self.planner_service = planner_service or PlannerService()
        self.mission_repository = mission_repository or MissionRepository()

    async def run(self, mission_id: str) -> MissionOrchestratorResponse:
        started = time.perf_counter()
        database: dict[str, bool] = {
            "missions": False,
            "market_discovery_results": False,
            "business_dna_results": False,
            "recommendation_results": False,
        }

        try:
            app_logger.info("Mission orchestration started", mission_id=mission_id)

            strategy = await self._run_strategy(mission_id)
            app_logger.info("Strategy completed", mission_id=mission_id)

            planner_response = await self._run_planner(mission_id)
            app_logger.info("Planner completed", mission_id=mission_id)

            await self.mission_repository.update_status(mission_id, MissionStatus.COMPLETED)
            app_logger.info("Mission orchestration completed", mission_id=mission_id)

            database["missions"] = True
            shared_memory = planner_response.shared_memory or {}
            if "market_discovery" in shared_memory:
                database["market_discovery_results"] = True
            if "business_dna" in shared_memory:
                database["business_dna_results"] = True
            if "recommendations" in shared_memory or "recommendation" in shared_memory:
                database["recommendation_results"] = True

            runtime = time.perf_counter() - started
            return MissionOrchestratorResponse(
                mission_id=mission_id,
                status=MissionStatus.COMPLETED.value,
                strategy=strategy,
                planner=planner_response.model_dump(mode="json"),
                shared_memory=shared_memory,
                database=database,
                execution_time=runtime,
                confidence=planner_response.confidence,
            )
        except Exception as exc:
            await self._fail_mission(mission_id, str(exc))
            runtime = time.perf_counter() - started
            app_logger.exception("Mission orchestration failed", mission_id=mission_id, error=str(exc))
            return MissionOrchestratorResponse(
                mission_id=mission_id,
                status=MissionStatus.FAILED.value,
                strategy=None,
                planner=None,
                shared_memory={},
                database=database,
                execution_time=runtime,
                confidence=0.0,
            )

    async def _run_strategy(self, mission_id: str) -> dict[str, Any]:
        mission = await self.mission_repository.get_mission(mission_id)
        current_strategy = mission.get("strategy") or {}
        if current_strategy:
            return current_strategy
        return await self.strategy_service.run_strategy(mission_id)

    async def _run_planner(self, mission_id: str) -> PlannerRunResponse:
        return await self.planner_service.run_planner(mission_id)

    async def _fail_mission(self, mission_id: str, error: str) -> None:
        mission = await self.mission_repository.get_mission(mission_id)
        metadata = dict(mission.get("metadata") or {})
        metadata["error"] = error
        await self.mission_repository.update_metadata(mission_id, metadata)
        await self.mission_repository.update_status(mission_id, MissionStatus.FAILED)
