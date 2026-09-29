from __future__ import annotations

import asyncio
from typing import Any

from app.core.exceptions import AionError
from app.core.logger import app_logger
from app.schemas.business_dna import BusinessDNAProfile
from app.supabase.client import SupabaseClient


class BusinessDNAPersistenceError(AionError):
    error_code = "BUSINESS_DNA_PERSISTENCE_ERROR"


class BusinessDNARepository:
    """Persistence for Business DNA company intelligence profiles."""

    def __init__(self, client: Any | None = None) -> None:
        self.client = client or SupabaseClient.get_client()
        self.table_name = "business_dna_results"

    async def save_results(self, mission_id: str, profiles: list[BusinessDNAProfile]) -> list[dict[str, Any]]:
        if not profiles:
            return []
        payload = [self._row(mission_id, profile) for profile in profiles]
        result = await asyncio.to_thread(lambda: self.client.table(self.table_name).insert(payload).execute())
        data = getattr(result, "data", result)
        if not isinstance(data, list):
            raise BusinessDNAPersistenceError("Business DNA upsert returned an unexpected response.")

        verified = await self.list_by_mission(mission_id)
        app_logger.info(
            "Business DNA persistence verified",
            mission_id=mission_id,
            inserted=len(data),
            verified=len(verified),
            table=self.table_name,
        )
        if len(verified) < len(profiles):
            raise BusinessDNAPersistenceError(
                "Business DNA upsert verification failed.",
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

    def _row(self, mission_id: str, profile: BusinessDNAProfile) -> dict[str, Any]:
        return {
            "mission_id": mission_id,
            "company_name": profile.company_name,
            "website": profile.website,
            "industry": profile.industry,
            "company_type": profile.company_type,
            "country": profile.country,
            "business_summary": profile.business_summary,
            "estimated_company_size": profile.estimated_company_size,
            "estimated_ai_maturity": profile.estimated_ai_maturity,
            "technology_signals": profile.technology_signals,
            "digital_transformation_signals": profile.digital_transformation_signals,
            "buying_personas": profile.buying_personas,
            "use_cases": profile.use_cases,
            "strengths": profile.strengths,
            "risks": profile.risks,
            "evidence": profile.evidence,
            "confidence": profile.confidence,
            "reasoning": profile.reasoning,
        }
