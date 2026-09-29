from __future__ import annotations
import time
from typing import Any
from app.agents.base.base_agent import BaseAgent
from app.agents.base.enums import AgentState
from app.agents.base.response import AgentResponse
from app.agents.base.task import AgentTask
from app.schemas.intelligence import FundingIntelligence, HiringIntelligence
from app.services.firecrawl_service import FirecrawlService
from app.services.tavily_service import TavilyService

class _ResearchAgent(BaseAgent):
    category = 'discovery'; version = '0.1.0'; priority = 2; supported_inputs = ('mission', 'company', 'shared_memory'); parallel_capable = True
    def __init__(self, *, tavily_service: TavilyService | None = None, firecrawl_service: FirecrawlService | None = None) -> None: self.tavily_service=tavily_service or TavilyService(); self.firecrawl_service=firecrawl_service or FirecrawlService()
    async def initialize(self) -> None: return None
    async def validate(self, task: AgentTask) -> bool: return bool(task.mission_id and task.objective.strip())
    async def summarize(self, response: AgentResponse) -> str: return response.reasoning
    async def calculate_confidence(self, response: AgentResponse) -> float: return response.confidence
    async def cleanup(self) -> None: return None
    def _company(self, task: AgentTask) -> str: return str(task.context.get('company') or task.context.get('mission', {}).get('company') or task.context.get('mission', {}).get('domain') or '').strip() or None
    def _sources(self, response: Any) -> list[Any]:
        results = getattr(response, 'results', []) if getattr(response, 'status', None) == 'ok' else []
        return [result for result in results if hasattr(result, 'title') and hasattr(result, 'url') and hasattr(result, 'content')]

class HiringIntelligenceAgent(_ResearchAgent):
    name='hiring'; description='Researches current hiring activity, career signals, roles, locations, and technology demand.'; supported_outputs=('hiring_intelligence',)
    async def run(self, task: AgentTask) -> AgentResponse:
        started=time.perf_counter(); company=self._company(task); query=f'{company or task.objective} hiring careers open roles technology'; response=await self.tavily_service.search(query); sources=self._sources(response)
        pages=await self.firecrawl_service.scrape_multiple([r.url for r in sources[:3]]) if sources else []
        text=' '.join([r.content for r in sources]+[p.page.content for p in pages if p.page and p.status=='ok']).lower()
        signals=[r.title for r in sources if any(word in r.title.lower() for word in ('hiring','career','job','role'))]
        output=HiringIntelligence(company=company, hiring_signals=signals, technology_signals=[word for word in ('python','ai','cloud','data') if word in text], sources=sources, confidence=.6 if sources else 0.0)
        return AgentResponse(success=True,mission_id=task.mission_id,task_id=task.task_id,agent_name=self.name,status=AgentState.COMPLETED,confidence=output.confidence,reasoning='Hiring intelligence collected from available source evidence.',evidence=[s.model_dump() for s in sources],execution_time=time.perf_counter()-started,output=output.model_dump(mode='json'))

class FundingIntelligenceAgent(_ResearchAgent):
    name='funding'; description='Researches verified funding, investors, investment activity, and related expansion signals.'; supported_outputs=('funding_intelligence',)
    async def run(self, task: AgentTask) -> AgentResponse:
        started=time.perf_counter(); company=self._company(task); query=f'{company or task.objective} funding investors investment announcement'; response=await self.tavily_service.search(query); sources=self._sources(response)
        pages=await self.firecrawl_service.scrape_multiple([r.url for r in sources[:3]]) if sources else []
        text=' '.join([r.content for r in sources]+[p.page.content for p in pages if p.page and p.status=='ok']).lower()
        output=FundingIntelligence(company=company, expansion_signals=[r.title for r in sources if any(word in r.title.lower() for word in ('funding','investment','series','raised'))], sources=sources, confidence=.6 if sources else 0.0)
        return AgentResponse(success=True,mission_id=task.mission_id,task_id=task.task_id,agent_name=self.name,status=AgentState.COMPLETED,confidence=output.confidence,reasoning='Funding intelligence collected from available source evidence.',evidence=[s.model_dump() for s in sources],execution_time=time.perf_counter()-started,output=output.model_dump(mode='json'))
