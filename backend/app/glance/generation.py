"""Generate deterministic Highlight suggestions from structured clinical state."""

import uuid
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.glance.importance import (
    ImportanceEntity,
    ImportanceInput,
    SourceAuthority,
    is_highlight_candidate,
    score_importance,
)
from app.models.audit import FeedbackAction, ImportanceFeedback
from app.models.clinical import (
    ClinicalFact,
    Conflict,
    ConflictStatus,
    FactType,
    Highlight,
    HighlightCategory,
    HighlightStatus,
    PersistenceType,
    ReviewStatus,
    RiskLevel,
    Task,
    TaskStatus,
)
from app.models.identity import Patient
from app.models.timeline import AuthorRole, EntryType


def generate_highlight_suggestions(
    db: Session,
    patient_id: uuid.UUID,
    *,
    now: datetime,
) -> list[Highlight]:
    clinic_id = db.scalar(
        select(Patient.clinic_id).where(Patient.id == patient_id)
    )
    if clinic_id is None:
        return []
    facts = list(
        db.scalars(
            select(ClinicalFact)
            .where(ClinicalFact.patient_id == patient_id)
            .order_by(ClinicalFact.created_at.desc(), ClinicalFact.id)
        )
    )
    tasks = list(
        db.scalars(
            select(Task).where(
                Task.patient_id == patient_id,
                Task.status == TaskStatus.OPEN,
                Task.source_fact_id.is_not(None),
            )
        )
    )
    conflicts = list(
        db.scalars(
            select(Conflict).where(
                Conflict.patient_id == patient_id,
                Conflict.status == ConflictStatus.DETECTED,
            )
        )
    )
    existing = set(
        db.execute(
            select(Highlight.clinical_fact_id, Highlight.category).where(
                Highlight.patient_id == patient_id
            )
        ).all()
    )
    active_persistent_critical_entities = {
        _entity_key(entity_name)
        for entity_name in db.scalars(
            select(ClinicalFact.entity_name)
            .join(Highlight, Highlight.clinical_fact_id == ClinicalFact.id)
            .where(
                Highlight.patient_id == patient_id,
                Highlight.category == HighlightCategory.CRITICAL,
                Highlight.status.in_(
                    (HighlightStatus.SUGGESTED, HighlightStatus.ACCEPTED)
                ),
                ClinicalFact.risk_level == RiskLevel.CRITICAL,
                ClinicalFact.persistence_type == PersistenceType.PERSISTENT,
            )
        )
    }

    tasks_by_fact: dict[uuid.UUID, list[Task]] = defaultdict(list)
    for task in tasks:
        if task.source_fact_id is not None:
            tasks_by_fact[task.source_fact_id].append(task)
    conflicts_by_fact = {conflict.conflicting_fact_id: conflict for conflict in conflicts}
    feedback_by_entity = _feedback_counts(db, clinic_id)

    generated: list[Highlight] = []
    for fact in facts:
        if not (
            fact.review_status is ReviewStatus.SUGGESTED
            or (
                fact.risk_level is RiskLevel.CRITICAL
                and fact.persistence_type is PersistenceType.PERSISTENT
            )
        ):
            continue
        linked_tasks = tasks_by_fact.get(fact.id, [])
        highest_task = max(
            linked_tasks,
            key=lambda item: {"low": 1, "medium": 3, "high": 5}[item.priority.value],
            default=None,
        )
        accepts, rejects = feedback_by_entity.get(fact.entity_name.casefold(), (0, 0))
        item = ImportanceInput(
            risk_level=fact.risk_level,
            occurred_at=_aware(fact.created_at),
            entity_type=fact.fact_type,
            persistence_type=fact.persistence_type,
            source_authority=_source_authority(fact),
            task_status=highest_task.status if highest_task else None,
            task_priority=highest_task.priority if highest_task else None,
            accept_count=accepts,
            reject_count=rejects,
        )
        score = score_importance(item, now=now)
        conflict = conflicts_by_fact.get(fact.id)
        category = _fact_category(fact, conflict)
        persistent_critical_key = _persistent_critical_key(fact, category)
        if (
            persistent_critical_key is not None
            and persistent_critical_key in active_persistent_critical_entities
        ):
            continue
        if is_highlight_candidate(item, score) and (fact.id, category) not in existing:
            highlight = Highlight(
                patient_id=patient_id,
                clinical_fact=fact,
                text=conflict.description if conflict else _fact_title(fact),
                category=category,
                risk_level=fact.risk_level,
                risk_reason=_risk_reason(score.explanations, conflict is not None),
                base_score=round(score.final_score - score.learning_score),
                learned_score=score.learning_score,
                status=HighlightStatus.SUGGESTED,
                created_at=now,
            )
            db.add(highlight)
            generated.append(highlight)
            existing.add((fact.id, category))
            if persistent_critical_key is not None:
                active_persistent_critical_entities.add(persistent_critical_key)

    for task in tasks:
        if task.source_fact is None:
            continue
        category = HighlightCategory.OPEN_ACTION
        if (task.source_fact_id, category) in existing:
            continue
        fact = task.source_fact
        accepts, rejects = feedback_by_entity.get(fact.entity_name.casefold(), (0, 0))
        item = ImportanceInput(
            risk_level=fact.risk_level,
            occurred_at=_aware(task.created_at),
            entity_type=ImportanceEntity.TASK,
            persistence_type=fact.persistence_type,
            source_authority=_entry_source_authority(task.source_entry.author_role),
            task_status=task.status,
            task_priority=task.priority,
            accept_count=accepts,
            reject_count=rejects,
        )
        score = score_importance(item, now=now)
        if not is_highlight_candidate(item, score):
            continue
        highlight = Highlight(
            patient_id=patient_id,
            clinical_fact=fact,
            text=task.description,
            category=category,
            risk_level=fact.risk_level,
            risk_reason=_risk_reason(score.explanations),
            base_score=round(score.final_score - score.learning_score),
            learned_score=score.learning_score,
            status=HighlightStatus.SUGGESTED,
            created_at=now,
        )
        db.add(highlight)
        generated.append(highlight)
        existing.add((fact.id, category))

    db.flush()
    return generated


