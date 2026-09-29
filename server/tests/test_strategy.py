from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.agents.base.task import AgentTask
from app.agents.intelligence.strategy_agent import StrategyAgent, StrategyValidationError
from app.api.routes.strategy import get_strategy_service
from app.main import app
from app.schemas.strategy import (
    BusinessTrigger,
    ICPProfile,
    MissionIntelligence,
    MissionMetadata,
    MissionStatus,
    Persona,
    QualificationRule,
    RecommendedAgent,
    StrategyAnalyzeRequest,
    TechnologyPreference,
)
from app.services.strategy_service import StrategyService
from app.supabase.repositories.mission_repository import MissionRepository


def build_intelligence(mission_id: str = "mission_001") -> MissionIntelligence:
    return MissionIntelligence(
        mission_id=mission_id,
        title="Find AI Customers",
        objective="We sell an AI Copilot for Manufacturing companies in Germany.",
        domain="Enterprise AI",
        industry="Manufacturing",
        countries=["Germany"],
        product="AI Copilot",
        product_category="Enterprise AI Platform",
        ideal_company_size="500+ employees",
        estimated_revenue="100M+",
        icp=ICPProfile(
            company_size="500+ employees",
            revenue="100M+",
            geography=["Germany"],
            industry="Manufacturing",
            maturity_signals=["Digital transformation", "Cloud migration"],
        ),
        target_personas=[
            Persona(
                title="CTO",
                seniority="Executive",
                department="Technology",
                pains=["Operational efficiency"],
                buying_role="Economic buyer",
            )
        ],
        technology_preferences=[
            TechnologyPreference(
                technology="Azure",
                category="Cloud",
                rationale="Common enterprise AI deployment environment.",
            )
        ],
        qualification_rules=[
            QualificationRule(
                criterion="Employee count",
                operator=">=",
                value="500",
                rationale="Enterprise readiness signal.",
            )
        ],
        business_triggers=[
            BusinessTrigger(
                name="Hiring AI Engineers",
                description="Indicates active AI investment.",
                priority=5,
            )
        ],
        recommended_agents=[
            RecommendedAgent(
                name="Market",
                reason="Find candidate accounts in the target segment.",
                priority=5,
            )
        ],
        confidence=0.96,
        reasoning="The mission names AI, manufacturing, and Germany directly.",
        metadata=MissionMetadata(assumptions=[]),
    )


class FakeRuntime:
    def __init__(self, intelligence: MissionIntelligence) -> None:
        self.intelligence = intelligence
        self.calls: list[dict[str, Any]] = []

    async def generate_json(self, **kwargs: Any) -> MissionIntelligence:
        self.calls.append(kwargs)
        return self.intelligence


class FakeRepository:
    def __init__(self) -> None:
        self.statuses: list[MissionStatus] = []
        self.saved: MissionIntelligence | None = None

    async def create_mission(self, *, title: str, objective: str) -> dict[str, Any]:
        return {"id": "mission_001", "title": title, "objective": objective}

    async def update_strategy(self, mission_id: str, intelligence: MissionIntelligence) -> dict[str, Any]:
        self.saved = intelligence
        return {"id": mission_id}

    async def update_status(self, mission_id: str, status: MissionStatus) -> dict[str, Any]:
        self.statuses.append(status)
        return {"id": mission_id, "status": status.value}


@pytest.mark.asyncio
async def test_strategy_agent_uses_ai_runtime_and_validates_output() -> None:
    runtime = FakeRuntime(build_intelligence("llm_generated_id"))
    agent = StrategyAgent(ai_runtime=runtime)  # type: ignore[arg-type]
    task = AgentTask(
        mission_id="mission_001",
        task_id="task_001",
        agent_name="strategy",
        objective="We sell an AI Copilot for Manufacturing companies in Germany.",
        context={"title": "Find AI Customers"},
    )

    response = await agent.run(task)

    assert response.success is True
    assert response.output["mission_id"] == "mission_001"
    assert response.output["industry"] == "Manufacturing"
    assert runtime.calls[0]["template_name"] == "strategy"
    assert runtime.calls[0]["response_model"] is MissionIntelligence


@pytest.mark.asyncio
async def test_strategy_agent_rejects_missing_objective() -> None:
    agent = StrategyAgent(ai_runtime=FakeRuntime(build_intelligence()))  # type: ignore[arg-type]
    task = AgentTask(
        mission_id="mission_001",
        task_id="task_001",
        agent_name="strategy",
        objective=" ",
    )

    with pytest.raises(StrategyValidationError):
        await agent.run(task)


@pytest.mark.asyncio
async def test_strategy_service_updates_status_and_persists_intelligence() -> None:
    repository = FakeRepository()
    service = StrategyService(
        agent=StrategyAgent(ai_runtime=FakeRuntime(build_intelligence())),  # type: ignore[arg-type]
        mission_repository=repository,  # type: ignore[arg-type]
    )

    result = await service.analyze(
        StrategyAnalyzeRequest(
            title="Find AI Customers",
            objective="We sell an AI Copilot for Manufacturing companies in Germany.",
        )
    )

    assert result.mission_id == "mission_001"
    assert repository.statuses == [MissionStatus.STRATEGY_RUNNING]
    assert repository.saved is not None
    assert repository.saved.confidence == 0.96


class FakeSupabaseResponse:
    def __init__(self, data: Any) -> None:
        self.data = data


