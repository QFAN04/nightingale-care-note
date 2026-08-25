from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.identity import Patient, User


def enum_column(enum_type: type[enum.Enum], name: str) -> Enum:
    return Enum(
        enum_type,
        name=name,
        native_enum=False,
        create_constraint=True,
        values_callable=lambda values: [value.value for value in values],
    )


class InteractionType(str, enum.Enum):
    DOCTOR_PATIENT = "doctor_patient"
    NURSE_PATIENT = "nurse_patient"
    AI_PATIENT = "ai_patient"


class ProcessingStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class AuthorRole(str, enum.Enum):
    PATIENT = "patient"
    STAFF = "staff"
    CLINICIAN = "clinician"
    SYSTEM = "system"


class EntryType(str, enum.Enum):
    CLINICIAN_NOTE = "clinician_note"
    STAFF_NOTE = "staff_note"
    AI_DOCTOR_CONSULT_SUMMARY = "ai_doctor_consult_summary"
    AI_NURSE_CONSULT_SUMMARY = "ai_nurse_consult_summary"
    AI_PATIENT_SESSION_SUMMARY = "ai_patient_session_summary"
    PATIENT_INSTRUCTION = "patient_instruction"
    SYSTEM_EVENT = "system_event"


class ProvenanceType(str, enum.Enum):
    CONSULT_SESSION = "consult_session"
    MANUAL = "manual"
    SYSTEM = "system"


class ConsultSession(Base):
    __tablename__ = "consult_sessions"
    __table_args__ = (
        Index("ix_consult_sessions_patient_id", "patient_id"),
        Index("ix_consult_sessions_created_by_id", "created_by_id"),
        Index("ix_consult_sessions_patient_occurred_at", "patient_id", "occurred_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False
    )
    interaction_type: Mapped[InteractionType] = mapped_column(
        enum_column(InteractionType, "interaction_type"), nullable=False
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw_transcript: Mapped[str] = mapped_column(Text, nullable=False)
    redacted_transcript: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    processing_status: Mapped[ProcessingStatus] = mapped_column(
        enum_column(ProcessingStatus, "processing_status"),
        nullable=False,
        default=ProcessingStatus.PENDING,
        server_default=ProcessingStatus.PENDING.value,
    )
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    patient: Mapped[Patient] = relationship()
    created_by: Mapped[User | None] = relationship()
    entries: Mapped[list[Entry]] = relationship(back_populates="consult_session")


class Entry(Base):
    __tablename__ = "entries"
    __table_args__ = (
        CheckConstraint("current_version >= 1", name="ck_entries_current_version_positive"),
        CheckConstraint(
            "(provenance_type = 'consult_session' AND provenance_id IS NOT NULL) OR "
            "(provenance_type <> 'consult_session' AND provenance_id IS NULL)",
            name="ck_entries_consult_provenance",
        ),
        Index("ix_entries_patient_id", "patient_id"),
        Index("ix_entries_author_id", "author_id"),
        Index("ix_entries_provenance_id", "provenance_id"),
        Index("ix_entries_patient_created_at", "patient_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False
    )
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    author_role: Mapped[AuthorRole] = mapped_column(
        enum_column(AuthorRole, "entry_author_role"), nullable=False
    )
    entry_type: Mapped[EntryType] = mapped_column(
        enum_column(EntryType, "entry_type"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    current_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    provenance_type: Mapped[ProvenanceType] = mapped_column(
        enum_column(ProvenanceType, "provenance_type"), nullable=False
    )
    provenance_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("consult_sessions.id", ondelete="RESTRICT"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    patient: Mapped[Patient] = relationship()
    author: Mapped[User | None] = relationship()
    consult_session: Mapped[ConsultSession | None] = relationship(back_populates="entries")
