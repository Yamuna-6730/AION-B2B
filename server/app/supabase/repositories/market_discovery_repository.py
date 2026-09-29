from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import urlparse

from app.core.exceptions import AionError
from app.core.logger import app_logger
from app.schemas.market_discovery import DiscoveredCompany
from app.supabase.client import SupabaseClient


class MarketDiscoveryPersistenceError(AionError):
    error_code = "MARKET_DISCOVERY_PERSISTENCE_ERROR"


class MarketDiscoveryRepository:
    """Persistence for market discovery company evidence."""

    def __init__(self, client: Any | None = None) -> None:
        self.client = client or SupabaseClient.get_client()
        self.table_name = "market_discovery_results"

    async def save_results(self, mission_id: str, companies: list[DiscoveredCompany]) -> list[dict[str, Any]]:
        if not companies:
            return []
        payload = [self._row(mission_id, company) for company in companies]
        try:
            result = await asyncio.to_thread(lambda: self.client.table(self.table_name).insert(payload).execute())
        except Exception as exc:
            if "column" not in str(exc).lower():
                raise
            payload = [self._supported_row(row) for row in payload]
            result = await asyncio.to_thread(lambda: self.client.table(self.table_name).insert(payload).execute())
        data = getattr(result, "data", result)
        if not isinstance(data, list):
            raise MarketDiscoveryPersistenceError("Market discovery upsert returned an unexpected response.")

        # Verify rows exist via SELECT COUNT(*) / select(*)
        verified = await self.list_by_mission(mission_id)
        app_logger.info(
            "Supabase Insert Count",
            mission_id=mission_id,
            inserted=len(data),
            table=self.table_name,
        )
        app_logger.info(
            "Supabase Verification Count",
            mission_id=mission_id,
            verified=len(verified),
            table=self.table_name,
        )
        if len(verified) < len(companies):
            raise MarketDiscoveryPersistenceError(
                "Market discovery upsert verification failed.",
                {"mission_id": mission_id, "inserted": len(data), "verified": len(verified), "table": self.table_name},
            )
        return verified

    async def list_by_mission(self, mission_id: str) -> list[dict[str, Any]]:
        result = await asyncio.to_thread(
            lambda: self.client.table(self.table_name).select("*").eq("mission_id", mission_id).execute()
        )
        data = getattr(result, "data", result)
        return data if isinstance(data, list) else []

    def _row(self, mission_id: str, company: DiscoveredCompany) -> dict[str, Any]:
        evidence = [item.model_dump(mode="json") for item in company.evidence]
        return {
            "mission_id": mission_id,
            "company_name": company.company_name,
            "website": company.website,
            "summary": company.summary,
            "industry": company.industry,
            "country": company.country,
            "products": company.products,
            "use_cases": company.use_cases,
            "technologies": company.technologies,
            "customer_logos": company.customer_logos,
            "evidence": evidence,
            "metadata": company.metadata,
        }

    def _supported_row(self, row: dict[str, Any]) -> dict[str, Any]:
        supported = {"mission_id", "company_name", "website", "summary", "industry", "country", "products", "use_cases", "technologies", "customer_logos", "evidence", "metadata"}
        return {key: value for key, value in row.items() if key in supported}

    def _domain(self, url: str) -> str | None:
        parsed = urlparse(url if "://" in url else f"https://{url}")
        return parsed.netloc or None

    def _markdown(self, company: DiscoveredCompany) -> str | None:
        parts = [
            company.summary,
            f"Industry: {company.industry}" if company.industry else None,
            f"Country: {company.country}" if company.country else None,
            f"Products: {', '.join(company.products)}" if company.products else None,
            f"Services: {', '.join(company.services)}" if company.services else None,
            f"Technologies: {', '.join(company.technologies)}" if company.technologies else None,
            f"Use cases: {', '.join(company.use_cases)}" if company.use_cases else None,
        ]
        markdown = "\n".join(part for part in parts if part)
        return markdown or None

    def _search_score(self, company: DiscoveredCompany) -> float | None:
        score = company.metadata.get("search_score")
        return float(score) if isinstance(score, int | float) else None
