from __future__ import annotations

from typing import Any

import pytest

from app.services.firecrawl_service import FirecrawlService
from app.services.tavily_service import TavilyService


class FakeResponse:
    def __init__(self, payload: dict[str, Any], *, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code

    def json(self) -> dict[str, Any]:
        return self.payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeClient:
    def __init__(self, responses: list[FakeResponse | Exception]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    async def post(
        self,
        url: str,
        *,
        json: dict[str, Any],
        headers: dict[str, str],
        timeout: float,
    ) -> FakeResponse:
        self.calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


@pytest.mark.asyncio
async def test_tavily_search_normalizes_results() -> None:
    client = FakeClient(
        [
            FakeResponse(
                {
                    "results": [
                        {
                            "title": "Acme launches AI factory tooling",
                            "url": "https://example.com/acme",
                            "content": "Acme announced new AI automation tooling.",
                            "score": 0.91,
                        }
                    ]
                }
            )
        ]
    )
    service = TavilyService(api_key="test-key", client=client, backoff_seconds=0)

    response = await service.search("Acme AI automation")

    assert response.status == "ok"
    assert response.results[0].title == "Acme launches AI factory tooling"
    assert response.results[0].url == "https://example.com/acme"
    assert response.results[0].score == 0.91
    assert response.results[0].source == "tavily"
    assert client.calls[0]["json"]["query"] == "Acme AI automation"


@pytest.mark.asyncio
async def test_tavily_search_retries_and_returns_empty_results_on_failure() -> None:
    client = FakeClient([RuntimeError("temporary outage"), FakeResponse({"results": []})])
    service = TavilyService(api_key="test-key", client=client, max_retries=1, backoff_seconds=0)

    response = await service.search("Acme news")

    assert response.status == "empty"
    assert response.results == []
    assert len(client.calls) == 2


@pytest.mark.asyncio
async def test_tavily_missing_api_key_returns_error_without_request() -> None:
    client = FakeClient([])
    service = TavilyService(api_key="", client=client)

    response = await service.search("Acme")

    assert response.status == "error"
    assert response.results == []
    assert response.error == "TAVILY_API_KEY is not configured."
    assert client.calls == []


@pytest.mark.asyncio
async def test_tavily_search_multiple_runs_each_query() -> None:
    client = FakeClient(
        [
            FakeResponse({"results": [{"title": "One", "url": "https://one.test"}]}),
            FakeResponse({"results": [{"title": "Two", "url": "https://two.test"}]}),
        ]
    )
    service = TavilyService(api_key="test-key", client=client)

    responses = await service.search_multiple(["one", "two"])

    assert [response.query for response in responses] == ["one", "two"]
    assert [response.results[0].title for response in responses] == ["One", "Two"]


@pytest.mark.asyncio
async def test_firecrawl_scrape_normalizes_page() -> None:
    client = FakeClient(
        [
            FakeResponse(
                {
                    "data": {
                        "markdown": "# Acme\nMain page content",
                        "metadata": {
                            "title": "Acme",
                            "description": "Industrial AI platform",
                            "sourceURL": "https://acme.test",
                        },
                        "links": ["https://acme.test/about", "https://acme.test/contact"],
                    }
                }
            )
        ]
    )
    service = FirecrawlService(api_key="fire-key", client=client)

    response = await service.scrape("https://acme.test")

    assert response.status == "ok"
    assert response.page is not None
    assert response.page.title == "Acme"
    assert response.page.description == "Industrial AI platform"
    assert response.page.content == "# Acme\nMain page content"
    assert response.page.links == ["https://acme.test/about", "https://acme.test/contact"]
    assert response.page.source == "firecrawl"
    assert client.calls[0]["headers"]["Authorization"] == "Bearer fire-key"


@pytest.mark.asyncio
async def test_firecrawl_scrape_multiple_and_missing_api_key() -> None:
    missing_key_client = FakeClient([])
    missing_key_service = FirecrawlService(api_key="", client=missing_key_client)

    missing_key_response = await missing_key_service.scrape("https://acme.test")

    assert missing_key_response.status == "error"
    assert missing_key_response.page is None
    assert missing_key_client.calls == []

    client = FakeClient(
        [
            FakeResponse({"data": {"title": "One", "markdown": "one"}}),
            FakeResponse({"data": {"title": "Two", "markdown": "two"}}),
        ]
    )
    service = FirecrawlService(api_key="fire-key", client=client)

    responses = await service.scrape_multiple(["https://one.test", "https://two.test"])

    assert [response.page.title for response in responses if response.page] == ["One", "Two"]
    assert len(client.calls) == 2
