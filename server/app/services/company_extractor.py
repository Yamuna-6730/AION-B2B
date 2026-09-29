from __future__ import annotations

import json
from typing import Any

from app.core.logger import app_logger
from app.llm import LLMManager, llm_manager
from app.schemas.market_discovery import DiscoveredCompany, CompanyExtractionResult
from app.supabase.repositories.market_discovery_repository import MarketDiscoveryRepository


class CompanyExtractor:
    """Evidence-bound structured extraction from scraped website content.

    This extractor sends one scraped page per LLM prompt, parses a single
    `DiscoveredCompany`, upserts immediately to Supabase (when a mission_id is
    provided), and appends the JSON company into the provided shared memory
    structure.
    """

    def __init__(self, ai_runtime: LLMManager = llm_manager) -> None:
        self.ai_runtime = ai_runtime

    async def extract(
        self,
        *,
        scraped_pages: list[dict[str, Any]],
        temperature: float = 0.0,
        max_tokens: int = 4096,
        mission_id: str | None = None,
        shared_memory: dict[str, Any] | None = None,
    ) -> CompanyExtractionResult:
        if not scraped_pages:
            return CompanyExtractionResult()

        system_role = (
            "You extract structured company facts from scraped official website content.\n\n"
            "Use only supplied scraped content.\n"
            "Do not guess.\n"
            "Do not rank, recommend, or filter companies.\n"
            "If a field is not supported by evidence, use null, or an empty list.\n"
            "Return valid JSON only."
        )

        repo = MarketDiscoveryRepository()
        companies: list[DiscoveredCompany] = []

        for idx, page in enumerate(scraped_pages, start=1):
            url = page.get("url") if isinstance(page, dict) else None
            app_logger.info("Processing scraped page", index=idx, url=url)

            try:
                app_logger.info("Gemini Started", page_index=idx, url=url)

                response = await self.ai_runtime.generate(
                    system_role=system_role,
                    mission="",
                    memory=page,
                    agent_name="market",
                    expected_schema=DiscoveredCompany,
                    template_name="market_discovery",
                    temperature=temperature,
                    top_p=0.95,
                    max_tokens=max_tokens,
                    use_cache=False,
                )

                app_logger.info("Gemini Raw Response", page_index=idx, raw=response.output)

                raw_output = getattr(response, "output", None)

                # First try to parse as a full CompanyExtractionResult (multiple companies)
                try:
                    extraction_result = self.ai_runtime.parser.parse_json(raw_output, CompanyExtractionResult)
                    parsed_companies = extraction_result.companies
                except ValueError:
                    # propagate malformed JSON to caller/tests
                    raise
                except Exception:
                    # Fallback: try parsing a single DiscoveredCompany
                    try:
                        company = self.ai_runtime.parser.parse_json(raw_output, DiscoveredCompany)
                        parsed_companies = [company]
                    except ValueError:
                        # propagate malformed JSON
                        raise
                    except Exception as exc:
                        app_logger.error("Company extraction parse failed", page_index=idx, url=url, error=str(exc))
                        # continue to next page
                        continue

                # Upsert immediately if mission_id provided
                if mission_id and parsed_companies:
                    try:
                        await repo.save_results(mission_id, parsed_companies)
                        app_logger.info("Supabase Insert Success", mission_id=mission_id, inserted=len(parsed_companies))
                    except Exception as exc:
                        app_logger.error("Supabase Insert Failed", mission_id=mission_id, error=str(exc))

                # Append to shared memory if provided
                if shared_memory is not None:
                    md = shared_memory.setdefault("market_discovery", {})
                    for comp in parsed_companies:
                        md.setdefault("companies", []).append(comp.model_dump(mode="json"))

                for comp in parsed_companies:
                    companies.append(comp)
                    app_logger.info("Company Extracted", website=comp.website, company_name=comp.company_name)

            except Exception as exc:
                # Propagate JSON parse errors to allow callers/tests to handle malformed JSON
                if isinstance(exc, ValueError):
                    raise

                raw = None
                try:
                    raw = getattr(response, "output", None)
                except Exception:
                    raw = None

                app_logger.error(
                    "Company extraction failed for page",
                    url=url,
                    reason=str(exc),
                    raw_response=raw,
                )
                # continue processing remaining pages
                continue

        return CompanyExtractionResult(companies=companies)
