from datetime import datetime, timedelta, timezone

from app.glance.decay_policy import DecayDecision, DecayInput, evaluate_decay
from app.models.clinical import (
    FactType,
    PersistenceType,
    ReviewStatus,
    RiskLevel,
)


NOW = datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc)


def candidate(**overrides: object) -> DecayInput:
    values: dict[str, object] = {
        "fact_type": FactType.SYMPTOM,
        "risk_level": RiskLevel.LOW,
        "persistence_type": PersistenceType.TRANSIENT,
        "review_status": ReviewStatus.SUGGESTED,
        "created_at": NOW - timedelta(days=120),
    }
    values.update(overrides)
    return DecayInput(**values)  # type: ignore[arg-type]


def test_allergy_never_becomes_a_compression_candidate() -> None:
    decision = evaluate_decay(
        candidate(
            fact_type=FactType.ALLERGY,
            created_at=NOW - timedelta(days=1000),
        ),
        now=NOW,
    )

    assert decision is DecayDecision.NEVER_DECAY


def test_confirmed_critical_fact_never_decays() -> None:
    decision = evaluate_decay(
        candidate(
            risk_level=RiskLevel.CRITICAL,
            review_status=ReviewStatus.CONFIRMED,
            created_at=NOW - timedelta(days=1000),
        ),
        now=NOW,
    )

    assert decision is DecayDecision.NEVER_DECAY


def test_recent_fact_keeps_full_fidelity() -> None:
    decision = evaluate_decay(
        candidate(created_at=NOW - timedelta(days=30)),
        now=NOW,
    )

    assert decision is DecayDecision.FULL_FIDELITY


def test_old_low_risk_transient_fact_is_only_marked_as_candidate() -> None:
    decision = evaluate_decay(candidate(), now=NOW)

    assert decision is DecayDecision.COMPRESSION_CANDIDATE


def test_old_medium_risk_or_persistent_context_keeps_full_fidelity() -> None:
    medium = evaluate_decay(
        candidate(risk_level=RiskLevel.MEDIUM),
        now=NOW,
    )
    persistent = evaluate_decay(
        candidate(persistence_type=PersistenceType.PERSISTENT),
        now=NOW,
    )

    assert medium is DecayDecision.FULL_FIDELITY
    assert persistent is DecayDecision.FULL_FIDELITY
