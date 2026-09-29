from __future__ import annotations

import time
from typing import Any

from app.agents.base.base_agent import BaseAgent
from app.agents.base.enums import AgentState
from app.agents.base.response import AgentResponse
from app.agents.base.task import AgentTask
from app.core.exceptions import AionError
from app.core.logger import agent_logger
from app.llm import LLMManager, llm_manager
from app.llm.exceptions import LLMError, ParsingError
from app.schemas.strategy import MissionIntelligence


class StrategyAgentError(AionError):
    error_code = "STRATEGY_AGENT_ERROR"


class StrategyValidationError(StrategyAgentError):
    status_code = 422
    error_code = "STRATEGY_VALIDATION_ERROR"


class StrategyAgent(BaseAgent):
    """Business strategy consultant agent for mission understanding."""

    name = "strategy"
    description = "Transforms a business mission into structured mission intelligence."
    category = "intelligence"
    version = "0.1.0"
    priority = 1
    supported_inputs = ("mission", "objective")
    supported_outputs = ("mission_intelligence",)

    def __init__(self, ai_runtime: LLMManager = llm_manager) -> None:
        self.ai_runtime = ai_runtime

    async def initialize(self) -> None:
        return None

    async def validate(self, task: AgentTask) -> bool:
        if task.agent_name and task.agent_name != self.name:
            return False
        return bool(task.objective.strip())

    async def run(self, task: AgentTask) -> AgentResponse:
        started = time.perf_counter()
        if not await self.validate(task):
            raise StrategyValidationError("Strategy mission objective is required.")

        title = str(task.context.get("title") or "Untitled Mission")
        memory = task.context.get("memory", {})
        system_role = (
            "You are an Enterprise B2B Sales Strategist.\n\n"
            "Your responsibility is to understand business goals and produce structured mission intelligence.\n\n"
            "You never search the internet.\n\n"
            "You only reason.\n\n"
            "Output valid JSON only."
        )

        try:
            intelligence = await self.ai_runtime.generate_json(
                response_model=MissionIntelligence,
                system_role=system_role,
                mission=task.objective,
                memory=memory,
                agent_name=self.name,
                expected_schema=MissionIntelligence,
                template_name="strategy",
                temperature=float(task.parameters.get("temperature", 0.2)),
                top_p=float(task.parameters.get("top_p", 0.95)),
                max_tokens=int(task.parameters.get("max_tokens", 4096)),
            )
        except ParsingError:
            agent_logger.exception("Strategy Agent failed to parse LLM JSON", mission_id=task.mission_id)
            raise
        except LLMError:
            agent_logger.exception("Strategy Agent LLM runtime failed", mission_id=task.mission_id)
            raise

        intelligence = intelligence.model_copy(
            update={
                "mission_id": task.mission_id,
                "title": title,
                "objective": task.objective,
            }
        )
        execution_time = time.perf_counter() - started
        response = AgentResponse(
            success=True,
            mission_id=task.mission_id,
            task_id=task.task_id,
            agent_name=self.name,
            status=AgentState.COMPLETED,
            confidence=await self.confidence(intelligence),
            reasoning=intelligence.reasoning,
            execution_time=execution_time,
            metadata={
                "domain": intelligence.domain,
                "industry": intelligence.industry,
                "countries": intelligence.countries,
            },
            output=intelligence.model_dump(mode="json"),
        )
        agent_logger.info(
            "Strategy Agent completed",
            mission_id=task.mission_id,
            execution_time=execution_time,
            confidence=response.confidence,
        )
        return response

    async def summarize(self, response: AgentResponse) -> str:
        output = response.output
        return (
            f"{output.get('title', 'Mission')} targets {output.get('industry', 'an inferred industry')} "
            f"with confidence {response.confidence:.2f}."
        )

    async def confidence(self, intelligence: MissionIntelligence) -> float:
        return intelligence.confidence

    async def calculate_confidence(self, response: AgentResponse) -> float:
        return response.confidence

    async def cleanup(self) -> None:
        return None
