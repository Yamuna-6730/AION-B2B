from typing import Any

from pydantic import BaseModel, Field

from app.agents.base.enums import AgentState


class AgentResponse(BaseModel):
    success: bool
    mission_id: str
    task_id: str
    agent_name: str
    status: AgentState
    confidence: float
    reasoning: str
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    execution_time: float
    metadata: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)

