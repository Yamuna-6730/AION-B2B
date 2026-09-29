from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.agents.base.enums import AgentState
from app.agents.base.response import AgentResponse
from app.agents.base.task import AgentTask
from app.agents.catalog import INITIAL_AGENT_CLASSES
from app.agents.market_discovery import MarketDiscoveryAgent
from app.api.routes.market_discovery import get_market_discovery_service
from app.main import app
from app.schemas.external import ScrapedPage, ScrapeResponse, SearchResponse, SearchResult
from app.schemas.market_discovery import CompanyEvidence, DiscoveredCompany, CompanyExtractionResult, MarketDiscoveryOutput
from app.services.company_extractor import CompanyExtractor
from app.services.market_discovery_service import MarketDiscoveryService
from app.supabase.repositories.market_discovery_repository import MarketDiscoveryRepository


class FakeTavily:
    def __init__(self) -> None:
        self.queries: list[str] = []

    async def search_multiple(self, queries: list[str]) -> list[SearchResponse]:
        self.queries = queries
        return [
            SearchResponse(
                query=queries[0],
                results=[
                    SearchResult(
                        title="Acme AI",
                        url="https://www.acme.ai/blog/post",
                        content="Acme AI builds industrial automation.",
                        score=0.91,
                        source="tavily",
                    ),
                    SearchResult(
                        title="Acme duplicate",
                        url="https://acme.ai/about",
                        content="Duplicate result.",
                        score=0.75,
                        source="tavily",
                    ),
                    SearchResult(
                        title="Low confidence",
                        url="https://low.example",
                        content="Low confidence result.",
                        score=0.1,
                        source="tavily",
                    ),
                ],
            )
        ]


class FakeFirecrawl:
    def __init__(self) -> None:
        self.urls: list[str] = []

    async def scrape_multiple(self, urls: list[str]) -> list[ScrapeResponse]:
        self.urls = urls
        return [
            ScrapeResponse(
                url=url,
                status="ok",
                page=ScrapedPage(
                    title="Acme AI",
                    description="Industrial AI automation platform",
                    content="Acme AI sells industrial AI automation to manufacturers using computer vision.",
                    metadata={"title": "Acme AI"},
                    links=["https://acme.ai/careers"],
                    url=url,
                    source="firecrawl",
                ),
            )
            for url in urls
        ]


class FakeExtractor:
    def __init__(self) -> None:
        self.scraped_pages: list[dict[str, Any]] = []

    async def extract(self, **kwargs: Any) -> CompanyExtractionResult:
        self.scraped_pages = kwargs["scraped_pages"]
        return CompanyExtractionResult(
            companies=[
                DiscoveredCompany(
                    company_name="Acme AI",
                    website="https://www.acme.ai",
                    summary="Industrial AI automation platform.",
                    industry="Industrial AI",
                    country=None,
                    headquarters=None,
                    products=["Computer vision automation"],
                    services=[],
                    use_cases=["Manufacturing inspection"],
                    technologies=["Computer vision"],
                    customer_logos=[],
                    careers_page=None,
                    about_page=None,
                    evidence=[
                        CompanyEvidence(
                            source="Website",
                            url="https://www.acme.ai",
                            fact="Acme AI sells industrial AI automation to manufacturers.",
                        )
                    ],
                )
            ]
        )


class EmptyTavily:
    async def search_multiple(self, queries: list[str]) -> list[SearchResponse]:
        return [SearchResponse(query=query, results=[]) for query in queries]


class FailingFirecrawl:
    async def scrape_multiple(self, urls: list[str]) -> list[ScrapeResponse]:
        return [ScrapeResponse(url=url, status="error", error="blocked") for url in urls]


class DuplicateExtractor(FakeExtractor):
    async def extract(self, **kwargs: Any) -> CompanyExtractionResult:
        company = DiscoveredCompany(company_name="Acme AI", website="https://acme.ai")
        better = DiscoveredCompany(company_name="Acme AI", website="https://www.acme.ai")
        return CompanyExtractionResult(companies=[company, better])


class FakeLLMResponse:
    def __init__(self, output: str) -> None:
        self.output = output


class FakeParser:
    def __init__(self, should_raise: bool = False) -> None:
        self.should_raise = should_raise

    def parse_json(self, raw_output: str, response_model: type[CompanyExtractionResult]) -> CompanyExtractionResult:
        if self.should_raise:
            raise ValueError("malformed json")
        return response_model.model_validate_json(raw_output)


