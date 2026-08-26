"""Append-only entry snapshot operations."""

import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditEvent, ChangeReason, EntryVersion
from app.models.identity import User
from app.models.timeline import Entry


class EntryVersionConflictError(Exception):
    def __init__(self, current_version: int, expected_version: int) -> None:
        self.current_version = current_version
        self.expected_version = expected_version
        super().__init__("Entry version conflict")


def update_entry(
    db: Session,
    entry: Entry,
    actor: User,
    content: str,
    expected_version: int,
) -> Entry:
    if entry.current_version != expected_version:
        raise EntryVersionConflictError(entry.current_version, expected_version)

    _ensure_snapshot_for_current_version(db, entry, actor)
    new_version = entry.current_version + 1
    db.add(
        EntryVersion(
            entry=entry,
            version_number=new_version,
            content=content,
            changed_by=actor,
            change_reason=ChangeReason.MANUAL_EDIT,
            source_version=entry.current_version,
            content_hash=_content_hash(content),
        )
    )
    db.add(
        AuditEvent(
            clinic_id=actor.clinic_id,
            patient_id=entry.patient_id,
            actor=actor,
            action="entry.updated",
            resource_type="entry",
            resource_id=entry.id,
            event_metadata={
                "from_version": entry.current_version,
                "to_version": new_version,
            },
        )
    )
    entry.content = content
    entry.current_version = new_version
    db.commit()
    db.refresh(entry)
    return entry


def _ensure_snapshot_for_current_version(
    db: Session,
    entry: Entry,
    actor: User,
) -> None:
    existing = db.scalar(
        select(EntryVersion.id).where(
            EntryVersion.entry_id == entry.id,
            EntryVersion.version_number == entry.current_version,
        )
    )
    if existing is not None:
        return

    original_actor = entry.author or actor
    db.add(
        EntryVersion(
            entry=entry,
            version_number=entry.current_version,
            content=entry.content,
            changed_by=original_actor,
            changed_at=entry.updated_at,
            change_reason=ChangeReason.CREATED,
            source_version=None,
            content_hash=_content_hash(entry.content),
        )
    )


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