class FakeSupabaseTable:
    def __init__(self) -> None:
        self.insert_payload: dict[str, Any] | None = None
        self.update_payload: dict[str, Any] | None = None
        self.insert_payloads: list[dict[str, Any]] = []

    def insert(self, payload: dict[str, Any]) -> FakeSupabaseTable:
        self.insert_payload = payload
        self.insert_payloads.append(payload.copy())
        return self

    def update(self, payload: dict[str, Any]) -> FakeSupabaseTable:
        self.update_payload = payload
        return self

    def eq(self, field: str, value: str) -> FakeSupabaseTable:
        return self

    def execute(self) -> FakeSupabaseResponse:
        if self.insert_payload is not None:
            return FakeSupabaseResponse([self.insert_payload | {"id": "mission_001"}])
        return FakeSupabaseResponse([self.update_payload or {}])


class FakeSupabaseClient:
    def __init__(self) -> None:
        self.table_instance = FakeSupabaseTable()

    def table(self, name: str) -> FakeSupabaseTable:
        assert name == "missions"
        return self.table_instance


@pytest.mark.asyncio
async def test_mission_repository_create_uses_actual_mission_columns() -> None:
    client = FakeSupabaseClient()
    repository = MissionRepository(client=client)

    await repository.create_mission(
        title="Find AI Customers",
        objective="Find manufacturers likely to buy AI.",
    )

    payload = client.table_instance.insert_payload
    assert payload is not None
    assert payload["title"] == "Find AI Customers"
    assert payload["objective"] == "Find manufacturers likely to buy AI."
    assert "name" not in payload


class MissingTitleColumnTable(FakeSupabaseTable):
    def execute(self) -> FakeSupabaseResponse:
        if self.insert_payload is not None and "title" in self.insert_payload:
            raise Exception("Could not find the 'title' column of 'missions' in the schema cache")
        return super().execute()


class MissingTitleColumnClient(FakeSupabaseClient):
    def __init__(self) -> None:
        self.table_instance = MissingTitleColumnTable()


@pytest.mark.asyncio
async def test_mission_repository_retries_create_without_missing_schema_columns() -> None:
    client = MissingTitleColumnClient()
    repository = MissionRepository(client=client)

    mission = await repository.create_mission(
        title="Find AI Customers",
        objective="Find manufacturers likely to buy AI.",
    )

    assert mission["id"] == "mission_001"
    assert "title" in client.table_instance.insert_payloads[0]
    assert "title" not in client.table_instance.insert_payloads[1]


@pytest.mark.asyncio
async def test_mission_repository_updates_strategy_columns() -> None:
    client = FakeSupabaseClient()
    repository = MissionRepository(client=client)
    intelligence = build_intelligence()

    await repository.update_strategy("mission_001", intelligence)

    payload = client.table_instance.update_payload
    assert payload is not None
    assert payload["strategy"]["mission_id"] == "mission_001"
    assert payload["icp"]["company_size"] == "500+ employees"
    assert payload["blueprint"]["recommended_agents"][0]["name"] == "Market"
    assert payload["confidence"] == 0.96
    assert payload["status"] == MissionStatus.STRATEGY_COMPLETED.value


def test_strategy_api_returns_mission_intelligence() -> None:
    class FakeStrategyService:
        async def analyze(self, request: StrategyAnalyzeRequest) -> MissionIntelligence:
            intelligence = build_intelligence()
            return intelligence.model_copy(update={"title": request.title, "objective": request.objective})

    app.dependency_overrides[get_strategy_service] = lambda: FakeStrategyService()
    client = TestClient(app)

    response = client.post(
        "/api/v1/strategy/analyze",
        json={
            "title": "Find AI Customers",
            "objective": "We sell an AI Copilot for Manufacturing companies in Germany.",
        },
    )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    payload = response.json()
    assert payload["industry"] == "Manufacturing"
    assert payload["recommended_agents"][0]["name"] == "Market"


@pytest.mark.asyncio
async def test_mission_repository_casts_estimated_duration_for_integer_column() -> None:
    client = FakeSupabaseClient()
    repository = MissionRepository(client=client)

    await repository.update_estimates(
        "mission_001",
        estimated_duration=1.4,
        estimated_cost=0.0,
        confidence=0.5,
    )

    payload = client.table_instance.update_payload
    assert payload is not None
    assert payload["estimated_duration"] == 1
    assert isinstance(payload["estimated_duration"], int)


@pytest.mark.asyncio
async def test_mission_repository_stores_recommendations_inside_metadata() -> None:
    class MetadataTable(FakeSupabaseTable):
        def __init__(self) -> None:
            super().__init__()
            self.select_called = False

        def select(self, value: str) -> MetadataTable:
            self.select_called = True
            return self

        def single(self) -> MetadataTable:
            return self

        def execute(self) -> FakeSupabaseResponse:
            if self.select_called and self.update_payload is None:
                self.select_called = False
                return FakeSupabaseResponse({"id": "mission_001", "metadata": {"existing": True}})
            return super().execute()

    class MetadataClient(FakeSupabaseClient):
        def __init__(self) -> None:
            self.table_instance = MetadataTable()

    client = MetadataClient()
    repository = MissionRepository(client=client)

    await repository.update_recommendations("mission_001", {"companies": []})

    payload = client.table_instance.update_payload
    assert payload is not None
    assert "recommendations" not in payload
    assert payload["metadata"]["existing"] is True
    assert payload["metadata"]["recommendations"] == {"companies": []}
