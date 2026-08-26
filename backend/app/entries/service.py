"""Append-only entry snapshot operations."""

import hashlib
import re
from difflib import SequenceMatcher

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.audit import AuditEvent, ChangeReason, EntryVersion
from app.models.identity import Patient, User, UserRole
from app.models.timeline import AuthorRole, Entry, EntryType, ProvenanceType


class EntryVersionConflictError(Exception):
    def __init__(self, current_version: int, expected_version: int) -> None:
        self.current_version = current_version
        self.expected_version = expected_version
        super().__init__("Entry version conflict")


class EntryVersionNotFoundError(Exception):
    pass


def create_manual_entry(
    db: Session,
    patient: Patient,
    actor: User,
    content: str,
) -> Entry:
    role_fields = {
        UserRole.STAFF: (AuthorRole.STAFF, EntryType.STAFF_NOTE),
        UserRole.CLINICIAN: (AuthorRole.CLINICIAN, EntryType.CLINICIAN_NOTE),
    }
    author_role, entry_type = role_fields[actor.role]
    entry = Entry(
        patient=patient,
        author=actor,
        author_role=author_role,
        entry_type=entry_type,
        content=content,
        current_version=1,
        provenance_type=ProvenanceType.MANUAL,
        provenance_id=None,
    )
    db.add(entry)
    db.flush()
    db.add(
        EntryVersion(
            entry=entry,
            version_number=1,
            content=content,
            changed_by=actor,
            change_reason=ChangeReason.CREATED,
            source_version=None,
            content_hash=_content_hash(content),
        )
    )
    db.add(
        AuditEvent(
            clinic_id=actor.clinic_id,
            patient_id=patient.id,
            actor=actor,
            action="entry.created",
            resource_type="entry",
            resource_id=entry.id,
            event_metadata={"version": 1, "entry_type": entry_type.value},
        )
    )
    db.commit()
    db.refresh(entry)
    return entry


def update_entry(
    db: Session,
    entry: Entry,
    actor: User,
    content: str,
    expected_version: int,
) -> Entry:
    _ensure_snapshot_for_current_version(db, entry, actor)
    new_version = expected_version + 1
    claimed = db.execute(
        update(Entry)
        .where(
            Entry.id == entry.id,
            Entry.current_version == expected_version,
        )
        .values(content=content, current_version=new_version)
        .execution_options(synchronize_session=False)
    )
    if claimed.rowcount != 1:
        db.rollback()
        current_version = db.scalar(
            select(Entry.current_version).where(Entry.id == entry.id)
        )
        raise EntryVersionConflictError(
            current_version if current_version is not None else entry.current_version,
            expected_version,
        )

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
                "from_version": expected_version,
                "to_version": new_version,
            },
        )
    )
    db.commit()
    db.refresh(entry)
    return entry


def get_entry_diff(
    db: Session,
    entry_id: object,
    from_version: int,
    to_version: int,
) -> list[dict[str, str]]:
    versions = list(
        db.scalars(
            select(EntryVersion).where(
                EntryVersion.entry_id == entry_id,
                EntryVersion.version_number.in_((from_version, to_version)),
            )
        )
    )
    by_number = {version.version_number: version for version in versions}
    if from_version not in by_number or to_version not in by_number:
        raise EntryVersionNotFoundError

    before = _tokens(by_number[from_version].content)
    after = _tokens(by_number[to_version].content)
    parts: list[dict[str, str]] = []
    for operation, before_start, before_end, after_start, after_end in SequenceMatcher(
        None, before, after
    ).get_opcodes():
        if operation in ("equal", "delete", "replace"):
            part_type = "unchanged" if operation == "equal" else "removed"
            _append_diff_part(parts, part_type, before[before_start:before_end])
        if operation in ("insert", "replace"):
            _append_diff_part(parts, "added", after[after_start:after_end])
    return parts


def revert_entry(
    db: Session,
    entry: Entry,
    actor: User,
    target_version: int,
    expected_version: int,
) -> EntryVersion:
    if entry.current_version != expected_version:
        raise EntryVersionConflictError(entry.current_version, expected_version)

    target = db.scalar(
        select(EntryVersion).where(
            EntryVersion.entry_id == entry.id,
            EntryVersion.version_number == target_version,
        )
    )
    if target is None:
        raise EntryVersionNotFoundError

    new_version_number = entry.current_version + 1
    new_version = EntryVersion(
        entry=entry,
        version_number=new_version_number,
        content=target.content,
        changed_by=actor,
        change_reason=ChangeReason.REVERT,
        source_version=entry.current_version,
        reverted_from_version=target_version,
        content_hash=_content_hash(target.content),
    )
    db.add(new_version)
    db.add(
        AuditEvent(
            clinic_id=actor.clinic_id,
            patient_id=entry.patient_id,
            actor=actor,
            action="entry.reverted",
            resource_type="entry",
            resource_id=entry.id,
            event_metadata={
                "from_version": entry.current_version,
                "to_version": new_version_number,
                "reverted_from": target_version,
            },
        )
    )
    entry.content = target.content
    entry.current_version = new_version_number
    db.commit()
    db.refresh(new_version)
    return new_version


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


def _tokens(content: str) -> list[str]:
    return re.findall(r"\S+\s*", content)


def _append_diff_part(
    parts: list[dict[str, str]],
    part_type: str,
    tokens: list[str],
) -> None:
    text = "".join(tokens).strip()
    if text:
        parts.append({"type": part_type, "text": text})