def _feedback_counts(
    db: Session, clinic_id: uuid.UUID
) -> dict[str, tuple[int, int]]:
    counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    feedback = db.scalars(
        select(ImportanceFeedback)
        .join(Patient, ImportanceFeedback.patient_id == Patient.id)
        .where(Patient.clinic_id == clinic_id)
    )
    for item in feedback:
        key = item.entity_key.casefold()
        if item.action is FeedbackAction.ACCEPT:
            counts[key][0] += 1
        elif item.action is FeedbackAction.REJECT:
            counts[key][1] += 1
    return {key: (values[0], values[1]) for key, values in counts.items()}


def _fact_category(
    fact: ClinicalFact,
    conflict: Conflict | None,
) -> HighlightCategory:
    if conflict is not None:
        return HighlightCategory.CONFLICT
    if fact.risk_level is RiskLevel.CRITICAL:
        return HighlightCategory.CRITICAL
    return HighlightCategory.RECENT_CHANGE


def _source_authority(fact: ClinicalFact) -> SourceAuthority:
    if fact.review_status is ReviewStatus.CONFIRMED:
        return SourceAuthority.CLINICIAN_ACCEPTED
    return _entry_source_authority(fact.entry.author_role, fact.entry.entry_type)


def _entry_source_authority(
    author_role: AuthorRole,
    entry_type: EntryType | None = None,
) -> SourceAuthority:
    if author_role is AuthorRole.CLINICIAN:
        return SourceAuthority.CLINICIAN_MANUAL
    if author_role is AuthorRole.STAFF:
        return SourceAuthority.STAFF_MANUAL
    if entry_type is EntryType.AI_PATIENT_SESSION_SUMMARY:
        return SourceAuthority.PATIENT_AI_SESSION
    return SourceAuthority.AI_SUGGESTION


def _fact_title(fact: ClinicalFact) -> str:
    if fact.fact_type is FactType.ALLERGY:
        return f"{fact.entity_name.title()} allergy"
    if fact.fact_type is FactType.SYMPTOM and fact.value_text:
        return f"{fact.value_text.title()} {fact.entity_name}"
    return fact.entity_name.title()


def _persistent_critical_key(
    fact: ClinicalFact,
    category: HighlightCategory,
) -> str | None:
    if (
        category is HighlightCategory.CRITICAL
        and fact.risk_level is RiskLevel.CRITICAL
        and fact.persistence_type is PersistenceType.PERSISTENT
    ):
        return _entity_key(fact.entity_name)
    return None


def _entity_key(value: str) -> str:
    return " ".join(value.split()).casefold()


def _risk_reason(explanations: tuple[str, ...], conflict: bool = False) -> str:
    reasons = list(explanations)
    if conflict:
        reasons.insert(0, "detected clinical conflict")
    return " · ".join(reasons)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
