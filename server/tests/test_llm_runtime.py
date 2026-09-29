from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.llm.base import BaseLLM
from app.llm.cache import LLMCache
from app.llm.manager import LLMManager
from app.llm.models import LLMRequest, LLMResponse
from app.llm.parser import LLMParser
from app.llm.prompt_engine import PromptEngine
from app.api.routes import llm as llm_route
from app.main import app


class DiscoveryResult(BaseModel):
    summary: str


class FakeProvider(BaseLLM):
    provider_name = "fake"
    model_name = "fake-model"

    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, request: LLMRequest) -> LLMResponse:
        self.calls += 1
        return LLMResponse(
            output='{"summary":"cached"}',
            provider=self.provider_name,
            model=self.model_name,
            latency_ms=1,
        )

    async def health_check(self) -> dict[str, Any]:
        return {
            "provider": self.provider_name,
            "model": self.model_name,
            "status": "ok",
            "latency": 1,
        }

    async def count_tokens(self, prompt: str) -> int:
        return len(prompt.split())

    async def validate_output(self, output: str, schema: type[BaseModel] | None = None) -> bool:
        return True


def test_parser_extracts_markdown_json_and_validates_schema() -> None:
    parser = LLMParser()

    result = parser.parse_json('```json\n{"summary":"ready"}\n```', DiscoveryResult)

    assert result.summary == "ready"


def test_parser_skips_non_json_brackets_before_json() -> None:
    parser = LLMParser()
    raw = 'Plan: [market, hiring] should run first. {"summary":"ready"} Done.'

    result = parser.parse_json(raw, DiscoveryResult)

    assert result.summary == "ready"


def test_prompt_engine_replaces_template_placeholders() -> None:
    prompt = PromptEngine().build_prompt(
        system_role="You are the strategy runtime.",
        mission="Find best-fit accounts.",
        memory={"segment": "enterprise"},
        agent_name="Strategy Agent",
        expected_schema=DiscoveryResult,
        template_name="strategy",
    )

    assert "{{mission}}" not in prompt
    assert "Find best-fit accounts." in prompt
    assert "Strategy Agent" in prompt
    assert "Return ONLY valid JSON" in prompt


def test_planner_prompt_includes_available_agents() -> None:
    prompt = PromptEngine().build_prompt(
        system_role="Planner",
        mission="Find best-fit accounts.",
        memory={"Available Agents": [{"name": "market"}, {"name": "recommendation"}]},
        agent_name="planner",
        expected_schema=DiscoveryResult,
        template_name="planner",
    )

    assert "{{available_agents}}" not in prompt
    assert '"name": "market"' in prompt
    assert '"name": "recommendation"' in prompt
    assert "\nplanner\n" not in prompt


@pytest.mark.asyncio
async def test_llm_manager_uses_cache_for_identical_prompts() -> None:
    provider = FakeProvider()
    manager = LLMManager(provider=provider, cache=LLMCache())

    first = await manager.generate_json(
        response_model=DiscoveryResult,
        system_role="System",
        mission="Mission",
        memory=None,
        agent_name="Strategy Agent",
        expected_schema=DiscoveryResult,
        template_name="strategy",
    )
    second = await manager.generate_json(
        response_model=DiscoveryResult,
        system_role="System",
        mission="Mission",
        memory=None,
        agent_name="Strategy Agent",
        expected_schema=DiscoveryResult,
        template_name="strategy",
    )

    assert first.summary == "cached"
    assert second.summary == "cached"
    assert provider.calls == 1


def test_llm_health_route_is_registered(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeManager:
        async def health_check(self) -> dict[str, object]:
            return {
                "provider": "fake",
                "model": "fake-model",
                "status": "ok",
                "latency": 1,
            }

    monkeypatch.setattr(llm_route, "llm_manager", FakeManager())
    client = TestClient(app)

    response = client.get("/api/v1/llm/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "fake"
    assert payload["model"] == "fake-model"
    assert "latency" in payload
