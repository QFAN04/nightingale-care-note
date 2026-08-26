"""Explainable, non-destructive clinical data decay classification."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from app.models.clinical import (
    FactType,
    PersistenceType,
    ReviewStatus,
    RiskLevel,
)


RECENT_FULL_FIDELITY_WINDOW = timedelta(days=30)


class DecayDecision(StrEnum):
    NEVER_DECAY = "never_decay"
    FULL_FIDELITY = "full_fidelity"
    COMPRESSION_CANDIDATE = "compression_candidate"


@dataclass(frozen=True)
class DecayInput:
    fact_type: FactType
    risk_level: RiskLevel
    persistence_type: PersistenceType
    review_status: ReviewStatus
    created_at: datetime

    def __post_init__(self) -> None:
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")


def evaluate_decay(item: DecayInput, *, now: datetime) -> DecayDecision:
    """Classify retention without mutating or deleting the source fact."""
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    if item.fact_type is FactType.ALLERGY:
        return DecayDecision.NEVER_DECAY
    if (
        item.risk_level is RiskLevel.CRITICAL
        and item.review_status is ReviewStatus.CONFIRMED
    ):
        return DecayDecision.NEVER_DECAY

    age = max(now - item.created_at, timedelta(0))
    if age <= RECENT_FULL_FIDELITY_WINDOW:
        return DecayDecision.FULL_FIDELITY
    if (
        item.risk_level is RiskLevel.LOW
        and item.persistence_type is PersistenceType.TRANSIENT
    ):
        return DecayDecision.COMPRESSION_CANDIDATE
    return DecayDecision.FULL_FIDELITY
