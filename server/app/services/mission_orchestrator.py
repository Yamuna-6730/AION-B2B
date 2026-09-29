from __future__ import annotations

import time
import re
import json
from typing import Any

from app.core.exceptions import AionError
from app.core.logger import app_logger
from app.schemas.missions import MissionOrchestratorResponse
from app.schemas.planner import PlannerRunResponse
from app.schemas.strategy import MissionStatus
from app.services.planner import PlannerService
from app.services.strategy_service import StrategyService
from app.services.memory_service import HindsightMemoryService, MemoryService
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
        memory_service: MemoryService | None = None,
    ) -> None:
        self.strategy_service = strategy_service or StrategyService()
        self.planner_service = planner_service or PlannerService()
        self.mission_repository = mission_repository or MissionRepository()
        self.memory_service = memory_service or HindsightMemoryService()

    async def run(self, mission_id: str) -> MissionOrchestratorResponse:
        started = time.perf_counter()
        database: dict[str, bool] = {
            "missions": False,
            "market_discovery_results": False,
            "business_dna_results": False,
            "recommendation_results": False,
        }
        memory: dict[str, Any] = {"status": "unavailable", "first_investigation": True, "relevant_memories": []}

        try:
            app_logger.info("Mission orchestration started", mission_id=mission_id)

            memory = await self._recall_memory(mission_id)

            strategy = await self._run_strategy(mission_id)
            app_logger.info("Strategy completed", mission_id=mission_id)

            planner_response = await self._run_planner(mission_id)
            app_logger.info("Planner completed", mission_id=mission_id)

            await self.mission_repository.update_status(mission_id, MissionStatus.COMPLETED)
            app_logger.info("Mission orchestration completed", mission_id=mission_id)

            database["missions"] = True
            mission = await self.mission_repository.get_mission(mission_id)
            shared_memory = dict(mission.get("shared_memory") or {})
            shared_memory.update(planner_response.shared_memory or {})
            if memory.get("status") == "available" and memory.get("relevant_memories"):
                reflection = await self.memory_service.reflect(
                    company_id=str(memory["company"]),
                    objective=str(mission.get("objective") or ""),
                    current_intelligence=shared_memory,
                )
                memory["changes"] = reflection.reflection
                if reflection.status == "unavailable":
                    memory["reflect_status"] = "unavailable"
            retention = await self._retain_memory(mission_id, shared_memory)
            memory["retain_status"] = retention
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
                memory=memory,
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
                memory=memory,
            )
        finally:
            close = getattr(self.memory_service, "aclose", None)
            if close is not None:
                await close()

    async def _run_strategy(self, mission_id: str) -> dict[str, Any]:
        mission = await self.mission_repository.get_mission(mission_id)
        current_strategy = mission.get("strategy") or {}
        if current_strategy:
            return current_strategy
        return await self.strategy_service.run_strategy(mission_id)

    async def _recall_memory(self, mission_id: str) -> dict[str, Any]:
        mission = await self.mission_repository.get_mission(mission_id)
        company = self._company(mission)
        if not company:
            context = {"status": "empty", "first_investigation": True, "relevant_memories": [], "historical_intelligence": [], "historical_signals": [], "previous_recommendation": None}
        else:
            result = await self.memory_service.recall(company_id=company, objective=str(mission.get("objective") or ""))
            context = {"status": result.status, "first_investigation": result.status == "empty", "company": company, "relevant_memories": result.records, "historical_intelligence": result.records, "historical_signals": [], "previous_recommendation": None, "error": result.error}
        await self.mission_repository.update_shared_memory(mission_id, {"memory": context})
        return context

    async def _retain_memory(self, mission_id: str, shared_memory: dict[str, Any]) -> str:
        mission = await self.mission_repository.get_mission(mission_id)
        company = self._company(mission)
        if not company:
            return "empty"
        statuses: list[str] = []
        for category in ("hiring", "funding", "recommendation"):
            item = shared_memory.get(category)
            if not isinstance(item, dict):
                continue
            content = self._memory_content(category, item)
            if not content:
                continue
            result = await self.memory_service.retain(mission_id=mission_id, company_id=company, category=category, content=content, source="aion", agent=category)
            statuses.append(result.status)
        return "available" if statuses and all(status == "available" for status in statuses) else ("unavailable" if "unavailable" in statuses else "empty")

    def _company(self, mission: dict[str, Any]) -> str | None:
        explicit = mission.get("domain") or (mission.get("metadata") or {}).get("company")
        if explicit:
            return str(explicit)
        objective = str(mission.get("objective") or "")
        match = re.search(r"(?:analyze|re-evaluate|evaluate|investigate)\s+([A-Z][A-Za-z0-9.& -]{1,80}?)(?:'s|\s+(?:hiring|funding|investment)|[.?!]|$)", objective, re.IGNORECASE)
        return match.group(1).strip() if match else None

    def _memory_content(self, category: str, item: dict[str, Any]) -> str | None:
        keys = {"hiring": ("hiring_signals", "technology_signals", "expansion_signals"), "funding": ("funding_events", "expansion_signals", "latest_round", "investors"), "recommendation": ("companies",)}[category]
        values = {key: item.get(key) for key in keys if item.get(key)}
        return json.dumps({"category": category, "intelligence": values}, default=str) if values else None

    async def _run_planner(self, mission_id: str) -> PlannerRunResponse:
        return await self.planner_service.run_planner(mission_id)

    async def _fail_mission(self, mission_id: str, error: str) -> None:
        mission = await self.mission_repository.get_mission(mission_id)
        metadata = dict(mission.get("metadata") or {})
        metadata["error"] = error
        await self.mission_repository.update_metadata(mission_id, metadata)
        await self.mission_repository.update_status(mission_id, MissionStatus.FAILED)
