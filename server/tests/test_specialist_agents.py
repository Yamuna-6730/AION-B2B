from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.agents.base.task import AgentTask
from app.agents.catalog import ACTIVE_INTELLIGENCE_AGENT_CLASSES, INITIAL_AGENT_CLASSES
from app.agents.discovery.intelligence_agents import FundingIntelligenceAgent, HiringIntelligenceAgent
from app.agents.planner.planner_agent import PlannerAgent
from app.schemas.external import ScrapeResponse, SearchResponse, SearchResult


class FakeTavily:
    def __init__(self, response: SearchResponse) -> None:
        self.response = response
        self.queries: list[str] = []

    async def search(self, query: str) -> SearchResponse:
        self.queries.append(query)
        return self.response


class FakeFirecrawl:
    def __init__(self, responses: list[ScrapeResponse]) -> None:
        self.responses = responses

    async def scrape_multiple(self, urls: list[str]) -> list[ScrapeResponse]:
        return self.responses


def task(name: str) -> AgentTask:
    return AgentTask(mission_id='mission_001', task_id='task_001', agent_name=name, objective='Analyze Acme Corp hiring and funding activity.', context={'company': 'Acme Corp'})


@pytest.mark.asyncio
async def test_hiring_agent_preserves_source_evidence() -> None:
    source = SearchResult(title='Acme careers: AI platform roles', url='https://acme.example/careers', content='Python and cloud engineering roles are open.', score=.9, source='tavily')
    agent = HiringIntelligenceAgent(tavily_service=FakeTavily(SearchResponse(query='q', results=[source])), firecrawl_service=FakeFirecrawl([]))  # type: ignore[arg-type]
    response = await agent.run(task('hiring'))
    assert response.output['company'] == 'Acme Corp'
    assert response.output['sources'][0]['url'] == source.url
    assert 'python' in response.output['technology_signals']


@pytest.mark.asyncio
async def test_hiring_agent_handles_empty_and_malformed_sources() -> None:
    response = SimpleNamespace(status='ok', results=[object()])
    agent = HiringIntelligenceAgent(tavily_service=FakeTavily(response), firecrawl_service=FakeFirecrawl([]))  # type: ignore[arg-type]
    result = await agent.run(task('hiring'))
    assert result.output['sources'] == []
    assert result.confidence == 0.0


@pytest.mark.asyncio
async def test_hiring_agent_handles_tavily_and_firecrawl_failure() -> None:
    source = SearchResult(title='Careers', url='https://acme.example/careers', content='', score=.8, source='tavily')
    agent = HiringIntelligenceAgent(tavily_service=FakeTavily(SearchResponse(query='q', status='error', error='unavailable')), firecrawl_service=FakeFirecrawl([]))  # type: ignore[arg-type]
    assert (await agent.run(task('hiring'))).output['sources'] == []
    agent = HiringIntelligenceAgent(tavily_service=FakeTavily(SearchResponse(query='q', results=[source])), firecrawl_service=FakeFirecrawl([ScrapeResponse(url=source.url, status='error', error='blocked')]))  # type: ignore[arg-type]
    assert (await agent.run(task('hiring'))).output['sources'][0]['url'] == source.url


@pytest.mark.asyncio
async def test_funding_agent_preserves_unknown_amount_and_source_evidence() -> None:
    source = SearchResult(title='Acme announces investment', url='https://acme.example/news', content='Investors joined the round.', score=.9, source='tavily')
    agent = FundingIntelligenceAgent(tavily_service=FakeTavily(SearchResponse(query='q', results=[source])), firecrawl_service=FakeFirecrawl([]))  # type: ignore[arg-type]
    response = await agent.run(task('funding'))
    assert response.output['funding_events'] == []
    assert response.output['total_known_funding'] is None
    assert response.output['sources'][0]['url'] == source.url


@pytest.mark.asyncio
async def test_funding_agent_handles_empty_malformed_tavily_and_firecrawl_failure() -> None:
    agent = FundingIntelligenceAgent(tavily_service=FakeTavily(SearchResponse(query='q', status='error', error='unavailable')), firecrawl_service=FakeFirecrawl([]))  # type: ignore[arg-type]
    assert (await agent.run(task('funding'))).output['sources'] == []
    malformed = SimpleNamespace(status='ok', results=[object()])
    agent = FundingIntelligenceAgent(tavily_service=FakeTavily(malformed), firecrawl_service=FakeFirecrawl([]))  # type: ignore[arg-type]
    assert (await agent.run(task('funding'))).output['sources'] == []


def test_specialists_are_registered_and_fallback_planner_selects_only_requested_capabilities() -> None:
    catalog_names = {agent.name for agent in (agent_class() for agent_class in INITIAL_AGENT_CLASSES)}
    active_names = {agent.name for agent in (agent_class() for agent_class in ACTIVE_INTELLIGENCE_AGENT_CLASSES)}
    assert {'hiring', 'funding'} <= catalog_names
    assert active_names == {'hiring', 'funding'}
    planner = PlannerAgent()
    available = [{'name': 'hiring'}, {'name': 'funding'}]
    assert planner._fallback_blueprint('m1', {'objective': 'Analyze Acme hiring'}, available, 'test').selected_agents == ['hiring']
    assert planner._fallback_blueprint('m1', {'objective': 'Analyze Acme funding'}, available, 'test').selected_agents == ['funding']
    combined = planner._fallback_blueprint('m1', {'objective': 'Analyze Acme hiring and funding'}, available, 'test')
    assert combined.selected_agents == ['hiring', 'funding']
    assert 'market' not in combined.selected_agents