class FakeRuntime:
    def __init__(self, output: str, *, should_raise: bool = False) -> None:
        self.output = output
        self.parser = FakeParser(should_raise=should_raise)

    async def generate(self, **kwargs: Any) -> FakeLLMResponse:
        return FakeLLMResponse(self.output)


class FakeSupabaseResult:
    def __init__(self, data: Any) -> None:
        self.data = data


class FakeSupabaseTable:
    def __init__(self, client: "FakeSupabaseClient") -> None:
        self.client = client
        self.operation = ""
        self.payload: Any = None
        self.filters: dict[str, Any] = {}

    def insert(self, payload: Any) -> "FakeSupabaseTable":
        self.operation = "insert"
        self.payload = payload
        return self

    def upsert(self, payload: Any, on_conflict: str = "") -> "FakeSupabaseTable":
        self.operation = "insert"  # Treat upsert similarly to insert for the fake table logic
        self.payload = payload
        return self

    def select(self, columns: str) -> "FakeSupabaseTable":
        self.operation = "select"
        return self

    def eq(self, column: str, value: Any) -> "FakeSupabaseTable":
        self.filters[column] = value
        return self

    def execute(self) -> FakeSupabaseResult:
        if self.operation == "insert":
            if self.client.reject_unsupported_columns and self._has_unsupported_columns(self.payload):
                raise ValueError("Could not find the 'headquarters' column")
            self.client.rows.extend(self.payload)
            return FakeSupabaseResult(self.payload)
        if self.operation == "select":
            mission_id = self.filters.get("mission_id")
            return FakeSupabaseResult([row for row in self.client.rows if row.get("mission_id") == mission_id])
        return FakeSupabaseResult([])

    def _has_unsupported_columns(self, payload: Any) -> bool:
        if not isinstance(payload, list):
            return False
        unsupported = {"headquarters", "careers_page", "about_page"}
        return any(isinstance(row, dict) and any(key in row for key in unsupported) for row in payload)


class FakeSupabaseClient:
    def __init__(self, *, reject_unsupported_columns: bool = False) -> None:
        self.rows: list[dict[str, Any]] = []
        self.reject_unsupported_columns = reject_unsupported_columns

    def table(self, name: str) -> FakeSupabaseTable:
        assert name == "market_discovery_results"
        return FakeSupabaseTable(self)


@pytest.mark.asyncio
async def test_market_discovery_agent_collects_scrapes_and_extracts_companies() -> None:
    tavily = FakeTavily()
    firecrawl = FakeFirecrawl()
    extractor = FakeExtractor()
    agent = MarketDiscoveryAgent(tavily_service=tavily, firecrawl_service=firecrawl, extractor=extractor)  # type: ignore[arg-type]
    task = AgentTask(
        mission_id=str(uuid4()),
        task_id="market_001",
        agent_name="market",
        objective="Find industrial AI companies in Germany.",
        context={
            "mission": {
                "objective": "Find industrial AI companies in Germany.",
                "strategy": {"industry": "Industrial AI", "countries": ["Germany"], "technologies": ["Computer vision"]},
                "icp": {"industry": "Manufacturing"},
            },
        },
    )

    response = await agent.run(task)

    assert response.success is True
    assert response.status == AgentState.COMPLETED
    assert response.output["total_companies"] == 1
    assert response.output["companies"][0]["company_name"] == "Acme AI"
    assert len(tavily.queries) >= 3
    assert firecrawl.urls == ["https://www.acme.ai"]
    assert extractor.scraped_pages[0]["content"].startswith("Acme AI sells")
    assert response.output["raw_tavily_results"]



@pytest.mark.asyncio
async def test_market_discovery_tavily_zero_results_returns_empty_with_shared_counts() -> None:
    agent = MarketDiscoveryAgent(tavily_service=EmptyTavily(), firecrawl_service=FakeFirecrawl(), extractor=FakeExtractor())  # type: ignore[arg-type]
    task = AgentTask(
        mission_id=str(uuid4()),
        task_id="market_empty",
        agent_name="market",
        objective="Find companies.",
        context={"mission": {"objective": "Find companies."}},
    )

    response = await agent.run(task)

    assert response.output["total_companies"] == 0
    assert response.output["company_count"] == 0
    assert response.output["scraped_pages"] == []


@pytest.mark.asyncio
async def test_market_discovery_firecrawl_failure_does_not_call_extractor_with_pages() -> None:
    extractor = FakeExtractor()
    agent = MarketDiscoveryAgent(tavily_service=FakeTavily(), firecrawl_service=FailingFirecrawl(), extractor=extractor)  # type: ignore[arg-type]
    task = AgentTask(
        mission_id=str(uuid4()),
        task_id="market_firecrawl_fail",
        agent_name="market",
        objective="Find companies.",
        context={"mission": {"objective": "Find companies."}},
    )

    response = await agent.run(task)

    assert response.output["total_companies"] == 0
    assert extractor.scraped_pages == []


