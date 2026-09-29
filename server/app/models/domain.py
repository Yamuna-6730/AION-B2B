from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class Mission(Base, TimestampMixin):
    __tablename__ = "missions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="created")
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)


class MissionEvent(Base, TimestampMixin):
    __tablename__ = "mission_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    mission_id: Mapped[str] = mapped_column(String(36), ForeignKey("missions.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Company(Base, TimestampMixin):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    mission_id: Mapped[str] = mapped_column(String(36), ForeignKey("missions.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str | None] = mapped_column(String(255))
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)


class Signal(Base, TimestampMixin):
    __tablename__ = "signals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    mission_id: Mapped[str] = mapped_column(String(36), ForeignKey("missions.id"), index=True)
    company_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("companies.id"))
    signal_type: Mapped[str] = mapped_column(String(128), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class DecisionMaker(Base, TimestampMixin):
    __tablename__ = "decision_makers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    mission_id: Mapped[str] = mapped_column(String(36), ForeignKey("missions.id"), index=True)
    company_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("companies.id"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255))
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)


class Recommendation(Base, TimestampMixin):
    __tablename__ = "recommendations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    mission_id: Mapped[str] = mapped_column(String(36), ForeignKey("missions.id"), index=True)
    company_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("companies.id"))
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[float | None] = mapped_column(Float)
    rationale: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class BusinessDNA(Base, TimestampMixin):
    __tablename__ = "business_dna"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    mission_id: Mapped[str] = mapped_column(String(36), ForeignKey("missions.id"), index=True)
    company_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("companies.id"))
    profile: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class AgentExecution(Base, TimestampMixin):
    __tablename__ = "agent_executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    mission_id: Mapped[str] = mapped_column(String(36), ForeignKey("missions.id"), index=True)
    agent_name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    input_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    output_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class KnowledgeNode(Base, TimestampMixin):
    __tablename__ = "knowledge_nodes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    mission_id: Mapped[str] = mapped_column(String(36), ForeignKey("missions.id"), index=True)
    node_type: Mapped[str] = mapped_column(String(128), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    properties: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class KnowledgeEdge(Base, TimestampMixin):
    __tablename__ = "knowledge_edges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    mission_id: Mapped[str] = mapped_column(String(36), ForeignKey("missions.id"), index=True)
    source_node_id: Mapped[str] = mapped_column(String(36), ForeignKey("knowledge_nodes.id"))
    target_node_id: Mapped[str] = mapped_column(String(36), ForeignKey("knowledge_nodes.id"))
    relationship_type: Mapped[str] = mapped_column(String(128), nullable=False)
    properties: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class MissionReport(Base, TimestampMixin):
    __tablename__ = "mission_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    mission_id: Mapped[str] = mapped_column(String(36), ForeignKey("missions.id"), index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(64), default="draft")

