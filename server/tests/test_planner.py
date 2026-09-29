from __future__ import annotations

import asyncio
import time
from typing import Any
from uuid import uuid4

import pytest

from app.agents.base.agent_registry import AgentRegistry
from app.agents.base.enums import AgentState
from app.agents.base.response import AgentResponse
from app.agents.base.task import AgentTask
from app.agents.planner.planner_agent import PlannerAgent
from app.api.routes.planner import get_planner_service
from app.llm.exceptions import ParsingError
from app.main import app
from app.schemas.planner import AgentCapability, ExecutionBlueprint, GraphEdge, GraphNode, GraphNodeData, PlannerRunRequest
from app.schemas.strategy import MissionStatus
from app.services.planner import PlannerService
from app.utils.graph_builder import build_execution_graph
from app.utils.graph_validator import PlannerValidationException, validate_execution_graph
from fastapi.testclient import TestClient


class FakePlannerAgent:
    name = "planner"

    def __init__(self, blueprint: ExecutionBlueprint) -> None:
        self.blueprint = blueprint

    async def run(self, task: AgentTask) -> AgentResponse:
        return AgentResponse(
            success=True,
            mission_id=task.mission_id,
            task_id=task.task_id,
            agent_name="planner",
            status=AgentState.COMPLETED,
            confidence=self.blueprint.confidence,
            reasoning=self.blueprint.planner_reasoning,
            execution_time=0,
            output=self.blueprint.model_dump(mode="json"),
        )


class BrokenPlannerRuntime:
    async def generate_json(self, **kwargs: Any) -> ExecutionBlueprint:
        raise ParsingError("LLM response did not contain a JSON object or array.")


class FakeAgent:
    description = "fake"
    category = "discovery"
    version = "0.1.0"
    priority = 1
    supported_inputs = ("mission",)
    supported_outputs = ("fake",)
    parallel_capable = True
    dependencies: list[str] = []

    def __init__(self, name: str, delay: float = 0.01, fail_once: bool = False) -> None:
        self.name = name
        self.delay = delay
        self.fail_once = fail_once
        self.starts: list[float] = []

    async def run(self, task: AgentTask) -> AgentResponse:
        self.starts.append(time.perf_counter())
        await asyncio.sleep(self.delay)
        if self.fail_once:
            self.fail_once = False
            raise RuntimeError("temporary failure")
        return AgentResponse(
            success=True,
            mission_id=task.mission_id,
            task_id=task.task_id,
            agent_name=self.name,
            status=AgentState.COMPLETED,
            confidence=0.9,
            reasoning=f"{self.name} completed",
            execution_time=self.delay,
            output={"agent": self.name},
        )

    async def initialize(self) -> None:
        return None

    async def validate(self, task: AgentTask) -> bool:
        return True

    async def summarize(self, response: AgentResponse) -> str:
        return response.reasoning

    async def calculate_confidence(self, response: AgentResponse) -> float:
        return response.confidence

    async def cleanup(self) -> None:
        return None


class FakeRepository:
    def __init__(self) -> None:
        self.statuses: list[MissionStatus] = []
        self.graphs: list[dict[str, Any]] = []
        self.planner_output: dict[str, Any] | None = None
        self.metadata: dict[str, Any] | None = None
        self.recommendations: dict[str, Any] | None = None
        self.mission = {
            "id": "mission_001",
            "objective": "Find companies likely to buy AI.",
            "status": MissionStatus.STRATEGY_COMPLETED.value,
            "strategy": {"recommended_agents": [{"name": "Market"}]},
            "icp": {"industry": "Manufacturing"},
            "blueprint": {},
        }

    async def get_mission(self, mission_id: str) -> dict[str, Any]:
        return self.mission

    async def update_status(self, mission_id: str, status: MissionStatus) -> dict[str, Any]:
        self.statuses.append(status)
        self.mission["status"] = status.value
        return {"id": mission_id, "status": status.value}

    async def update_planner(self, mission_id: str, planner_output: Any) -> dict[str, Any]:
        self.planner_output = planner_output.model_dump(mode="json")
        return {"id": mission_id}

    async def update_execution_graph(self, mission_id: str, execution_graph: dict[str, Any]) -> dict[str, Any]:
        self.graphs.append(execution_graph)
        return {"id": mission_id}

    async def update_estimates(self, mission_id: str, **kwargs: Any) -> dict[str, Any]:
        return {"id": mission_id, **kwargs}

    async def update_metadata(self, mission_id: str, metadata: dict[str, Any]) -> dict[str, Any]:
        self.metadata = metadata
        return {"id": mission_id}

    async def update_shared_memory(self, mission_id: str, shared_memory: dict[str, Any]) -> dict[str, Any]:
        self.metadata = self.metadata or {}
        self.metadata["shared_memory"] = shared_memory
        return {"id": mission_id}

    async def update_recommendations(self, mission_id: str, recommendations: dict[str, Any]) -> dict[str, Any]:
        self.recommendations = recommendations
        return {"id": mission_id}