@pytest.mark.asyncio
async def test_market_discovery_removes_duplicate_extracted_companies() -> None:
    agent = MarketDiscoveryAgent(tavily_service=FakeTavily(), firecrawl_service=FakeFirecrawl(), extractor=DuplicateExtractor())  # type: ignore[arg-type]
    task = AgentTask(
        mission_id=str(uuid4()),
        task_id="market_dupes",
        agent_name="market",
        objective="Find companies.",
        context={"mission": {"objective": "Find companies."}},
    )

    response = await agent.run(task)

    assert response.output["total_companies"] == 1
    assert response.output["companies"][0]["company_name"] == "Acme AI"


@pytest.mark.asyncio
async def test_company_extractor_raises_on_malformed_json() -> None:
    extractor = CompanyExtractor(ai_runtime=FakeRuntime("{bad json", should_raise=True))  # type: ignore[arg-type]

    with pytest.raises(ValueError):
        await extractor.extract(
            scraped_pages=[{"url": "https://acme.ai", "content": "Acme AI"}],
        )


@pytest.mark.asyncio
async def test_company_extractor_returns_valid_json_companies() -> None:
    raw = (
        '{"companies":[{"company_name":"Acme AI","website":"https://acme.ai"}]}'
    )
    extractor = CompanyExtractor(ai_runtime=FakeRuntime(raw))  # type: ignore[arg-type]

    result = await extractor.extract(
        scraped_pages=[{"url": "https://acme.ai", "content": "Acme AI"}],
    )

    assert result.companies[0].company_name == "Acme AI"


@pytest.mark.asyncio
async def test_market_discovery_agent_reuses_shared_memory() -> None:
    existing = MarketDiscoveryOutput(
        companies=[
            DiscoveredCompany(
                company_name="Cached Co",
                website="https://cached.example",
            )
        ],
        total_companies=1,
    )
    agent = MarketDiscoveryAgent(tavily_service=FakeTavily(), firecrawl_service=FakeFirecrawl(), extractor=FakeExtractor())  # type: ignore[arg-type]
    task = AgentTask(
        mission_id=str(uuid4()),
        task_id="market_002",
        agent_name="market",
        objective="Find companies.",
        context={"mission": {"objective": "Find companies."}, "shared_memory": {"market_discovery": existing.model_dump(mode="json")}},
    )

    response = await agent.run(task)

    assert response.output["companies"][0]["company_name"] == "Cached Co"
    assert response.metadata["reused"] is True


def test_market_discovery_agent_is_registered_as_market_agent() -> None:
    market_classes = [agent_class for agent_class in INITIAL_AGENT_CLASSES if getattr(agent_class, "name", "") == "market"]

    assert market_classes == [MarketDiscoveryAgent]


@pytest.mark.asyncio
async def test_market_discovery_service_persists_and_returns_shared_memory() -> None:
    mission_id = str(uuid4())

    class FakeMissionRepository:
        def __init__(self) -> None:
            self.metadata: dict[str, Any] | None = None
            self.shared_memory: dict[str, Any] | None = None

        async def get_mission(self, requested_id: str) -> dict[str, Any]:
            assert requested_id == mission_id
            return {"id": mission_id, "objective": "Find industrial AI companies.", "strategy": {}, "icp": {}, "metadata": {"existing": True}}

        async def update_metadata(self, requested_id: str, metadata: dict[str, Any]) -> dict[str, Any]:
            assert requested_id == mission_id
            self.metadata = metadata
            return {"id": requested_id, "metadata": metadata}

        async def update_shared_memory(self, requested_id: str, shared_memory: dict[str, Any]) -> dict[str, Any]:
            assert requested_id == mission_id
            self.shared_memory = shared_memory
            return {"id": requested_id, "shared_memory": shared_memory}

    class FakeAgent:
        name = "market"

        async def run(self, task: AgentTask) -> AgentResponse:
            output = MarketDiscoveryOutput(
                companies=[
                    DiscoveredCompany(
                        company_name="Acme AI",
                        website="https://acme.ai",
                    )
                ],
                total_companies=1,
            )
            return AgentResponse(
                success=True,
                mission_id=task.mission_id,
                task_id=task.task_id,
                agent_name="market",
                status=AgentState.COMPLETED,
                confidence=1.0,
                reasoning="done",
                execution_time=0.0,
                output=output.model_dump(mode="json"),
            )

    class FakeMarketRepository:
        table_name = "market_discovery_results"

        def __init__(self) -> None:
            self.saved: list[DiscoveredCompany] = []

        async def save_results(self, mission_id: str, companies: list[DiscoveredCompany]) -> list[dict[str, Any]]:
            self.saved = companies
            return [{"company_name": company.company_name, "mission_id": mission_id} for company in companies]


    market_repository = FakeMarketRepository()
    mission_repository = FakeMissionRepository()
    service = MarketDiscoveryService(
        agent=FakeAgent(),  # type: ignore[arg-type]
        mission_repository=mission_repository,  # type: ignore[arg-type]
        market_repository=market_repository,  # type: ignore[arg-type]
    )

    response = await service.run(mission_id)

    assert response.market_discovery.total_companies == 1
    assert response.shared_memory["market_discovery"]["company_count"] == 1
    assert market_repository.saved[0].company_name == "Acme AI"
    assert response.saved_company_count == 1
    assert response.database_status.verified is True
    assert mission_repository.metadata is not None
    assert mission_repository.metadata["existing"] is True
    assert mission_repository.metadata["market_discovery"]["completed"] is True


