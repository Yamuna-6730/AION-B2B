from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.agents.base.task import AgentTask
from app.agents.intelligence.strategy_agent import StrategyAgent
from app.core.exceptions import AionError
from app.core.logger import app_logger
from app.schemas.strategy import MissionIntelligence, MissionStatus, StrategyAnalyzeRequest
from app.supabase.repositories import MissionRepository


class StrategyServiceError(AionError):
    error_code = "STRATEGY_SERVICE_ERROR"


class StrategyService:
    """Application service for Strategy Agent analysis workflows."""

    def __init__(
        self,
        *,
        agent: StrategyAgent | None = None,
        mission_repository: MissionRepository | None = None,
    ) -> None:
        self.agent = agent or StrategyAgent()
        self.mission_repository = mission_repository or MissionRepository()

    async def analyze(self, request: StrategyAnalyzeRequest) -> MissionIntelligence:
        mission = await self.mission_repository.create_mission(
            title=request.title,
            objective=request.objective,
        )
        mission_id = str(mission.get("id") or mission.get("mission_id"))
        if not mission_id:
            raise StrategyServiceError("Mission repository did not return a mission id.")

        task = AgentTask(
            mission_id=mission_id,
            task_id=f"strategy_{uuid4().hex}",
            agent_name=self.agent.name,
            objective=request.objective,
            context={"title": request.title},
        )

        try:
            await self.mission_repository.update_status(mission_id, MissionStatus.STRATEGY_RUNNING)
            response = await self.agent.run(task)
            intelligence = MissionIntelligence.model_validate(response.output)
            await self.mission_repository.update_strategy(mission_id, intelligence)
            if hasattr(self.mission_repository, "update_shared_memory"):
                await self.mission_repository.update_shared_memory(
                    mission_id,
                    {"strategy": intelligence.model_dump(mode="json")},
                )
            app_logger.info(
                "Strategy analysis persisted",
                mission_id=mission_id,
                confidence=intelligence.confidence,
                execution_time=response.execution_time,
            )
            return intelligence
        except Exception:
            await self.mission_repository.update_status(mission_id, MissionStatus.STRATEGY_FAILED)
            app_logger.exception("Strategy analysis failed", mission_id=mission_id)
            raise

    async def run_strategy(self, mission_id: str) -> dict[str, Any]:
        mission = await self.mission_repository.get_mission(mission_id)
        objective = str(mission.get("objective") or "")
        title = str(mission.get("title") or mission_id)
        if not objective:
            raise StrategyServiceError("Mission objective is required to run strategy.")

        task = AgentTask(
            mission_id=mission_id,
            task_id=f"strategy_{uuid4().hex}",
            agent_name=self.agent.name,
            objective=objective,
            context={"title": title},
        )

        try:
            await self.mission_repository.update_status(mission_id, MissionStatus.STRATEGY_RUNNING)
            response = await self.agent.run(task)
            intelligence = MissionIntelligence.model_validate(response.output)
            await self.mission_repository.update_strategy(mission_id, intelligence)
            if hasattr(self.mission_repository, "update_shared_memory"):
                await self.mission_repository.update_shared_memory(
                    mission_id,
                    {"strategy": intelligence.model_dump(mode="json")},
                )
            app_logger.info(
                "Strategy analysis persisted",
                mission_id=mission_id,
                confidence=intelligence.confidence,
                execution_time=response.execution_time,
            )
            return intelligence.model_dump(mode="json")
        except Exception:
            await self.mission_repository.update_status(mission_id, MissionStatus.STRATEGY_FAILED)
            app_logger.exception("Strategy analysis failed", mission_id=mission_id)
            raise
