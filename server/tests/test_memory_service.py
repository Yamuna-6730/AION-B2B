from __future__ import annotations

import pytest

from app.services.memory_service import DevMemoryService


@pytest.mark.asyncio
async def test_dev_memory_service_stores_and_retrieves_history() -> None:
    service = DevMemoryService()

    await service.store(
        mission_id="mission-1",
        company_id="siemens",
        event_type="signal_update",
        payload={"headline": "AI expansion", "confidence": 0.92},
        source="aion",
    )

    await service.store(
        mission_id="mission-1",
        company_id="siemens",
        event_type="recommendation_update",
        payload={"recommendation": "Increase priority"},
        source="aion",
    )

    history = await service.get_company_history("siemens", mission_id="mission-1")
    assert len(history) == 2
    assert history[0]["event_type"] in {"signal_update", "recommendation_update"}

    search_results = await service.search("mission-1", "expansion")
    assert search_results
    assert any(item["company_id"] == "siemens" for item in search_results)

    context = await service.get_relevant_context("mission-1", company_id="siemens", query="AI expansion")
    assert context["company_id"] == "siemens"
    assert context["history"]
