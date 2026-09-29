from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from app.agents.base.base_agent import BaseAgent
from app.agents.base.enums import AgentState
from app.agents.base.response import AgentResponse
from app.agents.base.task import AgentTask
from app.core.exceptions import AionError
from app.core.logger import agent_logger
from app.schemas.external import ScrapeResponse, SearchResponse, SearchResult
from app.schemas.market_discovery import DiscoveredCompany, MarketDiscoveryOutput
from app.services.company_extractor import CompanyExtractor
from app.services.firecrawl_service import FirecrawlService
from app.services.tavily_service import TavilyService


class MarketDiscoveryAgentError(AionError):
    error_code = "MARKET_DISCOVERY_AGENT_ERROR"


class MarketDiscoveryValidationError(MarketDiscoveryAgentError):
    status_code = 422
    error_code = "MARKET_DISCOVERY_VALIDATION_ERROR"


class MarketDiscoveryAgent(BaseAgent):
    """Discovers companies matching mission criteria and produces evidence."""

    name = "market"
    description = "Discovers candidate companies matching mission strategy and ICP using external search and website evidence."
    category = "discovery"
    version = "0.1.0"
    priority = 2
    supported_inputs = ("mission", "strategy", "icp", "shared_memory")
    supported_outputs = ("market_discovery",)

    def __init__(
        self,
        *,
        tavily_service: TavilyService | None = None,
        firecrawl_service: FirecrawlService | None = None,
        extractor: CompanyExtractor | None = None,
    ) -> None:
        self.tavily_service = tavily_service or TavilyService()
        self.firecrawl_service = firecrawl_service or FirecrawlService()
        self.extractor = extractor or CompanyExtractor()

    async def initialize(self) -> None:
        return None

    async def validate(self, task: AgentTask) -> bool:
        if task.agent_name and task.agent_name != self.name:
            return False
        return bool(task.mission_id and task.context.get("mission"))

    async def run(self, task: AgentTask) -> AgentResponse:
        started = time.perf_counter()
        if not await self.validate(task):
            raise MarketDiscoveryValidationError("Market discovery requires a mission context.")

        shared_memory = task.context.get("shared_memory") or {}
        existing = shared_memory.get("market_discovery")
        if isinstance(existing, dict) and existing.get("companies"):
            output = MarketDiscoveryOutput.model_validate(existing)
            return self._response(task, output, time.perf_counter() - started, reused=True)

        mission = self._dict(task.context.get("mission"))
        strategy = self._dict(task.context.get("strategy") or mission.get("strategy"))
        icp = self._dict(task.context.get("icp") or mission.get("icp"))
        agent_logger.info("Mission Loaded", mission_id=task.mission_id)
        queries = self._generate_queries(mission=mission, strategy=strategy, icp=icp)
        agent_logger.info("Queries Generated", mission_id=task.mission_id, count=len(queries), queries=queries)
        search_responses = await self.tavily_service.search_multiple(queries)

        print("\n" + "=" * 80)
        print("TAVILY RESULTS")
        print("=" * 80)

        for i, response in enumerate(search_responses, start=1):
            print(f"\n[{i}]")
            print("Query :", self._console_text(response.query))
            print("Provider :", self._console_text(response.provider))
            for r in response.results:
                print(" Title :", self._console_text(getattr(r, "title", None)))
                print(" URL   :", self._console_text(getattr(r, "url", None)))
                print(" Score :", getattr(r, "score", None))

        print("=" * 80 + "\n")

        tavily_count = sum(len(response.results) for response in search_responses)
        agent_logger.info("Tavily Results", mission_id=task.mission_id, results=tavily_count)
        raw_results = self._raw_tavily_results(search_responses)
        candidates, skipped_results = self._unique_high_confidence_results(search_responses)
        agent_logger.info(
            "Unique Domains",
            mission_id=task.mission_id,
            unique_domains=len(candidates),
            skipped_items=len(skipped_results),
            skipped_reasons=skipped_results,
        )
        scrape_responses = await self.firecrawl_service.scrape_multiple([candidate.url for candidate in candidates])
        print("\n" + "=" * 80)
        print("FIRECRAWL PAGES")
        print("=" * 80)

        for page in scrape_responses:
            print("\nURL:", self._console_text(getattr(page, "url", None)))
            title = getattr(getattr(page, "page", None), "title", None)
            print("TITLE:", self._console_text(title))

            content = getattr(getattr(page, "page", None), "content", "") or ""
            print(self._console_text(content[:1000]))

        print("=" * 80 + "\n")
        scraped_pages, skipped_pages = self._scraped_page_payloads(scrape_responses)
        agent_logger.info(
            "Firecrawl completed",
            mission_id=task.mission_id,
            firecrawl_success=len(scraped_pages),
            firecrawl_failed=len(scrape_responses) - len(scraped_pages),
            skipped_pages=skipped_pages,
        )
        for page in scraped_pages:
            agent_logger.info(
                "Scraped Pages",
                mission_id=task.mission_id,
                company=page.get("title") or page.get("url"),
                title=page.get("title"),
                content_length=len(str(page.get("content") or "")),
                url=page.get("url"),
            )
        agent_logger.info("Gemini Started", mission_id=task.mission_id, pages=len(scraped_pages))
        if scraped_pages:
            extraction = await self.extractor.extract(
                scraped_pages=scraped_pages,
                temperature=float(task.parameters.get("temperature", 0.0)),
                max_tokens=int(task.parameters.get("max_tokens", 4096)),
                mission_id=task.mission_id,
                shared_memory=shared_memory,
            )
        else:
            extraction = None
            agent_logger.warning(
                "Market discovery skipped company extraction",
                mission_id=task.mission_id,
                reason="no_scraped_pages_with_content",
            )
        companies = self._deduplicate_companies([self._with_metadata(company) for company in extraction.companies]) if extraction else []
        if not companies and scraped_pages:
            companies = self._fallback_companies(candidates, scraped_pages)
        if not companies:
            agent_logger.warning(
                "Market discovery extracted zero companies",
                mission_id=task.mission_id,
                pages_sent_to_llm=len(scraped_pages),
                possible_reason="LLM returned an empty companies array or no scraped pages contained supported company evidence.",
            )
        agent_logger.info(
            "Companies Extracted",
            mission_id=task.mission_id,
            count=len(companies),
            companies=[
                {
                    "company_name": company.company_name,
                    "evidence_count": len(company.evidence),
                }
                for company in companies
            ],
        )
        execution_time = time.perf_counter() - started
        output = MarketDiscoveryOutput(
            companies=companies,
            search_queries=queries,
            queries=queries,
            raw_tavily_results=raw_results,
            scraped_pages=scraped_pages,
            total_companies=len(companies),
            company_count=len(companies),
            execution_time=execution_time,
        )
        agent_logger.info(
            "Completed",
            mission_id=task.mission_id,
            total_companies=output.total_companies,
            execution_time=execution_time,
        )
        return self._response(task, output, execution_time)

    async def summarize(self, response: AgentResponse) -> str:
        total = response.output.get("total_companies", 0)
        return f"Discovered {total} candidate companies with website-backed evidence."

    async def calculate_confidence(self, response: AgentResponse) -> float:
        return 1.0

    async def cleanup(self) -> None:
        return None

    def _response(
        self,
        task: AgentTask,
        output: MarketDiscoveryOutput,
        execution_time: float,
        *,
        reused: bool = False,
    ) -> AgentResponse:
        return AgentResponse(
            success=True,
            mission_id=task.mission_id,
            task_id=task.task_id,
            agent_name=self.name,
            status=AgentState.COMPLETED,
            confidence=1.0,
            reasoning=(
                "Reused existing market discovery from shared memory."
                if reused
                else f"Discovered {output.total_companies} candidate companies from external market evidence."
            ),
            evidence=[
                evidence.model_dump(mode="json")
                for company in output.companies
                for evidence in company.evidence
            ],
            execution_time=execution_time,
            metadata={"total_companies": output.total_companies, "reused": reused},
            output=output.model_dump(mode="json"),
        )


    def _generate_queries(self, *, mission: dict[str, Any], strategy: dict[str, Any], icp: dict[str, Any]) -> list[str]:
        objective = str(mission.get("objective") or "")
        domain = str(strategy.get("domain") or mission.get("domain") or icp.get("industry") or "").strip()
        industry = str(strategy.get("industry") or icp.get("industry") or domain).strip()
        countries = self._strings(strategy.get("countries") or icp.get("countries") or icp.get("regions"))
        technologies = self._strings(strategy.get("technologies") or icp.get("technologies") or icp.get("technology_preferences"))
        triggers = self._strings(strategy.get("business_triggers") or icp.get("business_triggers"))
        personas = self._strings(strategy.get("target_personas") or icp.get("target_personas"))

        location = " ".join(countries[:2])
        tech = " ".join(technologies[:3])
        trigger = " ".join(triggers[:2])
        persona = " ".join(personas[:2])
        base_terms = " ".join(part for part in [industry, tech, location] if part).strip() or objective
        patterns = [
            f"{base_terms} companies",
            f"{base_terms} startups",
            f"{industry} {tech} enterprise software companies {location}".strip(),
            f"{trigger} {industry} companies {location}".strip(),
            f"{objective} companies",
            f"{tech} platforms for {persona}".strip(),
            f"{industry} SaaS companies {location}".strip(),
            f"{domain} technology vendors {location}".strip(),
        ]
        queries = [self._compact_spaces(query) for query in patterns if len(self._compact_spaces(query)) >= 8]
        return list(dict.fromkeys(queries))[:8] or [objective]

    def _unique_high_confidence_results(self, responses: list[SearchResponse]) -> tuple[list[SearchResult], list[dict[str, Any]]]:
        selected: dict[str, SearchResult] = {}
        skipped: list[dict[str, Any]] = []
        for response in responses:
            for result in response.results:
                normalized_url = self._normalize_url(result.url)
                if not normalized_url or result.score < 0.25:
                    skipped.append({"url": result.url, "score": result.score, "reason": "invalid_url_or_low_score"})
                    continue
                key = self._domain_key(normalized_url)
                if not key:
                    skipped.append({"url": result.url, "score": result.score, "reason": "missing_domain"})
                    continue
                normalized = result.model_copy(update={"url": normalized_url})
                current = selected.get(key)
                if current is None or normalized.score > current.score:
                    selected[key] = normalized
                else:
                    skipped.append({"url": result.url, "score": result.score, "reason": "duplicate_lower_score"})
        return list(selected.values())[:12], skipped

    def _scraped_page_payloads(self, responses: list[ScrapeResponse]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        pages: list[dict[str, Any]] = []
        skipped: list[dict[str, Any]] = []
        for response in responses:
            if response.status != "ok" or response.page is None:
                skipped.append({"url": response.url, "status": response.status, "reason": response.error or "scrape_failed"})
                continue
            payload = response.page.model_dump(mode="json")
            content_length = len(str(payload.get("content") or ""))
            if content_length:
                pages.append(payload)
            else:
                skipped.append({"url": response.url, "status": response.status, "reason": "empty_content", "content_length": 0})
        return pages, skipped

    def _raw_tavily_results(self, responses: list[SearchResponse]) -> list[dict[str, Any]]:
        return [
            result.model_dump(mode="json") | {"query": response.query}
            for response in responses
            for result in response.results
        ]

    def _with_metadata(self, company: DiscoveredCompany) -> DiscoveredCompany:
        metadata = {
            "discovered_from": "tavily",
            "scraped": True,
            "timestamp": datetime.now(UTC).isoformat(),
        } | company.metadata
        return company.model_copy(update={"metadata": metadata})

    def _deduplicate_companies(self, companies: list[DiscoveredCompany]) -> list[DiscoveredCompany]:
        selected: dict[str, DiscoveredCompany] = {}
        for company in companies:
            key = self._domain_key(self._normalize_url(company.website)) or company.company_name.strip().lower()
            if key not in selected:
                selected[key] = company
        return list(selected.values())

    def _fallback_companies(
        self,
        candidates: list[SearchResult],
        scraped_pages: list[dict[str, Any]],
    ) -> list[DiscoveredCompany]:
        pages_by_domain = {
            self._domain_key(self._normalize_url(str(page.get("url") or ""))): page
            for page in scraped_pages
            if isinstance(page, dict)
        }
        companies: list[DiscoveredCompany] = []
        for candidate in candidates:
            page = pages_by_domain.get(self._domain_key(candidate.url)) or {}
            title = str(page.get("title") or candidate.title or self._domain_key(candidate.url) or candidate.url)
            content = str(page.get("content") or candidate.content or "")
            summary = content[:500] if content else None
            companies.append(
                DiscoveredCompany(
                    company_name=title[:200],
                    website=candidate.url,
                    summary=summary,
                    evidence=[
                        {
                            "source": "search",
                            "url": candidate.url,
                            "fact": candidate.content or candidate.title or "Discovered from market search result.",
                        }
                    ],
                    metadata={
                        "discovered_from": "tavily",
                        "fallback_extraction": True,
                        "search_score": candidate.score,
                    },
                )
            )
        return self._deduplicate_companies(companies)

    def _normalize_url(self, url: str) -> str:
        parsed = urlparse(url if "://" in url else f"https://{url}")
        if not parsed.netloc:
            return ""
        return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")

    def _domain_key(self, url: str) -> str:
        host = urlparse(url).netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        return host

    def _strings(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value] if value.strip() else []
        if isinstance(value, dict):
            for key in ("name", "title", "label", "value", "technology", "trigger"):
                if value.get(key):
                    return [str(value[key])]
            return []
        if isinstance(value, list):
            items: list[str] = []
            for item in value:
                items.extend(self._strings(item))
            return items
        return [str(value)]

    def _dict(self, value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    def _compact_spaces(self, value: str) -> str:
        return " ".join(value.split())

    def _console_text(self, value: Any) -> str:
        return str(value or "").encode("ascii", errors="ignore").decode("ascii")
