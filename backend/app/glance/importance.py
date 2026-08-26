"""Centralized and explainable first-version Importance Engine."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from app.models.clinical import (
    FactType,
    PersistenceType,
    RiskLevel,
    TaskPriority,
    TaskStatus,
)


class ImportanceEntity(StrEnum):
    ALLERGY = "allergy"
    DIAGNOSIS = "diagnosis"
    MEDICATION = "medication"
    SYMPTOM = "symptom"
    TASK = "task"
    OTHER = "other"


class SourceAuthority(StrEnum):
    CLINICIAN_MANUAL = "clinician_manual"
    CLINICIAN_ACCEPTED = "clinician_accepted"
    STAFF_MANUAL = "staff_manual"
    AI_SUGGESTION = "ai_suggestion"
    PATIENT_AI_SESSION = "patient_ai_session"


RISK_WEIGHTS = {
    RiskLevel.CRITICAL: 10,
    RiskLevel.HIGH: 7,
    RiskLevel.MEDIUM: 3,
    RiskLevel.LOW: 1,
}

ENTITY_WEIGHTS = {
    ImportanceEntity.ALLERGY.value: 4,
    ImportanceEntity.DIAGNOSIS.value: 3,
    ImportanceEntity.MEDICATION.value: 2,
    ImportanceEntity.SYMPTOM.value: 2,
    ImportanceEntity.TASK.value: 1,
    ImportanceEntity.OTHER.value: 0,
}

OPEN_TASK_WEIGHTS = {
    TaskPriority.HIGH: 5,
    TaskPriority.MEDIUM: 3,
    TaskPriority.LOW: 1,
}

SOURCE_AUTHORITY_WEIGHTS = {
    SourceAuthority.CLINICIAN_MANUAL: 4,
    SourceAuthority.CLINICIAN_ACCEPTED: 4,
    SourceAuthority.STAFF_MANUAL: 2,
    SourceAuthority.AI_SUGGESTION: 0,
    SourceAuthority.PATIENT_AI_SESSION: 0,
}

PERSISTENT_CRITICAL_WEIGHT = 4
LEARNING_ACCEPT_WEIGHT = 0.25
LEARNING_REJECT_WEIGHT = 0.20
LEARNING_MIN = 0.0
LEARNING_MAX = 3.0
HIGHLIGHT_THRESHOLD = 7.0


@dataclass(frozen=True)
class ImportanceInput:
    risk_level: RiskLevel
    occurred_at: datetime
    entity_type: FactType | ImportanceEntity
    persistence_type: PersistenceType
    source_authority: SourceAuthority
    task_status: TaskStatus | None = None
    task_priority: TaskPriority | None = None
    accept_count: int = 0
    reject_count: int = 0

    def __post_init__(self) -> None:
        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")
        if self.accept_count < 0 or self.reject_count < 0:
            raise ValueError("feedback counts cannot be negative")
        if self.task_status is TaskStatus.OPEN and self.task_priority is None:
            raise ValueError("an open task requires a priority")


@dataclass(frozen=True)
class ImportanceScore:
    risk_score: int
    recency_score: int
    entity_score: int
    task_score: int
    source_authority_score: int
    persistence_score: int
    learning_score: float
    final_score: float
    explanations: tuple[str, ...]


def score_importance(item: ImportanceInput, *, now: datetime) -> ImportanceScore:
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")

    risk_score = RISK_WEIGHTS[item.risk_level]
    recency_score = _recency_score(item.occurred_at, now)
    entity_score = ENTITY_WEIGHTS.get(item.entity_type.value, 0)
    task_score = (
        OPEN_TASK_WEIGHTS[item.task_priority]
        if item.task_status is TaskStatus.OPEN and item.task_priority is not None
        else 0
    )
    source_authority_score = SOURCE_AUTHORITY_WEIGHTS[item.source_authority]
    persistence_score = (
        PERSISTENT_CRITICAL_WEIGHT
        if item.persistence_type is PersistenceType.PERSISTENT
        and item.risk_level is RiskLevel.CRITICAL
        else 0
    )
    learning_score = min(
        LEARNING_MAX,
        max(
            LEARNING_MIN,
            item.accept_count * LEARNING_ACCEPT_WEIGHT
            - item.reject_count * LEARNING_REJECT_WEIGHT,
        ),
    )
    final_score = float(
        risk_score
        + recency_score
        + entity_score
        + task_score
        + source_authority_score
        + persistence_score
        + learning_score
    )

    explanations = tuple(
        explanation
        for score, explanation in (
            (risk_score, f"{item.risk_level.value} clinical risk"),
            (recency_score, "recent clinical change"),
            (entity_score, f"{item.entity_type.value} context"),
            (task_score, "open follow-up action"),
            (source_authority_score, f"{item.source_authority.value} source"),
            (persistence_score, "persistent critical safety context"),
            (learning_score, "bounded clinic feedback signal"),
        )
        if score > 0
    )
    return ImportanceScore(
        risk_score=risk_score,
        recency_score=recency_score,
        entity_score=entity_score,
        task_score=task_score,
        source_authority_score=source_authority_score,
        persistence_score=persistence_score,
        learning_score=learning_score,
        final_score=final_score,
        explanations=explanations,
    )


def is_highlight_candidate(item: ImportanceInput, score: ImportanceScore) -> bool:
    return (
        item.risk_level is RiskLevel.CRITICAL
        and item.persistence_type is PersistenceType.PERSISTENT
    ) or score.final_score >= HIGHLIGHT_THRESHOLD


def _recency_score(occurred_at: datetime, now: datetime) -> int:
    age = max(now - occurred_at, timedelta(0))
    if age <= timedelta(hours=24):
        return 4
    if age <= timedelta(days=7):
        return 3
    if age <= timedelta(days=30):
        return 1
    return 0
