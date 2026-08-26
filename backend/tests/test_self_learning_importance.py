from datetime import date, datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.glance.generation import generate_highlight_suggestions
from app.glance.importance import ImportanceInput, SourceAuthority, score_importance
from app.highlights.service import HighlightReviewAction, review_highlight
from app.models.base import Base
from app.models.clinical import (
    ClinicalFact,
    FactType,
    Highlight,
    HighlightCategory,
    HighlightStatus,
    PersistenceType,
    RiskLevel,
)
from app.models.identity import Clinic, Patient, User, UserRole
from app.models.timeline import AuthorRole, Entry, EntryType, ProvenanceType


NOW = datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc)


def make_patient_with_fact(
    clinic: Clinic,
    *,
    external_ref: str,
    entity_name: str = "chest pressure",
) -> tuple[Patient, ClinicalFact]:
    patient = Patient(
        clinic=clinic,
        external_ref=external_ref,
        display_name=f"Patient {external_ref}",
        date_of_birth=date(1980, 1, 1),
        sex="female",
    )
    entry = Entry(
        patient=patient,
        author_role=AuthorRole.SYSTEM,
        entry_type=EntryType.AI_PATIENT_SESSION_SUMMARY,
        content=f"Synthetic report of {entity_name}.",
        provenance_type=ProvenanceType.SYSTEM,
        created_at=NOW,
        updated_at=NOW,
    )
    fact = ClinicalFact(
        patient=patient,
        entry=entry,
        fact_type=FactType.SYMPTOM,
        entity_name=entity_name,
        value_text="worsening",
        risk_level=RiskLevel.HIGH,
        persistence_type=PersistenceType.TRANSIENT,
        source_quote=f"My {entity_name} is worsening",
        extraction_confidence=0.95,
        created_at=NOW,
    )
    return patient, fact


def test_clinician_acceptance_boosts_similar_content_without_changing_risk() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = Session(engine)
    clinic = Clinic(name="Nightingale Learning Clinic")
    clinician = User(
        clinic=clinic,
        display_name="Dr Learning",
        role=UserRole.CLINICIAN,
    )
    source_patient, source_fact = make_patient_with_fact(
        clinic, external_ref="LEARN-SOURCE"
    )
    source_highlight = Highlight(
        patient=source_patient,
        clinical_fact=source_fact,
        text="Worsening chest pressure",
        category=HighlightCategory.RECENT_CHANGE,
        risk_level=RiskLevel.HIGH,
        risk_reason="High-risk symptom",
        base_score=13,
        learned_score=0,
        status=HighlightStatus.SUGGESTED,
        created_at=NOW,
    )
    before_patient, before_fact = make_patient_with_fact(
        clinic, external_ref="LEARN-BEFORE"
    )
    db.add_all([source_highlight, before_fact])
    db.commit()

    before = generate_highlight_suggestions(db, before_patient.id, now=NOW)[0]
    review_highlight(
        db,
        source_highlight.id,
        clinician,
        HighlightReviewAction.ACCEPT,
        now=NOW,
    )
    after_patient, after_fact = make_patient_with_fact(
        clinic, external_ref="LEARN-AFTER"
    )
    db.add(after_fact)
    db.commit()
    after = generate_highlight_suggestions(db, after_patient.id, now=NOW)[0]

    assert before.learned_score == 0
    assert after.learned_score == 0.25
    assert before.base_score + before.learned_score < after.base_score + after.learned_score
    assert before.risk_level is RiskLevel.HIGH
    assert after.risk_level is RiskLevel.HIGH
    assert before.clinical_fact.risk_level is after.clinical_fact.risk_level

    other_clinic = Clinic(name="Other Learning Clinic")
    other_patient, other_fact = make_patient_with_fact(
        other_clinic, external_ref="LEARN-OTHER-CLINIC"
    )
    db.add(other_fact)
    db.commit()
    other = generate_highlight_suggestions(db, other_patient.id, now=NOW)[0]
    assert other.learned_score == 0
    db.close()


def test_rejection_offsets_acceptance_within_bounds_without_changing_risk() -> None:
    base = ImportanceInput(
        risk_level=RiskLevel.HIGH,
        occurred_at=NOW,
        entity_type=FactType.SYMPTOM,
        persistence_type=PersistenceType.TRANSIENT,
        source_authority=SourceAuthority.AI_SUGGESTION,
    )
    accepted = score_importance(
        ImportanceInput(**{**base.__dict__, "accept_count": 1}),
        now=NOW,
    )
    accepted_then_rejected = score_importance(
        ImportanceInput(
            **{**base.__dict__, "accept_count": 1, "reject_count": 1}
        ),
        now=NOW,
    )
    rejected_only = score_importance(
        ImportanceInput(**{**base.__dict__, "reject_count": 1}),
        now=NOW,
    )

    assert accepted.learning_score == 0.25
    assert accepted_then_rejected.learning_score == pytest.approx(0.05)
    assert rejected_only.learning_score == 0
    assert accepted_then_rejected.risk_score == accepted.risk_score == 7