def build_blueprint() -> ExecutionBlueprint:
    return ExecutionBlueprint(
        mission_id="mission_001",
        selected_agents=["market", "hiring", "recommendation"],
        planner_reasoning="Market and hiring can run in parallel, recommendation is final.",
        estimated_duration=2,
        estimated_cost=0.1,
        confidence=0.88,
        nodes=[
            GraphNode(id="market", data=GraphNodeData(label="Market Agent", agent_name="market")),
            GraphNode(id="hiring", data=GraphNodeData(label="Hiring Agent", agent_name="hiring")),
            GraphNode(id="recommendation", data=GraphNodeData(label="Recommendation Agent", agent_name="recommendation")),
        ],
        edges=[
            GraphEdge(id="market-recommendation", source="market", target="recommendation"),
            GraphEdge(id="hiring-recommendation", source="hiring", target="recommendation"),
        ],
    )


def build_registry(*agents: FakeAgent) -> AgentRegistry:
    registry = AgentRegistry()
    for agent in agents:
        registry.register(agent)
    return registry


@pytest.mark.asyncio
async def test_planner_agent_falls_back_when_llm_json_is_malformed() -> None:
    agent = PlannerAgent(ai_runtime=BrokenPlannerRuntime())  # type: ignore[arg-type]
    task = AgentTask(
        mission_id="mission_001",
        task_id="planner_001",
        agent_name="planner",
        objective="Find companies likely to buy AI.",
        context={
            "mission": {
                "objective": "Find companies likely to buy AI.",
                "blueprint": {"recommended_agents": [{"name": "Market"}]},
            },
            "available_agents": [
                {"name": "hiring", "category": "intelligence"},
                {"name": "funding", "category": "intelligence"},
            ],
        },
    )

    response = await agent.run(task)

    assert response.success is True
    assert response.output["execution_constraints"]["fallback"] is True
    assert response.output["selected_agents"] == ["funding", "hiring"]
    assert "market" not in response.output["selected_agents"]


