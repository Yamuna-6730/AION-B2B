from __future__ import annotations

import json
import time

from app.agents.base.base_agent import BaseAgent
from app.agents.base.enums import AgentState
from app.agents.base.response import AgentResponse
from app.agents.base.task import AgentTask
from app.core.logger import agent_logger
from app.llm import LLMManager, llm_manager
from app.llm.exceptions import LLMError, ParsingError
from app.schemas.planner import AgentCapability, ExecutionBlueprint, GraphEdge, GraphNode, GraphNodeData, GraphPosition
from app.utils.graph_builder import normalize_agent_name


class PlannerAgent(BaseAgent):
    name = "planner"
    description = "Converts mission intelligence into an executable workflow graph."
    category = "planner"
    version = "0.1.0"
    priority = 1
    supported_inputs = ("mission", "strategy", "icp", "blueprint")
    supported_outputs = ("execution_blueprint",)

    def __init__(self, ai_runtime: LLMManager = llm_manager) -> None:
        self.ai_runtime = ai_runtime

    async def initialize(self) -> None:
        return None

    async def validate(self, task: AgentTask) -> bool:
        return bool(task.mission_id and task.context.get("mission"))

    async def run(self, task: AgentTask) -> AgentResponse:
        agent_logger.debug("Planner Agent run started", mission_id=task.mission_id)
        started = time.perf_counter()
        mission = task.context.get("mission", {})
        available_agents = task.context.get("available_agents", [])
        system_role = (
            "You are an Enterprise Workflow Planner.\n\n"
            "Your responsibility is to convert business strategy into the optimal execution workflow.\n\n"
            "Always minimize execution time.\n\n"
            "Prefer parallel execution.\n\n"
            "Only choose necessary agents.\n\n"
            "Never execute unnecessary agents.\n\n"
            "Output ONLY JSON."
        )
        memory = {
            "Mission": mission,
            "Strategy": mission.get("strategy"),
            "ICP": mission.get("icp"),
            "Mission Intelligence": mission.get("strategy"),
            "Available Agents": available_agents,
            "Output Schema": ExecutionBlueprint.model_json_schema(),
        }
        try:
            blueprint = await self.ai_runtime.generate_json(
                response_model=ExecutionBlueprint,
                system_role=system_role,
                mission=json.dumps(mission, default=str),
                memory=memory,
                agent_name=self.name,
                expected_schema=ExecutionBlueprint,
                template_name="planner",
                temperature=float(task.parameters.get("temperature", 0.2)),
                top_p=float(task.parameters.get("top_p", 0.95)),
                max_tokens=int(task.parameters.get("max_tokens", 4096)),
            )
        except (ParsingError, LLMError) as exc:
            agent_logger.exception(
                "Planner Agent LLM output failed; using registry-driven fallback blueprint",
                mission_id=task.mission_id,
            )
            blueprint = self._fallback_blueprint(task.mission_id, mission, available_agents, str(exc))
        blueprint = blueprint.model_copy(update={"mission_id": task.mission_id})
        execution_time = time.perf_counter() - started
        agent_logger.info(
            "Planner Agent generated execution blueprint",
            mission_id=task.mission_id,
            execution_time=execution_time,
            selected_agents=blueprint.selected_agents,
        )
        return AgentResponse(
            success=True,
            mission_id=task.mission_id,
            task_id=task.task_id,
            agent_name=self.name,
            status=AgentState.COMPLETED,
            confidence=blueprint.confidence,
            reasoning=blueprint.planner_reasoning,
            execution_time=execution_time,
            metadata={"estimated_duration": blueprint.estimated_duration, "estimated_cost": blueprint.estimated_cost},
            output=blueprint.model_dump(mode="json"),
        )

    async def summarize(self, response: AgentResponse) -> str:
        return response.reasoning

    async def calculate_confidence(self, response: AgentResponse) -> float:
        return response.confidence

    async def cleanup(self) -> None:
        return None

    def _fallback_blueprint(
        self,
        mission_id: str,
        mission: dict,
        available_agents: list[dict],
        reason: str,
    ) -> ExecutionBlueprint:
        registered = {normalize_agent_name(str(agent.get("name", ""))) for agent in available_agents}
        selected = self._recommended_agents_from_mission(mission)
        if not selected:
            selected = self._objective_agents(str(mission.get("objective") or ""))
        selected = list(dict.fromkeys(agent for agent in selected if agent in registered and agent != self.name))
        if not selected:
            selected = sorted(agent for agent in registered if agent != self.name)
        nodes = [
            GraphNode(
                id=agent,
                position=GraphPosition(x=index * 220, y=0),
                data=GraphNodeData(
                    label=" ".join(part.capitalize() for part in agent.split("_")),
                    agent_name=agent,
                    priority=4 - index,
                    parallel=False,
                    status="PENDING",
                    critical=True,
                ),
            )
            for index, agent in enumerate(selected)
        ]
        edges = [
            GraphEdge(id=f"{source}-{target}", source=source, target=target)
            for source, target in zip(selected, selected[1:], strict=False)
        ]

        return ExecutionBlueprint(
            mission_id=mission_id,
            selected_agents=selected,
            execution_order=selected,
            parallel_groups=[[agent] for agent in selected],
            planner_reasoning=(
                "Fallback planner blueprint generated because the LLM planner response could not be parsed. "
                f"Original planner error: {reason}"
            ),
            estimated_duration=float(max(len(selected), 1)),
            estimated_cost=0.0,
            confidence=0.5,
            execution_constraints={"fallback": True},
            nodes=nodes,
            edges=edges,
        )

    def _recommended_agents_from_mission(self, mission: dict) -> list[str]:
        candidates: list[str] = []
        for source in (mission.get("blueprint") or {}, mission.get("strategy") or {}):
            for item in source.get("recommended_agents", []) or []:
                if isinstance(item, dict):
                    name = item.get("name")
                else:
                    name = item
                if name:
                    candidates.append(normalize_agent_name(str(name)))
        return list(dict.fromkeys(candidates))

    def _objective_agents(self, objective: str) -> list[str]:
        text = objective.lower()
        selected: list[str] = []
        if any(term in text for term in ("hiring", "hire", "career", "open role", "workforce")):
            selected.append("hiring")
        if any(term in text for term in ("funding", "funded", "investor", "investment", "series ", "raise")):
            selected.append("funding")
        return selected


def capability_from_agent(agent: BaseAgent) -> AgentCapability:
    return AgentCapability(
        name=agent.name,
        category=agent.category,
        description=getattr(agent, "description", ""),
        parallel_capable=getattr(agent, "parallel_capable", True),
        dependencies=list(getattr(agent, "dependencies", [])),
        priority=getattr(agent, "priority", 3),
    )
