"""Build the role-aware CareState read model from persisted clinical state."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.glance.schemas import (
    CareStateResponse,
    GlanceDetails,
    GlanceItem,
    GlancePatient,
    GlanceSource,
)
from app.models.clinical import (
    ClinicalFact,
    Conflict,
    ConflictStatus,
    Highlight,
    HighlightCategory,
    HighlightStatus,
    RiskLevel,
    Task,
    TaskPriority,
    TaskStatus,
)
from app.models.identity import Patient, User, UserRole
from app.models.timeline import Entry


def build_care_state(
    db: Session,
    patient: Patient,
    user: User,
    *,
    now: datetime | None = None,
) -> CareStateResponse:
    visible_statuses = (
        (HighlightStatus.ACCEPTED,)
        if user.role is UserRole.PATIENT
        else (HighlightStatus.ACCEPTED, HighlightStatus.SUGGESTED)
    )
    highlights = list(
        db.scalars(
            select(Highlight)
            .options(
                joinedload(Highlight.clinical_fact)
                .joinedload(ClinicalFact.entry)
                .joinedload(Entry.consult_session)
            )
            .where(
                Highlight.patient_id == patient.id,
                Highlight.status.in_(visible_statuses),
                Highlight.category.in_(
                    (HighlightCategory.CRITICAL, HighlightCategory.RECENT_CHANGE)
                ),
            )
        )
    )
    highlights.sort(
        key=lambda item: (item.base_score + item.learned_score, _aware(item.created_at)),
        reverse=True,
    )

    critical = [
        _highlight_item(item)
        for item in highlights
        if item.category is HighlightCategory.CRITICAL
    ][:2]
    recent_changes = [
        _highlight_item(item)
        for item in highlights
        if item.category is HighlightCategory.RECENT_CHANGE
    ][:2]

    open_actions: list[GlanceItem] = []
    conflicts: list[GlanceItem] = []
    if user.role is not UserRole.PATIENT:
        open_actions = _open_action_items(db, patient.id)
        conflicts = _conflict_items(db, patient.id)

    return CareStateResponse(
        patient=GlancePatient(
            id=patient.id,
            external_ref=patient.external_ref,
            display_name=patient.display_name,
        ),
        generated_at=now or datetime.now(timezone.utc),
        critical=critical,
        recent_changes=recent_changes,
        open_actions=open_actions,
        conflicts=conflicts,
    )


def _open_action_items(db: Session, patient_id: uuid.UUID) -> list[GlanceItem]:
    tasks = list(
        db.scalars(
            select(Task)
            .options(
                joinedload(Task.source_entry).joinedload(Entry.consult_session),
                joinedload(Task.source_fact)
                .joinedload(ClinicalFact.entry)
                .joinedload(Entry.consult_session),
            )
            .where(Task.patient_id == patient_id, Task.status == TaskStatus.OPEN)
        )
    )
    priority = {TaskPriority.HIGH: 3, TaskPriority.MEDIUM: 2, TaskPriority.LOW: 1}
    tasks.sort(
        key=lambda item: (priority[item.priority], _aware(item.created_at)),
        reverse=True,
    )

    items: list[GlanceItem] = []
    for task in tasks[:2]:
        fact = task.source_fact
        entry = fact.entry if fact is not None else task.source_entry
        source_quote = fact.source_quote if fact is not None else entry.content
        items.append(
            GlanceItem(
                id=task.id,
                title=task.description,
                category=HighlightCategory.OPEN_ACTION.value,
                status=task.status.value,
                risk_level=_task_risk(task.priority).value,
                risk_reason=(
                    f"{task.priority.value.title()}-priority open action requires follow-up"
                ),
                source=_source(entry, source_quote, fact),
                details=GlanceDetails(
                    entity_name=fact.entity_name if fact is not None else None,
                    value_text=fact.value_text if fact is not None else None,
                    value_number=fact.value_number if fact is not None else None,
                    unit=fact.unit if fact is not None else None,
                    fact_review_status=(
                        fact.review_status.value if fact is not None else None
                    ),
                    task_priority=task.priority.value,
                    task_status=task.status.value,
                ),
            )
        )
    return items


def _conflict_items(db: Session, patient_id: uuid.UUID) -> list[GlanceItem]:
    conflicts = list(
        db.scalars(
            select(Conflict)
            .options(
                joinedload(Conflict.conflicting_fact)
                .joinedload(ClinicalFact.entry)
                .joinedload(Entry.consult_session),
                joinedload(Conflict.authoritative_fact)
                .joinedload(ClinicalFact.entry)
                .joinedload(Entry.consult_session),
            )
            .where(
                Conflict.patient_id == patient_id,
                Conflict.status == ConflictStatus.DETECTED,
            )
        )
    )
    conflicts.sort(key=lambda item: _aware(item.created_at), reverse=True)

    items: list[GlanceItem] = []
    for conflict in conflicts[:1]:
        fact = conflict.conflicting_fact
        items.append(
            GlanceItem(
                id=conflict.id,
                title=f"{conflict.entity_name.title()} discrepancy",
                category=HighlightCategory.CONFLICT.value,
                status=conflict.status.value,
                risk_level=fact.risk_level.value,
                risk_reason=conflict.description,
                source=_source(fact.entry, fact.source_quote, fact),
                details=GlanceDetails(
                    entity_name=conflict.entity_name,
                    value_text=fact.value_text,
                    value_number=fact.value_number,
                    unit=fact.unit,
                    fact_review_status=fact.review_status.value,
                    authoritative_value=conflict.authoritative_fact.value_text,
                    conflicting_value=fact.value_text,
                ),
            )
        )
    return items


def _highlight_item(highlight: Highlight) -> GlanceItem:
    fact = highlight.clinical_fact
    return GlanceItem(
        id=highlight.id,
        title=highlight.text,
        category=highlight.category.value,
        status=highlight.status.value,
        risk_level=highlight.risk_level.value,
        risk_reason=highlight.risk_reason,
        source=_source(fact.entry, fact.source_quote, fact),
        details=GlanceDetails(
            entity_name=fact.entity_name,
            value_text=fact.value_text,
            value_number=fact.value_number,
            unit=fact.unit,
            fact_review_status=fact.review_status.value,
        ),
    )


def _source(
    entry: Entry,
    source_quote: str,
    fact: ClinicalFact | None = None,
) -> GlanceSource:
    occurred_at = (
        entry.consult_session.occurred_at
        if entry.consult_session is not None
        else entry.created_at
    )
    return GlanceSource(
        entry_id=entry.id,
        entry_type=entry.entry_type.value,
        occurred_at=_aware(occurred_at),
        provenance_type=entry.provenance_type.value,
        provenance_id=entry.provenance_id,
        source_quote=source_quote,
        source_start=fact.source_start if fact is not None else None,
        source_end=fact.source_end if fact is not None else None,
    )


def _task_risk(priority: TaskPriority) -> RiskLevel:
    return {
        TaskPriority.HIGH: RiskLevel.HIGH,
        TaskPriority.MEDIUM: RiskLevel.MEDIUM,
        TaskPriority.LOW: RiskLevel.LOW,
    }[priority]


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
