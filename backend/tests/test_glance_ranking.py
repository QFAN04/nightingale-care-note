from datetime import datetime, timedelta, timezone

import pytest

from app.glance.importance import (
    ImportanceInput,
    SourceAuthority,
    score_importance,
)
from app.models.clinical import (
    FactType,
    PersistenceType,
    RiskLevel,
    TaskPriority,
    TaskStatus,
)


NOW = datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc)


def candidate(**overrides: object) -> ImportanceInput:
    values: dict[str, object] = {
        "risk_level": RiskLevel.LOW,
        "occurred_at": NOW,
        "entity_type": FactType.SYMPTOM,
        "persistence_type": PersistenceType.TRANSIENT,
        "source_authority": SourceAuthority.AI_SUGGESTION,
    }
    values.update(overrides)
    return ImportanceInput(**values)  # type: ignore[arg-type]


def test_old_persistent_critical_allergy_outranks_recent_low_risk_note() -> None:
    allergy = score_importance(
        candidate(
            risk_level=RiskLevel.CRITICAL,
            occurred_at=NOW - timedelta(days=120),
            entity_type=FactType.ALLERGY,
            persistence_type=PersistenceType.PERSISTENT,
            source_authority=SourceAuthority.CLINICIAN_MANUAL,
        ),
        now=NOW,
    )
    recent_note = score_importance(candidate(), now=NOW)

    assert allergy.final_score == 22
    assert recent_note.final_score == 7
    assert allergy.final_score > recent_note.final_score


def test_recent_high_risk_symptom_rises_above_older_equivalent() -> None:
    recent = score_importance(
        candidate(risk_level=RiskLevel.HIGH, occurred_at=NOW - timedelta(hours=12)),
        now=NOW,
    )
    older = score_importance(
        candidate(risk_level=RiskLevel.HIGH, occurred_at=NOW - timedelta(days=31)),
        now=NOW,
    )

    assert recent.recency_score == 4
    assert older.recency_score == 0
    assert recent.final_score == older.final_score + 4


def test_open_task_adds_priority_but_completed_task_does_not() -> None:
    open_task = score_importance(
        candidate(task_status=TaskStatus.OPEN, task_priority=TaskPriority.HIGH),
        now=NOW,
    )
    completed_task = score_importance(
        candidate(task_status=TaskStatus.COMPLETED, task_priority=TaskPriority.HIGH),
        now=NOW,
    )

    assert open_task.task_score == 5
    assert completed_task.task_score == 0
    assert open_task.final_score == completed_task.final_score + 5


def test_persistent_critical_fact_never_loses_its_persistence_weight() -> None:
    score = score_importance(
        candidate(
            risk_level=RiskLevel.CRITICAL,
            occurred_at=NOW - timedelta(days=500),
            entity_type=FactType.ALLERGY,
            persistence_type=PersistenceType.PERSISTENT,
        ),
        now=NOW,
    )

    assert score.recency_score == 0
    assert score.persistence_score == 4


@pytest.mark.parametrize(
    ("accept_count", "reject_count", "expected"),
    [(100, 0, 3.0), (4, 0, 1.0), (0, 100, 0.0), (8, 5, 1.0)],
)
def test_learning_bonus_is_bounded(
    accept_count: int,
    reject_count: int,
    expected: float,
) -> None:
    score = score_importance(
        candidate(accept_count=accept_count, reject_count=reject_count),
        now=NOW,
    )

    assert score.learning_score == expected
    assert 0 <= score.learning_score <= 3
