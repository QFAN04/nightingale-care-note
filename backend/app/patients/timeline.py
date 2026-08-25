import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.identity import User, UserRole
from app.models.timeline import (
    AuthorRole,
    ConsultSession,
    Entry,
    EntryType,
    ProvenanceType,
)


class TimelineEntryRead(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    author_id: uuid.UUID | None
    author_role: AuthorRole
    entry_type: EntryType
    content: str
    occurred_at: datetime
    provenance_type: ProvenanceType
    provenance_id: uuid.UUID | None
    current_version: int


def list_timeline_entries(
    session: Session,
    user: User,
    patient_id: uuid.UUID,
) -> list[TimelineEntryRead]:
    occurred_at = func.coalesce(ConsultSession.occurred_at, Entry.created_at).label(
        "occurred_at"
    )
    statement = (
        select(Entry, occurred_at)
        .outerjoin(ConsultSession, Entry.provenance_id == ConsultSession.id)
        .where(Entry.patient_id == patient_id)
    )
    if user.role is UserRole.PATIENT:
        statement = statement.where(Entry.entry_type == EntryType.PATIENT_INSTRUCTION)

    rows = session.execute(statement.order_by(occurred_at.desc(), Entry.id.desc())).all()
    return [
        TimelineEntryRead(
            id=entry.id,
            patient_id=entry.patient_id,
            author_id=entry.author_id,
            author_role=entry.author_role,
            entry_type=entry.entry_type,
            content=entry.content,
            occurred_at=row_occurred_at,
            provenance_type=entry.provenance_type,
            provenance_id=entry.provenance_id,
            current_version=entry.current_version,
        )
        for entry, row_occurred_at in rows
    ]
