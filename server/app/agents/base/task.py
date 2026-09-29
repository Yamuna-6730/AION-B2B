from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class AgentTask(BaseModel):
    mission_id: str
    task_id: str
    agent_name: str
    objective: str
    context: dict[str, Any] = Field(default_factory=dict)
    parameters: dict[str, Any] = Field(default_factory=dict)
    dependencies: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

