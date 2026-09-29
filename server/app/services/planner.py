from __future__ import annotations

import asyncio
import time
from typing import Any
from uuid import uuid4

from app.agents.base.agent_registry import AgentRegistry
from app.agents.base.task import AgentTask
from app.agents.catalog import ACTIVE_INTELLIGENCE_AGENT_CLASSES
from app.agents.planner.planner_agent import PlannerAgent, capability_from_agent
from app.core.exceptions import AionError
from app.core.logger import app_logger
from app.schemas.planner import ExecutionBlueprint, ExecutionContext, PlannerRunResponse
from app.schemas.strategy import MissionStatus
from app.schemas.market_discovery import MarketDiscoveryOutput
from app.schemas.business_dna import BusinessDNAOutput
from app.schemas.recommendations import RecommendationOutput
from app.supabase.repositories import MissionRepository
from app.supabase.repositories.market_discovery_repository import MarketDiscoveryRepository
from app.supabase.repositories.business_dna_repository import BusinessDNARepository
from app.supabase.repositories.recommendation_repository import RecommendationRepository
from app.utils.graph_builder import build_execution_graph, normalize_agent_name
from app.utils.graph_validator import validate_execution_graph


class PlannerServiceError(AionError):
    error_code = "PLANNER_SERVICE_ERROR"


