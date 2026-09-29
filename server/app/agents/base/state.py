from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.agents.base.enums import AgentState


@dataclass(slots=True)
class AgentRuntimeState:
    status: AgentState = AgentState.CREATED
    last_updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)

