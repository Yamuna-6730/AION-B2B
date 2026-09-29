from datetime import datetime
from typing import Any, TypeAlias

from pydantic import BaseModel, ConfigDict, Field


class SchemaBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class EntityBase(SchemaBase):
    metadata: dict[str, Any] = Field(default_factory=dict, alias="metadata_")


class MissionCreate(EntityBase):
    name: str
    objective: str


class MissionRead(MissionCreate):
    id: str
    status: str
    created_at: datetime
    updated_at: datetime


class MissionUpdate(EntityBase):
    name: str | None = None
    objective: str | None = None
    status: str | None = None


class MissionResponse(SchemaBase):
    data: MissionRead


class MissionEventCreate(SchemaBase):
    mission_id: str
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)


class MissionEventRead(MissionEventCreate):
    id: str
    created_at: datetime
    updated_at: datetime


class MissionEventUpdate(SchemaBase):
    event_type: str | None = None
    payload: dict[str, Any] | None = None


class MissionEventResponse(SchemaBase):
    data: MissionEventRead


class CompanyCreate(EntityBase):
    mission_id: str
    name: str
    domain: str | None = None


class CompanyRead(CompanyCreate):
    id: str
    created_at: datetime
    updated_at: datetime


class CompanyUpdate(EntityBase):
    name: str | None = None
    domain: str | None = None


class CompanyResponse(SchemaBase):
    data: CompanyRead


class SignalCreate(SchemaBase):
    mission_id: str
    company_id: str | None = None
    signal_type: str
    confidence: float | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)


class SignalRead(SignalCreate):
    id: str
    created_at: datetime
    updated_at: datetime


class SignalUpdate(SchemaBase):
    signal_type: str | None = None
    confidence: float | None = None
    evidence: dict[str, Any] | None = None


class SignalResponse(SchemaBase):
    data: SignalRead


class DecisionMakerCreate(EntityBase):
    mission_id: str
    company_id: str | None = None
    name: str
    title: str | None = None


class DecisionMakerRead(DecisionMakerCreate):
    id: str
    created_at: datetime
    updated_at: datetime


class DecisionMakerUpdate(EntityBase):
    name: str | None = None
    title: str | None = None


class DecisionMakerResponse(SchemaBase):
    data: DecisionMakerRead


class RecommendationCreate(SchemaBase):
    mission_id: str
    company_id: str | None = None
    summary: str
    score: float | None = None
    rationale: dict[str, Any] = Field(default_factory=dict)


class RecommendationRead(RecommendationCreate):
    id: str
    created_at: datetime
    updated_at: datetime


class RecommendationUpdate(SchemaBase):
    summary: str | None = None
    score: float | None = None
    rationale: dict[str, Any] | None = None


class RecommendationResponse(SchemaBase):
    data: RecommendationRead


class BusinessDNACreate(SchemaBase):
    mission_id: str
    company_id: str | None = None
    profile: dict[str, Any] = Field(default_factory=dict)


class BusinessDNARead(BusinessDNACreate):
    id: str
    created_at: datetime
    updated_at: datetime


class BusinessDNAUpdate(SchemaBase):
    profile: dict[str, Any] | None = None


class BusinessDNAResponse(SchemaBase):
    data: BusinessDNARead


class AgentExecutionCreate(SchemaBase):
    mission_id: str
    agent_name: str
    status: str
    input_payload: dict[str, Any] = Field(default_factory=dict)
    output_payload: dict[str, Any] = Field(default_factory=dict)


class AgentExecutionRead(AgentExecutionCreate):
    id: str
    created_at: datetime
    updated_at: datetime


class AgentExecutionUpdate(SchemaBase):
    status: str | None = None
    input_payload: dict[str, Any] | None = None
    output_payload: dict[str, Any] | None = None


class AgentExecutionResponse(SchemaBase):
    data: AgentExecutionRead


class KnowledgeNodeCreate(SchemaBase):
    mission_id: str
    node_type: str
    label: str
    properties: dict[str, Any] = Field(default_factory=dict)


class KnowledgeNodeRead(KnowledgeNodeCreate):
    id: str
    created_at: datetime
    updated_at: datetime


class KnowledgeNodeUpdate(SchemaBase):
    node_type: str | None = None
    label: str | None = None
    properties: dict[str, Any] | None = None


class KnowledgeNodeResponse(SchemaBase):
    data: KnowledgeNodeRead


class KnowledgeEdgeCreate(SchemaBase):
    mission_id: str
    source_node_id: str
    target_node_id: str
    relationship_type: str
    properties: dict[str, Any] = Field(default_factory=dict)


class KnowledgeEdgeRead(KnowledgeEdgeCreate):
    id: str
    created_at: datetime
    updated_at: datetime


class KnowledgeEdgeUpdate(SchemaBase):
    relationship_type: str | None = None
    properties: dict[str, Any] | None = None


class KnowledgeEdgeResponse(SchemaBase):
    data: KnowledgeEdgeRead


class MissionReportCreate(SchemaBase):
    mission_id: str
    title: str
    content: dict[str, Any] = Field(default_factory=dict)
    status: str = "draft"


class MissionReportRead(MissionReportCreate):
    id: str
    created_at: datetime
    updated_at: datetime


class MissionReportUpdate(SchemaBase):
    title: str | None = None
    content: dict[str, Any] | None = None
    status: str | None = None


class MissionReportResponse(SchemaBase):
    data: MissionReportRead


MissionListResponse: TypeAlias = list[MissionRead]
CompanyListResponse: TypeAlias = list[CompanyRead]
SignalListResponse: TypeAlias = list[SignalRead]
RecommendationListResponse: TypeAlias = list[RecommendationRead]