@pytest.mark.asyncio
async def test_planner_runs_parallel_agents_before_recommendation() -> None:
    repository = FakeRepository()
    market = FakeAgent("market", delay=0.03)
    hiring = FakeAgent("hiring", delay=0.03)
    recommendation = FakeAgent("recommendation", delay=0.01)
    service = PlannerService(
        agent=FakePlannerAgent(build_blueprint()),  # type: ignore[arg-type]
        mission_repository=repository,  # type: ignore[arg-type]
        registry=build_registry(market, hiring, recommendation),
    )

    result = await service.run_planner("mission_001")

    assert result.status == MissionStatus.COMPLETED.value
    assert set(result.shared_memory) == {"market", "hiring", "recommendation"}
    assert abs(market.starts[0] - hiring.starts[0]) < 0.02
    assert recommendation.starts[0] > market.starts[0]
    assert repository.statuses[0] == MissionStatus.PLANNER_RUNNING
    assert MissionStatus.EXECUTION_RUNNING in repository.statuses
    assert repository.statuses[-1] == MissionStatus.COMPLETED
    assert repository.graphs[-1]["nodes"][0]["data"]["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_planner_retries_node_before_failure() -> None:
    repository = FakeRepository()
    blueprint = build_blueprint()
    blueprint.nodes[0].data.max_retries = 1
    market = FakeAgent("market", fail_once=True)
    service = PlannerService(
        agent=FakePlannerAgent(blueprint),  # type: ignore[arg-type]
        mission_repository=repository,  # type: ignore[arg-type]
        registry=build_registry(market, FakeAgent("hiring"), FakeAgent("recommendation")),
    )

    result = await service.run_planner("mission_001")

    assert result.status == MissionStatus.COMPLETED.value
    assert len(market.starts) == 2


def test_graph_validator_rejects_cycles() -> None:
    nodes = [
        GraphNode(id="market", data=GraphNodeData(label="Market Agent", agent_name="market")),
        GraphNode(id="recommendation", data=GraphNodeData(label="Recommendation Agent", agent_name="recommendation")),
    ]
    edges = [
        GraphEdge(id="a", source="market", target="recommendation"),
        GraphEdge(id="b", source="recommendation", target="market"),
    ]

    with pytest.raises(PlannerValidationException):
        validate_execution_graph(nodes, edges)


def test_graph_builder_connects_available_agents_when_llm_omits_edges() -> None:
    blueprint = ExecutionBlueprint(
        mission_id="mission_001",
        selected_agents=["market", "hiring", "funding"],
        nodes=[
            GraphNode(id="market", data=GraphNodeData(label="Market Agent", agent_name="market")),
            GraphNode(id="hiring", data=GraphNodeData(label="Hiring Agent", agent_name="hiring")),
            GraphNode(id="funding", data=GraphNodeData(label="Funding Agent", agent_name="funding")),
        ],
        edges=[GraphEdge(id="market-hiring", source="market", target="hiring")],
    )
    capabilities = {
        "hiring": AgentCapability(name="hiring", category="intelligence"),
        "funding": AgentCapability(name="funding", category="intelligence"),
    }

    graph = build_execution_graph(blueprint, capabilities)

    assert graph.selected_agents == ["hiring", "funding"]
    assert [node.id for node in graph.nodes] == ["hiring", "funding"]
    assert [(edge.source, edge.target) for edge in graph.edges] == [("hiring", "funding")]
    validate_execution_graph(graph.nodes, graph.edges)


def test_graph_validator_rejects_orphans_and_unknown_edges() -> None:
    nodes = [
        GraphNode(id="hiring", data=GraphNodeData(label="Hiring Agent", agent_name="hiring")),
        GraphNode(id="funding", data=GraphNodeData(label="Funding Agent", agent_name="funding")),
    ]

    with pytest.raises(PlannerValidationException, match="orphan"):
        validate_execution_graph(nodes, [])
    with pytest.raises(PlannerValidationException, match="unknown"):
        validate_execution_graph(nodes, [GraphEdge(id="bad", source="hiring", target="market")])


@pytest.mark.asyncio
async def test_planner_normalizes_llm_graph_and_executes_combined_mission() -> None:
    repository = FakeRepository()
    llm_blueprint = ExecutionBlueprint(
        mission_id="mission_001",
        selected_agents=["market", "hiring", "funding"],
        planner_reasoning="LLM-selected graph without edges.",
        confidence=0.8,
        nodes=[
            GraphNode(id="market", data=GraphNodeData(label="Market Agent", agent_name="market")),
            GraphNode(id="hiring", data=GraphNodeData(label="Hiring Agent", agent_name="hiring")),
            GraphNode(id="funding", data=GraphNodeData(label="Funding Agent", agent_name="funding")),
        ],
    )
    hiring = FakeAgent("hiring")
    funding = FakeAgent("funding")
    service = PlannerService(
        agent=FakePlannerAgent(llm_blueprint),  # type: ignore[arg-type]
        mission_repository=repository,  # type: ignore[arg-type]
        registry=build_registry(hiring, funding),
    )

    result = await service.run_planner("mission_001")

    assert result.status == MissionStatus.COMPLETED.value
    assert result.planner_output["selected_agents"] == ["hiring", "funding"]
    assert [(edge["source"], edge["target"]) for edge in result.execution_graph["edges"]] == [("hiring", "funding")]
    assert set(result.shared_memory) == {"hiring", "funding"}
    assert funding.starts[0] > hiring.starts[0]


def test_planner_api_uses_service_dependency() -> None:
    mission_id = str(uuid4())

    class FakeService:
        async def run_planner(self, mission_id: str) -> dict[str, Any]:
            return {
                "mission_id": mission_id,
                "status": MissionStatus.COMPLETED.value,
                "execution_graph": {"nodes": [], "edges": []},
                "planner_output": {},
                "shared_memory": {},
                "recommendations": {},
                "runtime": 0,
                "confidence": 0.9,
            }

    app.dependency_overrides[get_planner_service] = lambda: FakeService()
    client = TestClient(app)
    response = client.post("/api/v1/planner/run", json={"mission_id": mission_id})
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["mission_id"] == mission_id


def test_planner_api_rejects_invalid_uuid_before_repository_lookup() -> None:
    mission_id = str(uuid4())

    class FakeService:
        async def run_planner(self, mission_id: str) -> dict[str, Any]:
            raise AssertionError("Service should not be called for invalid mission ids")

    app.dependency_overrides[get_planner_service] = lambda: FakeService()
    client = TestClient(app)
    response = client.post("/api/v1/planner/run", json={"mission_id": mission_id + mission_id})
    app.dependency_overrides.clear()

    assert response.status_code == 422
