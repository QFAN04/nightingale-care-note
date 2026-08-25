from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.identity import Patient, User, UserRole
from app.models.timeline import Entry, enum_column


class FactType(str, enum.Enum):
    SYMPTOM = "symptom"
    MEDICATION = "medication"
    ALLERGY = "allergy"
    DIAGNOSIS = "diagnosis"
    VITAL = "vital"
    PLAN = "plan"


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PersistenceType(str, enum.Enum):
    TRANSIENT = "transient"
    PERSISTENT = "persistent"


class ReviewStatus(str, enum.Enum):
    SUGGESTED = "suggested"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class HighlightCategory(str, enum.Enum):
    CRITICAL = "critical"
    RECENT_CHANGE = "recent_change"
    OPEN_ACTION = "open_action"
    CONFLICT = "conflict"


class HighlightStatus(str, enum.Enum):
    SUGGESTED = "suggested"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class TaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskStatus(str, enum.Enum):
    OPEN = "open"
    COMPLETED = "completed"


class ConflictType(str, enum.Enum):
    MEDICATION_DOSE = "medication_dose"


class ConflictStatus(str, enum.Enum):
    DETECTED = "detected"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class ClinicalFact(Base):
    __tablename__ = "clinical_facts"
    __table_args__ = (
        CheckConstraint(
            "extraction_confidence >= 0 AND extraction_confidence <= 1",
            name="ck_clinical_facts_confidence_range",
        ),
        CheckConstraint(
            "(source_start IS NULL AND source_end IS NULL) OR "
            "(source_start >= 0 AND source_end > source_start)",
            name="ck_clinical_facts_source_span",
        ),
        Index("ix_clinical_facts_patient_id", "patient_id"),
        Index("ix_clinical_facts_entry_id", "entry_id"),
        Index("ix_clinical_facts_reviewed_by_id", "reviewed_by_id"),
        Index("ix_clinical_facts_patient_entity", "patient_id", "entity_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False
    )
    entry_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("entries.id", ondelete="RESTRICT"), nullable=False
    )
    fact_type: Mapped[FactType] = mapped_column(
        enum_column(FactType, "fact_type"), nullable=False
    )
    entity_name: Mapped[str] = mapped_column(Text, nullable=False)
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_number: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_level: Mapped[RiskLevel] = mapped_column(
        enum_column(RiskLevel, "risk_level"), nullable=False
    )
    persistence_type: Mapped[PersistenceType] = mapped_column(
        enum_column(PersistenceType, "persistence_type"), nullable=False
    )
    source_quote: Mapped[str] = mapped_column(Text, nullable=False)
    source_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extraction_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    review_status: Mapped[ReviewStatus] = mapped_column(
        enum_column(ReviewStatus, "fact_review_status"),
        nullable=False,
        default=ReviewStatus.SUGGESTED,
        server_default=ReviewStatus.SUGGESTED.value,
    )
    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    patient: Mapped[Patient] = relationship()
    entry: Mapped[Entry] = relationship()
    reviewed_by: Mapped[User | None] = relationship()
    highlights: Mapped[list[Highlight]] = relationship(back_populates="clinical_fact")


class Highlight(Base):
    __tablename__ = "highlights"
    __table_args__ = (
        CheckConstraint("learned_score >= 0 AND learned_score <= 3", name="ck_highlights_learning_range"),
        Index("ix_highlights_patient_id", "patient_id"),
        Index("ix_highlights_clinical_fact_id", "clinical_fact_id"),
        Index("ix_highlights_reviewed_by_id", "reviewed_by_id"),
        Index("ix_highlights_patient_status", "patient_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False
    )
    clinical_fact_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("clinical_facts.id", ondelete="RESTRICT"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[HighlightCategory] = mapped_column(
        enum_column(HighlightCategory, "highlight_category"), nullable=False
    )
    risk_level: Mapped[RiskLevel] = mapped_column(
        enum_column(RiskLevel, "highlight_risk_level"), nullable=False
    )
    risk_reason: Mapped[str] = mapped_column(Text, nullable=False)
    base_score: Mapped[int] = mapped_column(Integer, nullable=False)
    learned_score: Mapped[float] = mapped_column(Float, nullable=False, default=0, server_default="0")
    status: Mapped[HighlightStatus] = mapped_column(
        enum_column(HighlightStatus, "highlight_status"),
        nullable=False,
        default=HighlightStatus.SUGGESTED,
        server_default=HighlightStatus.SUGGESTED.value,
    )
    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    patient: Mapped[Patient] = relationship()
    clinical_fact: Mapped[ClinicalFact] = relationship(back_populates="highlights")
    reviewed_by: Mapped[User | None] = relationship()


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_patient_id", "patient_id"),
        Index("ix_tasks_source_entry_id", "source_entry_id"),
        Index("ix_tasks_source_fact_id", "source_fact_id"),
        Index("ix_tasks_completed_by_id", "completed_by_id"),
        Index("ix_tasks_patient_status", "patient_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False
    )
    source_entry_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("entries.id", ondelete="RESTRICT"), nullable=False
    )
    source_fact_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("clinical_facts.id", ondelete="RESTRICT"), nullable=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[TaskPriority] = mapped_column(
        enum_column(TaskPriority, "task_priority"), nullable=False
    )
    status: Mapped[TaskStatus] = mapped_column(
        enum_column(TaskStatus, "task_status"),
        nullable=False,
        default=TaskStatus.OPEN,
        server_default=TaskStatus.OPEN.value,
    )
    assigned_role: Mapped[UserRole | None] = mapped_column(
        enum_column(UserRole, "task_assigned_role"), nullable=True
    )
    completed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    patient: Mapped[Patient] = relationship()
    source_entry: Mapped[Entry] = relationship()
    source_fact: Mapped[ClinicalFact | None] = relationship()
    completed_by: Mapped[User | None] = relationship()


class Conflict(Base):
    __tablename__ = "conflicts"
    __table_args__ = (
        CheckConstraint(
            "conflicting_fact_id <> authoritative_fact_id",
            name="ck_conflicts_distinct_facts",
        ),
        Index("ix_conflicts_patient_id", "patient_id"),
        Index("ix_conflicts_conflicting_fact_id", "conflicting_fact_id"),
        Index("ix_conflicts_authoritative_fact_id", "authoritative_fact_id"),
        Index("ix_conflicts_resolved_by_id", "resolved_by_id"),
        Index("ix_conflicts_patient_status", "patient_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False
    )
    conflict_type: Mapped[ConflictType] = mapped_column(
        enum_column(ConflictType, "conflict_type"), nullable=False
    )
    entity_name: Mapped[str] = mapped_column(Text, nullable=False)
    conflicting_fact_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("clinical_facts.id", ondelete="RESTRICT"), nullable=False
    )
    authoritative_fact_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("clinical_facts.id", ondelete="RESTRICT"), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ConflictStatus] = mapped_column(
        enum_column(ConflictStatus, "conflict_status"),
        nullable=False,
        default=ConflictStatus.DETECTED,
        server_default=ConflictStatus.DETECTED.value,
    )
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    patient: Mapped[Patient] = relationship()
    conflicting_fact: Mapped[ClinicalFact] = relationship(foreign_keys=[conflicting_fact_id])
    authoritative_fact: Mapped[ClinicalFact] = relationship(
        foreign_keys=[authoritative_fact_id]
    )
    resolved_by: Mapped[User | None] = relationship()
