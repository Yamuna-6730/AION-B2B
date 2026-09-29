from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class MissionRunRequest(BaseModel):
    mission_id: str


class MissionCreateRequest(BaseModel):
    title: str = Field(min_length=1)
    objective: str = Field(min_length=1)
    domain: str | None = None
    mission_type: str | None = None
    created_by: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MissionOrchestratorResponse(BaseModel):
    mission_id: str
    status: str
    strategy: dict[str, Any] | None = None
    planner: dict[str, Any] | None = None
    shared_memory: dict[str, Any] = Field(default_factory=dict)
    database: dict[str, bool] = Field(default_factory=dict)
    memory: dict[str, Any] = Field(default_factory=dict)
    execution_time: float
    confidence: float