class PlannerService:
    def __init__(
        self,
        *,
        agent: PlannerAgent | None = None,
        mission_repository: MissionRepository | None = None,
        registry: AgentRegistry | None = None,
    ) -> None:
        self.agent = agent or PlannerAgent()
        self.mission_repository = mission_repository or MissionRepository()
        self.registry = registry or self._default_registry()
        self.market_repository = MarketDiscoveryRepository()
        self.business_dna_repository = BusinessDNARepository()
        self.recommendation_repository = RecommendationRepository()

    async def run_planner(self, mission_id: str) -> PlannerRunResponse:
        started = time.perf_counter()
        mission = await self.mission_repository.get_mission(mission_id)
        await self.mission_repository.update_status(mission_id, MissionStatus.PLANNER_RUNNING)

        task = AgentTask(
            mission_id=mission_id,
            task_id=f"planner_{uuid4().hex}",
            agent_name=self.agent.name,
            objective=str(mission.get("objective") or ""),
            context={"mission": mission, "available_agents": self._available_agent_payload()},
        )
        response = await self.agent.run(task)
        blueprint = ExecutionBlueprint.model_validate(response.output)
        capabilities = {agent.name: capability_from_agent(agent) for agent in self.registry.list_agents()}
        blueprint = build_execution_graph(blueprint, capabilities)
        validate_execution_graph(blueprint.nodes, blueprint.edges)

        execution_graph = self._graph_payload(blueprint)
        await self.mission_repository.update_planner(mission_id, blueprint)
        await self.mission_repository.update_shared_memory(
            mission_id,
            {"planner": blueprint.model_dump(mode="json")},
        )
        await self.mission_repository.update_execution_graph(mission_id, execution_graph)
        await self.mission_repository.update_estimates(
            mission_id,
            estimated_duration=blueprint.estimated_duration,
            estimated_cost=blueprint.estimated_cost,
            confidence=blueprint.confidence,
        )

        await self.mission_repository.update_status(mission_id, MissionStatus.EXECUTING_AGENTS)
        await self.mission_repository.update_status(mission_id, MissionStatus.EXECUTION_RUNNING)
        context = ExecutionContext(
            mission=mission,
            strategy=mission.get("strategy") or {},
            icp=mission.get("icp") or {},
            blueprint=mission.get("blueprint") or {},
            shared_memory={},
            metadata={"planner_started_at": started},
        )
        shared_memory = await self.execute_graph(mission_id, blueprint, context)
        runtime = time.perf_counter() - started
        metadata = self._execution_metrics(blueprint, shared_memory, runtime)
        recommendations = shared_memory.get("recommendation", {})
        if recommendations:
            metadata["recommendations"] = recommendations
        await self.mission_repository.update_metadata(mission_id, metadata)
        await self.mission_repository.update_status(mission_id, MissionStatus.COMPLETED)

        final_graph = self._graph_payload(blueprint)
        return PlannerRunResponse(
            mission_id=mission_id,
            status=MissionStatus.COMPLETED.value,
            execution_graph=final_graph,
            planner_output=blueprint.model_dump(mode="json"),
            shared_memory=shared_memory,
            recommendations=recommendations,
            runtime=runtime,
            confidence=blueprint.confidence,
        )

    async def execute_graph(
        self,
        mission_id: str,
        blueprint: ExecutionBlueprint,
        context: ExecutionContext,
    ) -> dict[str, Any]:
        nodes = {node.id: node for node in blueprint.nodes}
        incoming = {node_id: set[str]() for node_id in nodes}
        for edge in blueprint.edges:
            incoming[edge.target].add(edge.source)

        completed: set[str] = set()
        failed: set[str] = set()
        running: set[str] = set()
        while len(completed | failed) < len(nodes):
            mission = await self.mission_repository.get_mission(mission_id)
            if mission.get("status") == MissionStatus.CANCELLED.value:
                await self.mission_repository.update_status(mission_id, MissionStatus.CANCELLED)
                break

            ready = [
                node_id
                for node_id, deps in incoming.items()
                if node_id not in completed | failed | running and deps <= completed
            ]
            if not ready:
                raise PlannerServiceError("Execution graph stalled with unresolved dependencies.")

            for node_id in ready:
                self._set_node_status(blueprint, node_id, "RUNNING")
                running.add(node_id)
                if node_id == "recommendation":
                    await self.mission_repository.update_status(mission_id, MissionStatus.RECOMMENDATION_RUNNING)
            await self.mission_repository.update_execution_graph(mission_id, self._graph_payload(blueprint))

            results = await asyncio.gather(
                *(self._execute_node(mission_id, node_id, nodes[node_id], context) for node_id in ready),
                return_exceptions=True,
            )
            running.difference_update(ready)
            for node_id, result in zip(ready, results, strict=True):
                if isinstance(result, Exception):
                    failed.add(node_id)
                    self._set_node_status(blueprint, node_id, "FAILED")
                    if nodes[node_id].data.critical:
                        await self.mission_repository.update_status(mission_id, MissionStatus.FAILED)
                        raise result
                    app_logger.warning("Non-critical planner node failed", mission_id=mission_id, node_id=node_id)
                else:
                    completed.add(node_id)
                    output = self._node_output(result)
                    memory_key = self._memory_key(node_id)
                    context.shared_memory[memory_key] = output
                    await self._persist_node_output(mission_id, memory_key, output)
                    if hasattr(self.mission_repository, "update_shared_memory"):
                        await self.mission_repository.update_shared_memory(mission_id, context.shared_memory)
                    self._set_node_status(blueprint, node_id, "COMPLETED")
            await self.mission_repository.update_execution_graph(mission_id, self._graph_payload(blueprint))

        return context.shared_memory

    def _node_output(self, result: Any) -> dict[str, Any]:
        if isinstance(result, dict) and isinstance(result.get("output"), dict):
            return result["output"]
        return result if isinstance(result, dict) else {}

    def _memory_key(self, node_id: str) -> str:
        if node_id in {"market", "market_discovery"}:
            return "market"
        if node_id in {"recommendations", "recommendation"}:
            return "recommendation"
        return node_id

    async def _persist_node_output(self, mission_id: str, memory_key: str, output: dict[str, Any]) -> None:
        if memory_key in {"market", "market_discovery"}:
            market_output = MarketDiscoveryOutput.model_validate(output)
            await self.market_repository.save_results(mission_id, market_output.companies)
        elif memory_key == "business_dna":
            dna_output = BusinessDNAOutput.model_validate(output)
            await self.business_dna_repository.save_results(mission_id, dna_output.profiles)
        elif memory_key == "recommendation":
            recommendation_output = RecommendationOutput.model_validate(output)
            await self.recommendation_repository.save_results(mission_id, recommendation_output.companies)

    async def _execute_node(
        self,
        mission_id: str,
        node_id: str,
        node: Any,
        context: ExecutionContext,
    ) -> dict[str, Any]:
        agent_name = normalize_agent_name(node.data.agent_name or node_id)
        agent = self.registry.get_agent(agent_name)
        if agent is None:
            raise PlannerServiceError(f"Agent not registered: {agent_name}")

        task = AgentTask(
            mission_id=mission_id,
            task_id=f"{agent_name}_{uuid4().hex}",
            agent_name=agent_name,
            objective=str(context.mission.get("objective") or ""),
            context=context.model_dump(mode="json"),
            parameters={"node": node.model_dump(mode="json")},
            dependencies=[],
        )
        attempts = node.data.max_retries + 1
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                app_logger.info("Planner agent node started", mission_id=mission_id, agent_name=agent_name)
                if node.data.timeout:
                    response = await asyncio.wait_for(agent.run(task), timeout=node.data.timeout)
                else:
                    response = await agent.run(task)
                app_logger.info("Planner agent node completed", mission_id=mission_id, agent_name=agent_name)
                return response.model_dump(mode="json")
            except Exception as exc:
                last_error = exc
                app_logger.exception("Planner agent node failed", mission_id=mission_id, agent_name=agent_name, attempt=attempt)
                if attempt < attempts - 1 and node.data.retry_delay:
                    await asyncio.sleep(node.data.retry_delay)
        raise last_error or PlannerServiceError(f"Agent failed: {agent_name}")

    def _available_agent_payload(self) -> list[dict[str, Any]]:
        return [capability_from_agent(agent).model_dump(mode="json") for agent in self.registry.list_agents()]

    def _graph_payload(self, blueprint: ExecutionBlueprint) -> dict[str, Any]:
        return {
            "nodes": [node.model_dump(mode="json") for node in blueprint.nodes],
            "edges": [edge.model_dump(mode="json") for edge in blueprint.edges],
        }

    def _set_node_status(self, blueprint: ExecutionBlueprint, node_id: str, status: str) -> None:
        for node in blueprint.nodes:
            if node.id == node_id:
                node.data.status = status
                return

    def _execution_metrics(
        self,
        blueprint: ExecutionBlueprint,
        shared_memory: dict[str, Any],
        runtime: float,
    ) -> dict[str, Any]:
        failures = [node.id for node in blueprint.nodes if node.data.status == "FAILED"]
        parallel_nodes = [node for node in blueprint.nodes if node.data.parallel]
        return {
            "execution_time": runtime,
            "llm_calls": 1,
            "external_calls": len(shared_memory),
            "success_rate": (len(blueprint.nodes) - len(failures)) / max(len(blueprint.nodes), 1),
            "failure_count": len(failures),
            "parallelism_score": len(parallel_nodes) / max(len(blueprint.nodes), 1),
            "overall_confidence": blueprint.confidence,
        }

    def _default_registry(self) -> AgentRegistry:
        registry = AgentRegistry()
        for agent_class in ACTIVE_INTELLIGENCE_AGENT_CLASSES:
            registry.register(agent_class())
        return registry
