from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from app.core.exceptions import ResourceNotFoundError
from app.core.logger import app_logger
from app.schemas.planner import ExecutionBlueprint
from app.schemas.strategy import MissionIntelligence, MissionStatus
from app.supabase.client import SupabaseClient


class MissionRepository:
    """Repository for persistence against the Supabase missions table."""

    def __init__(self, client: Any | None = None) -> None:
        self.client = client or SupabaseClient.get_client()
        self.table_name = "missions"

    async def create_mission(
        self,
        *,
        title: str,
        objective: str,
        domain: str | None = None,
        mission_type: str | None = None,
        created_by: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "title": title,
            "objective": objective,
            "status": MissionStatus.CREATED.value,
            "shared_memory": {},
            "updated_at": datetime.now(UTC).isoformat(),
        }
        if domain is not None:
            payload["domain"] = domain
        if mission_type is not None:
            payload["mission_type"] = mission_type
        if created_by is not None:
            payload["created_by"] = created_by
        if metadata is not None:
            payload["metadata"] = metadata
        return await asyncio.to_thread(self._insert, payload)

    async def get_mission(self, mission_id: str) -> dict[str, Any]:
        result = await asyncio.to_thread(
            lambda: self.client.table(self.table_name).select("*").eq("id", mission_id).single().execute()
        )
        data = self._response_data(result)
        if not data:
            raise ResourceNotFoundError("Mission not found", {"mission_id": mission_id})
        return data

    async def update_strategy(self, mission_id: str, intelligence: MissionIntelligence) -> dict[str, Any]:
        payload = {
            "strategy": intelligence.model_dump(mode="json"),
            "icp": intelligence.icp.model_dump(mode="json"),
            "blueprint": {
                "target_personas": [persona.model_dump(mode="json") for persona in intelligence.target_personas],
                "qualification_rules": [
                    rule.model_dump(mode="json") for rule in intelligence.qualification_rules
                ],
                "business_triggers": [
                    trigger.model_dump(mode="json") for trigger in intelligence.business_triggers
                ],
                "technology_preferences": [
                    preference.model_dump(mode="json") for preference in intelligence.technology_preferences
                ],
                "recommended_agents": [
                    agent.model_dump(mode="json") for agent in intelligence.recommended_agents
                ],
            },
            "confidence": intelligence.confidence,
            "status": MissionStatus.STRATEGY_COMPLETED.value,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        return await self._update(mission_id, payload)

    async def update_status(self, mission_id: str, status: MissionStatus) -> dict[str, Any]:
        return await self._update(
            mission_id,
            {
                "status": status.value,
                "updated_at": datetime.now(UTC).isoformat(),
            },
        )

    async def update_planner(self, mission_id: str, planner_output: ExecutionBlueprint | dict[str, Any]) -> dict[str, Any]:
        output = planner_output.model_dump(mode="json") if isinstance(planner_output, ExecutionBlueprint) else planner_output
        return await self._update(
            mission_id,
            {
                "planner_output": output,
                "planner_status": "COMPLETED",
                "confidence": output.get("confidence"),
                "status": MissionStatus.PLANNER_COMPLETED.value,
                "updated_at": datetime.now(UTC).isoformat(),
            },
        )

    async def update_execution_graph(self, mission_id: str, execution_graph: dict[str, Any]) -> dict[str, Any]:
        return await self._update(
            mission_id,
            {
                "execution_graph": execution_graph,
                "updated_at": datetime.now(UTC).isoformat(),
            },
        )

    async def update_estimates(
        self,
        mission_id: str,
        *,
        estimated_duration: float,
        estimated_cost: float,
        confidence: float,
    ) -> dict[str, Any]:
        return await self._update(
            mission_id,
            {
                "estimated_duration": int(round(estimated_duration)),
                "estimated_cost": estimated_cost,
                "confidence": confidence,
                "updated_at": datetime.now(UTC).isoformat(),
            },
        )

    async def update_metadata(self, mission_id: str, metadata: dict[str, Any]) -> dict[str, Any]:
        return await self._update(
            mission_id,
            {
                "metadata": metadata,
                "updated_at": datetime.now(UTC).isoformat(),
            },
        )

    async def update_recommendations(self, mission_id: str, recommendations: dict[str, Any]) -> dict[str, Any]:
        mission = await self.get_mission(mission_id)
        metadata = mission.get("metadata") or {}
        metadata["recommendations"] = recommendations
        return await self._update(
            mission_id,
            {
                "metadata": metadata,
                "updated_at": datetime.now(UTC).isoformat(),
            },
        )

    async def update_shared_memory(self, mission_id: str, shared_memory: dict[str, Any]) -> dict[str, Any]:
        mission = await self.get_mission(mission_id)
        merged = dict(mission.get("shared_memory") or {})
        merged.update(shared_memory)
        return await self._update(
            mission_id,
            {
                "shared_memory": merged,
                "updated_at": datetime.now(UTC).isoformat(),
            },
        )

    async def list_missions(self) -> list[dict[str, Any]]:
        result = await asyncio.to_thread(
            lambda: self.client.table(self.table_name).select("*").order("updated_at", desc=True).execute()
        )
        data = self._response_data(result)
        return data if isinstance(data, list) else []

    def _insert(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            result = self.client.table(self.table_name).insert(payload).execute()
        except Exception as exc:
            if "title" not in payload or "title" not in str(exc).lower():
                raise
            compatible_payload = {key: value for key, value in payload.items() if key != "title"}
            result = self.client.table(self.table_name).insert(compatible_payload).execute()
        data = self._response_data(result)
        if isinstance(data, list) and data:
            return data[0]
        if isinstance(data, dict):
            return data
        app_logger.warning("Supabase mission insert returned no data")
        return payload

    async def _update(self, mission_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        result = await asyncio.to_thread(
            lambda: self.client.table(self.table_name).update(payload).eq("id", mission_id).execute()
        )
        data = self._response_data(result)
        if isinstance(data, list) and data:
            return data[0]
        if isinstance(data, dict):
            return data
        return payload | {"id": mission_id}

    def _response_data(self, response: Any) -> Any:
        return getattr(response, "data", response)
