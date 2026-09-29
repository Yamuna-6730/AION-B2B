from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.schemas.planner import PlannerRunResponse
from app.schemas.strategy import MissionStatus
from app.services.memory_service import DevMemoryService, HindsightMemoryService
from app.services.mission_orchestrator import MissionOrchestratorService


class FakeHindsight:
    def __init__(self, *, fail: bool = False, results: list[object] | None = None) -> None: self.fail=fail; self.results=results or []; self.retains: list[dict] = []
    async def aretain(self, **kwargs):
        if self.fail: raise RuntimeError('offline')
        self.retains.append(kwargs); return SimpleNamespace(operation_id='retain-1')
    async def arecall(self, **kwargs):
        if self.fail: raise RuntimeError('offline')
        return SimpleNamespace(results=self.results)
    async def areflect(self, **kwargs):
        if self.fail: raise RuntimeError('offline')
        return SimpleNamespace(text='Hiring activity changed.')


@pytest.mark.asyncio
async def test_hindsight_memory_retain_recall_and_reflect() -> None:
    client = FakeHindsight(results=[SimpleNamespace(id='r1', text='Acme previously hired engineers.', context='hiring')])
    service = HindsightMemoryService(client=client, bank_id='aion')
    retained = await service.retain(mission_id='m1', company_id='Acme Corp', category='hiring_signal', content='Acme hired engineers.', source='aion', agent='hiring')
    recalled = await service.recall(company_id='Acme Corp', objective='Re-evaluate hiring')
    reflected = await service.reflect(company_id='Acme Corp', objective='Re-evaluate hiring', current_intelligence={'hiring': {}})
    assert retained.status == recalled.status == reflected.status == 'available'
    assert recalled.records[0]['content'] == 'Acme previously hired engineers.'
    assert reflected.reflection == 'Hiring activity changed.'
    assert client.retains[0]['metadata']['company'] == 'Acme Corp'


@pytest.mark.asyncio
async def test_hindsight_memory_handles_empty_and_failure_without_false_success() -> None:
    empty = HindsightMemoryService(client=FakeHindsight(), bank_id='aion')
    assert (await empty.recall(company_id='Acme', objective='Hiring')).status == 'empty'
    unavailable = HindsightMemoryService(client=FakeHindsight(fail=True), bank_id='aion')
    assert (await unavailable.retain(mission_id='m1', company_id='Acme', category='hiring', content='fact', source='aion')).status == 'unavailable'
    assert (await unavailable.recall(company_id='Acme', objective='Hiring')).status == 'unavailable'
    assert (await unavailable.reflect(company_id='Acme', objective='Hiring', current_intelligence={})).status == 'unavailable'


class FakeRepository:
    def __init__(self) -> None: self.missions = {key: {'id': key, 'objective': 'Analyze Acme Corp hiring and funding activity.', 'shared_memory': {}, 'metadata': {}} for key in ('m1', 'm2')}
    async def get_mission(self, mission_id): return self.missions[mission_id]
    async def update_shared_memory(self, mission_id, payload): self.missions[mission_id]['shared_memory'].update(payload); return self.missions[mission_id]
    async def update_status(self, mission_id, status): self.missions[mission_id]['status'] = status.value; return self.missions[mission_id]
    async def update_metadata(self, mission_id, metadata): self.missions[mission_id]['metadata'] = metadata; return self.missions[mission_id]


class FakeStrategy:
    async def run_strategy(self, mission_id): return {}


class FakePlanner:
    async def run_planner(self, mission_id):
        return PlannerRunResponse(mission_id=mission_id, status=MissionStatus.COMPLETED.value, execution_graph={}, planner_output={}, shared_memory={'hiring': {'hiring_signals': ['Acme is hiring engineers']}, 'funding': {'expansion_signals': ['Acme announced investment']}}, runtime=0.1, confidence=0.8)


@pytest.mark.asyncio
async def test_mission_memory_marks_first_and_returning_investigations() -> None:
    memory = DevMemoryService(); repository = FakeRepository()
    service = MissionOrchestratorService(strategy_service=FakeStrategy(), planner_service=FakePlanner(), mission_repository=repository, memory_service=memory)  # type: ignore[arg-type]
    first = await service.run('m1')
    second = await service.run('m2')
    assert first.status == second.status == MissionStatus.COMPLETED.value
    assert first.memory['first_investigation'] is True
    assert second.memory['first_investigation'] is False
    assert second.memory['relevant_memories']