def test_market_discovery_api_uses_service_dependency() -> None:
    mission_id = str(uuid4())

    class FakeService:
        async def run(self, requested_id: str) -> MarketDiscoveryRunResponse:
            assert requested_id == mission_id
            return MarketDiscoveryRunResponse(
                mission_id=requested_id,
                status="COMPLETED",
                market_discovery=MarketDiscoveryOutput(total_companies=0),
            )

    from app.schemas.market_discovery import MarketDiscoveryRunResponse

    app.dependency_overrides[get_market_discovery_service] = lambda: FakeService()
    client = TestClient(app)
    response = client.post("/api/v1/market-discovery/run", json={"mission_id": mission_id})
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["mission_id"] == mission_id


def test_market_discovery_repository_maps_company_to_row() -> None:
    repository = MarketDiscoveryRepository(client=object())
    mission_id = str(uuid4())
    company = DiscoveredCompany(
        company_name="Acme AI",
        website="https://acme.ai",
        summary="Industrial AI.",
        industry="Industrial AI",
        country="Germany",
        products=["Vision"],
        use_cases=["Inspection"],
        technologies=["Computer vision"],
        customer_logos=["FactoryCo"],
        evidence=[CompanyEvidence(source="Website", url="https://acme.ai", fact="Builds industrial AI.")],
        metadata={"discovered_from": "tavily"},
    )

    row = repository._row(mission_id, company)

    assert row["mission_id"] == mission_id
    assert row["company_name"] == "Acme AI"
    assert row["evidence"][0]["fact"] == "Builds industrial AI."
    assert row["products"] == ["Vision"]


@pytest.mark.asyncio
async def test_market_discovery_repository_inserts_and_verifies_rows() -> None:
    client = FakeSupabaseClient()
    repository = MarketDiscoveryRepository(client=client)
    mission_id = str(uuid4())
    company = DiscoveredCompany(company_name="Acme AI", website="https://acme.ai")

    rows = await repository.save_results(mission_id, [company])

    assert len(rows) == 1
    assert rows[0]["mission_id"] == mission_id


@pytest.mark.asyncio
async def test_market_discovery_repository_sanitizes_unsupported_columns() -> None:
    client = FakeSupabaseClient(reject_unsupported_columns=True)
    repository = MarketDiscoveryRepository(client=client)
    mission_id = str(uuid4())
    company = DiscoveredCompany(
        company_name="Acme AI",
        website="https://acme.ai",
        headquarters="Berlin",
        services=["AI consulting"],
        careers_page="https://acme.ai/careers",
        about_page="https://acme.ai/about",
    )

    rows = await repository.save_results(mission_id, [company])

    assert len(rows) == 1
    assert rows[0]["company_name"] == "Acme AI"
    assert "headquarters" not in client.rows[0]
    assert rows[0]["company_name"] == "Acme AI"


@pytest.mark.asyncio
async def test_market_discovery_repository_read_back_by_mission() -> None:
    client = FakeSupabaseClient()
    repository = MarketDiscoveryRepository(client=client)
    mission_id = str(uuid4())
    other_id = str(uuid4())
    client.rows.extend(
        [
            {"mission_id": mission_id, "company_name": "Acme AI"},
            {"mission_id": other_id, "company_name": "Other AI"},
        ]
    )

    rows = await repository.list_by_mission(mission_id)

    assert [row["company_name"] for row in rows] == ["Acme AI"]

