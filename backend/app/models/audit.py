from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, JSON, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.clinical import Highlight
from app.models.identity import Clinic, Patient, User, UserRole
from app.models.timeline import Entry, enum_column


class ChangeReason(str, enum.Enum):
    CREATED = "created"
    MANUAL_EDIT = "manual_edit"
    REVERT = "revert"
    CONFLICT_RESOLUTION = "conflict_resolution"
    SYSTEM_CORRECTION = "system_correction"


class FeedbackAction(str, enum.Enum):
    ACCEPT = "accept"
    REJECT = "reject"
    EDIT = "edit"
    COMMENT = "comment"


class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = (
        Index("ix_comments_entry_id", "entry_id"),
        Index("ix_comments_author_id", "author_id"),
        Index("ix_comments_parent_comment_id", "parent_comment_id"),
        Index("ix_comments_resolved_by_id", "resolved_by_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    entry_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("entries.id", ondelete="RESTRICT"), nullable=False
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    parent_comment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("comments.id", ondelete="RESTRICT"), nullable=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    mentioned_role: Mapped[UserRole | None] = mapped_column(
        enum_column(UserRole, "comment_mentioned_role"), nullable=True
    )
    resolved: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    resolved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    entry: Mapped[Entry] = relationship()
    author: Mapped[User] = relationship(foreign_keys=[author_id])
    parent_comment: Mapped[Comment | None] = relationship(
        remote_side="Comment.id", back_populates="replies"
    )
    replies: Mapped[list[Comment]] = relationship(back_populates="parent_comment")
    resolved_by: Mapped[User | None] = relationship(foreign_keys=[resolved_by_id])


class EntryVersion(Base):
    __tablename__ = "entry_versions"
    __table_args__ = (
        CheckConstraint("version_number >= 1", name="ck_entry_versions_number_positive"),
        CheckConstraint(
            "(version_number = 1 AND source_version IS NULL) OR "
            "(version_number > 1 AND source_version >= 1 AND source_version < version_number)",
            name="ck_entry_versions_source_precedes_version",
        ),
        CheckConstraint("length(content_hash) = 64", name="ck_entry_versions_sha256_length"),
        UniqueConstraint("entry_id", "version_number", name="uq_entry_versions_entry_version"),
        Index("ix_entry_versions_entry_id", "entry_id"),
        Index("ix_entry_versions_changed_by_id", "changed_by_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    entry_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("entries.id", ondelete="RESTRICT"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    changed_by_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    change_reason: Mapped[ChangeReason] = mapped_column(
        enum_column(ChangeReason, "change_reason"), nullable=False
    )
    source_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reverted_from_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)

    entry: Mapped[Entry] = relationship()
    changed_by: Mapped[User] = relationship()


class ImportanceFeedback(Base):
    __tablename__ = "importance_feedback"
    __table_args__ = (
        CheckConstraint(
            "ranking_delta >= -1 AND ranking_delta <= 1",
            name="ck_importance_feedback_delta_range",
        ),
        Index("ix_importance_feedback_patient_id", "patient_id"),
        Index("ix_importance_feedback_actor_id", "actor_id"),
        Index("ix_importance_feedback_highlight_id", "highlight_id"),
        Index("ix_importance_feedback_patient_entity", "patient_id", "entity_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    highlight_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("highlights.id", ondelete="RESTRICT"), nullable=True
    )
    entity_key: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[FeedbackAction] = mapped_column(
        enum_column(FeedbackAction, "feedback_action"), nullable=False
    )
    ranking_delta: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    patient: Mapped[Patient] = relationship()
    actor: Mapped[User] = relationship()
    highlight: Mapped[Highlight | None] = relationship()


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_clinic_id", "clinic_id"),
        Index("ix_audit_events_patient_id", "patient_id"),
        Index("ix_audit_events_actor_id", "actor_id"),
        Index("ix_audit_events_resource", "resource_type", "resource_id"),
        Index("ix_audit_events_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("clinics.id", ondelete="RESTRICT"), nullable=False
    )
    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("patients.id", ondelete="RESTRICT"), nullable=True
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    action: Mapped[str] = mapped_column(Text, nullable=False)
    resource_type: Mapped[str] = mapped_column(Text, nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    event_metadata: Mapped[dict[str, object]] = mapped_column("metadata", JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    clinic: Mapped[Clinic] = relationship()
    patient: Mapped[Patient | None] = relationship()
    actor: Mapped[User | None] = relationship()
