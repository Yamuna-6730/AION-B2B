from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PlannerSchemaBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class PlannerRunRequest(PlannerSchemaBase):
    mission_id: UUID


class AgentCapability(PlannerSchemaBase):
    name: str
    category: str
    description: str = ""
    parallel_capable: bool = True
    dependencies: list[str] = Field(default_factory=list)
    priority: int = 3


class GraphNodeData(PlannerSchemaBase):
    label: str
    agent_name: str
    priority: int = 3
    parallel: bool = True
    status: str = "PENDING"
    estimated_duration: float = 1.0
    critical: bool = False
    max_retries: int = 2
    retry_delay: float = 0.0
    timeout: float | None = None


class GraphPosition(PlannerSchemaBase):
    x: float = 0
    y: float = 0


class GraphNode(PlannerSchemaBase):
    id: str
    type: Literal["agent"] = "agent"
    position: GraphPosition = Field(default_factory=GraphPosition)
    data: GraphNodeData


class GraphEdge(PlannerSchemaBase):
    id: str
    source: str
    target: str
    type: str = "smoothstep"


class ExecutionBlueprint(PlannerSchemaBase):
    mission_id: str
    planner_version: str = "0.1.0"
    selected_agents: list[str] = Field(default_factory=list)
    execution_order: list[str] = Field(default_factory=list)
    parallel_groups: list[list[str]] = Field(default_factory=list)
    planner_reasoning: str = ""
    estimated_duration: float = 0.0
    estimated_cost: float = 0.0
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    execution_constraints: dict[str, Any] = Field(default_factory=dict)
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)


class ExecutionContext(PlannerSchemaBase):
    mission: dict[str, Any]
    strategy: dict[str, Any] = Field(default_factory=dict)
    icp: dict[str, Any] = Field(default_factory=dict)
    blueprint: dict[str, Any] = Field(default_factory=dict)
    shared_memory: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PlannerRunResponse(PlannerSchemaBase):
    mission_id: str
    status: str
    execution_graph: dict[str, Any]
    planner_output: dict[str, Any]
    shared_memory: dict[str, Any] = Field(default_factory=dict)
    recommendations: dict[str, Any] = Field(default_factory=dict)
    runtime: float = 0.0
    confidence: float = 0.0
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
