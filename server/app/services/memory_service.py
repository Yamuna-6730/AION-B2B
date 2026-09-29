from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

from app.core.config import settings
from app.core.logger import app_logger


@dataclass
class MemoryRecord:
    id: str
    mission_id: str
    company_id: str
    event_type: str
    payload: dict[str, Any]
    source: str
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class MemoryResult:
    status: str
    records: list[dict[str, Any]] = field(default_factory=list)
    reflection: str | None = None
    error: str | None = None


class MemoryService(Protocol):
    async def retain(self, *, mission_id: str, company_id: str, category: str, content: str, source: str, agent: str | None = None) -> MemoryResult: ...
    async def recall(self, *, company_id: str, objective: str) -> MemoryResult: ...
    async def reflect(self, *, company_id: str, objective: str, current_intelligence: dict[str, Any]) -> MemoryResult: ...


class DevMemoryService:
    """In-memory test implementation with the same retain/recall/reflect contract."""
    def __init__(self) -> None: self._records: list[MemoryRecord] = []
    async def retain(self, *, mission_id: str, company_id: str, category: str, content: str, source: str, agent: str | None = None) -> MemoryResult:
        record = MemoryRecord(id=f"{mission_id}:{company_id}:{category}:{len(self._records)}", mission_id=mission_id, company_id=company_id, event_type=category, payload={"content": content, "agent": agent}, source=source)
        self._records.append(record)
        return MemoryResult(status="available", records=[self._as_dict(record)])
    async def recall(self, *, company_id: str, objective: str) -> MemoryResult:
        matches = [self._as_dict(record) for record in self._records if record.company_id.lower() == company_id.lower()]
        return MemoryResult(status="available" if matches else "empty", records=matches)
    async def reflect(self, *, company_id: str, objective: str, current_intelligence: dict[str, Any]) -> MemoryResult:
        history = await self.recall(company_id=company_id, objective=objective)
        return MemoryResult(status=history.status, records=history.records, reflection=None)
    async def store(self, *, mission_id: str, company_id: str, event_type: str, payload: dict[str, Any], source: str = "aion") -> MemoryRecord:
        result = await self.retain(mission_id=mission_id, company_id=company_id, category=event_type, content=json.dumps(payload, default=str), source=source)
        return self._records[-1]
    async def search(self, mission_id: str, query: str) -> list[dict[str, Any]]:
        query_text = query.lower(); return [self._as_dict(record) for record in self._records if record.mission_id == mission_id and query_text in json.dumps(record.payload).lower()]
    async def get_company_history(self, company_id: str, *, mission_id: str | None = None) -> list[dict[str, Any]]:
        return [self._as_dict(record) for record in self._records if record.company_id == company_id and (mission_id is None or record.mission_id == mission_id)]
    async def get_relevant_context(self, mission_id: str, *, company_id: str | None = None, query: str | None = None) -> dict[str, Any]:
        history = await self.get_company_history(company_id or "", mission_id=mission_id) if company_id else []
        return {"mission_id": mission_id, "company_id": company_id, "query": query, "history": history}
    def _as_dict(self, record: MemoryRecord) -> dict[str, Any]: return {"id": record.id, "mission_id": record.mission_id, "company_id": record.company_id, "category": record.event_type, "event_type": record.event_type, "content": record.payload.get("content", ""), "agent": record.payload.get("agent"), "source": record.source, "created_at": record.created_at}


class HindsightMemoryService:
    def __init__(self, client: Any | None = None, *, base_url: str | None = None, api_key: str | None = None, bank_id: str | None = None) -> None:
        self.bank_id = bank_id or settings.hindsight_bank_id
        if client is not None: self.client = client
        elif base_url or settings.hindsight_api_url:
            from hindsight_client import Hindsight
            self.client = Hindsight(base_url=base_url or settings.hindsight_api_url or "", api_key=api_key or settings.hindsight_api_key, timeout=float(settings.request_timeout_seconds))
        else: self.client = None
    async def retain(self, *, mission_id: str, company_id: str, category: str, content: str, source: str, agent: str | None = None) -> MemoryResult:
        if not self.client or not self.bank_id: return MemoryResult(status="unavailable", error="Memory is not configured.")
        try:
            response = await self.client.aretain(bank_id=self.bank_id, content=content, context=f"AION {category} for {company_id}", metadata={"mission_id": mission_id, "company": company_id, "agent": agent or "", "source": source}, tags=["aion", category, company_id.lower().replace(" ", "-")])
            return MemoryResult(status="available", records=[{"id": str(getattr(response, "operation_id", "")), "company_id": company_id, "category": category, "content": content, "source": source, "agent": agent}])
        except Exception as exc:
            app_logger.warning("Hindsight retain unavailable", error_type=type(exc).__name__)
            return MemoryResult(status="unavailable", error="Hindsight retain failed.")
    async def recall(self, *, company_id: str, objective: str) -> MemoryResult:
        if not self.client or not self.bank_id: return MemoryResult(status="unavailable", error="Memory is not configured.")
        query = f"Previous intelligence about {company_id}: hiring, funding, expansion, business signals, and recommendations relevant to {objective}."
        try:
            response = await self.client.arecall(bank_id=self.bank_id, query=query, tags=[company_id.lower().replace(" ", "-")], tags_match="any")
            records = [{"id": str(getattr(item, "id", "")), "content": str(getattr(item, "text", "")), "context": str(getattr(item, "context", ""))} for item in (getattr(response, "results", None) or []) if getattr(item, "text", None)]
            return MemoryResult(status="available" if records else "empty", records=records)
        except Exception as exc:
            app_logger.warning("Hindsight recall unavailable", error_type=type(exc).__name__)
            return MemoryResult(status="unavailable", error="Hindsight recall failed.")
    async def reflect(self, *, company_id: str, objective: str, current_intelligence: dict[str, Any]) -> MemoryResult:
        if not self.client or not self.bank_id: return MemoryResult(status="unavailable", error="Memory is not configured.")
        query = f"What changed for {company_id} relative to previous intelligence? Objective: {objective}. Current intelligence: {json.dumps(current_intelligence, default=str)[:4000]}"
        try:
            response = await self.client.areflect(bank_id=self.bank_id, query=query, tags=[company_id.lower().replace(" ", "-")], tags_match="any")
            return MemoryResult(status="available", reflection=str(getattr(response, "text", "")) or None)
        except Exception as exc:
            app_logger.warning("Hindsight reflect unavailable", error_type=type(exc).__name__)
            return MemoryResult(status="unavailable", error="Hindsight reflect failed.")
    async def aclose(self) -> None:
        close = getattr(self.client, "aclose", None)
        if close is not None:
            await close()
