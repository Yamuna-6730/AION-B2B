from __future__ import annotations

import asyncio
from typing import Any

from app.core.exceptions import AionError
from app.core.logger import app_logger
from app.schemas.recommendations import ScoredCompany
from app.supabase.client import SupabaseClient


class RecommendationPersistenceError(AionError):
    error_code = "RECOMMENDATION_PERSISTENCE_ERROR"


class RecommendationRepository:
    """Persistence for Recommendation scored and ranked companies."""

    def __init__(self, client: Any | None = None) -> None:
        self.client = client or SupabaseClient.get_client()
        self.table_name = "recommendation_results"

    async def save_results(self, mission_id: str, companies: list[ScoredCompany]) -> list[dict[str, Any]]:
        if not companies:
            return []
        payload = [self._row(mission_id, company) for company in companies]
        result = await asyncio.to_thread(lambda: self.client.table(self.table_name).insert(payload).execute())
        data = getattr(result, "data", result)
        if not isinstance(data, list):
            raise RecommendationPersistenceError("Recommendation upsert returned an unexpected response.")

        verified = await self.list_by_mission(mission_id)
        app_logger.info(
            "Recommendation persistence verified",
            mission_id=mission_id,
            inserted=len(data),
            verified=len(verified),
            table=self.table_name,
        )
        if len(verified) < len(companies):
            raise RecommendationPersistenceError(
                "Recommendation upsert verification failed.",
                {"mission_id": mission_id, "inserted": len(data), "verified": len(verified), "table": self.table_name},
            )
        return verified

    async def list_by_mission(self, mission_id: str) -> list[dict[str, Any]]:
        result = await asyncio.to_thread(
            lambda: self.client.table(self.table_name).select("*").eq("mission_id", mission_id).execute()
        )
        data = getattr(result, "data", result)
        return data if isinstance(data, list) else []

    async def delete_by_mission(self, mission_id: str) -> None:
        await asyncio.to_thread(
            lambda: self.client.table(self.table_name).delete().eq("mission_id", mission_id).execute()
        )

    def _row(self, mission_id: str, company: ScoredCompany) -> dict[str, Any]:
        return {
            "mission_id": mission_id,
            "company_name": company.company_name,
            "website": company.website,
            "priority_score": company.priority_score,
            "priority": company.priority,
            "rank": company.rank,
            "confidence": company.confidence,
            "why_selected": company.why_selected,
            "strengths": company.strengths,
            "risks": company.risks,
            "recommended_personas": company.recommended_personas,
            "recommended_use_cases": company.recommended_use_cases,
            "next_action": company.next_action,
            "scoring_breakdown": company.scoring_breakdown,
        }
