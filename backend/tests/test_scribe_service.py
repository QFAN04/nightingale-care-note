import asyncio
from collections.abc import Sequence
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.ai.service import ScribeProcessingError, process_consult_session
from app.models.base import Base
from app.models.clinical import (
    ClinicalFact,
    Conflict,
    ConflictStatus,
    FactType,
    Highlight,
    HighlightCategory,
    PersistenceType,
    ReviewStatus,
    RiskLevel,
    Task,
    TaskStatus,
)
from app.models.identity import Clinic, Patient, User, UserRole
from app.models.timeline import (
    AuthorRole,
    ConsultSession,
    Entry,
    EntryType,
    InteractionType,
    ProcessingStatus,
    ProvenanceType,
)


class SequenceProvider:
    def __init__(self, responses: Sequence[str]) -> None:
        self.responses = iter(responses)
        self.calls: list[dict[str, str]] = []

    async def generate(self, *, system_prompt: str, transcript: str) -> str:
        self.calls.append({"system_prompt": system_prompt, "transcript": transcript})
        return next(self.responses)


def make_session() -> tuple[Session, ConsultSession]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    db = Session(engine)
    clinic = Clinic(name="Nightingale Test Clinic")
    patient = Patient(
        clinic=clinic,
        external_ref="TEST-001",
        display_name="Sarah Lim",
        date_of_birth=date(1984, 5, 18),
        sex="female",
    )
    patient_user = User(
        clinic=clinic,
        patient=patient,
        display_name="Sarah Lim",
        role=UserRole.PATIENT,
    )
    consult = ConsultSession(
        patient=patient,
        interaction_type=InteractionType.AI_PATIENT,
        occurred_at=datetime(2026, 8, 23, 20, 15, tzinfo=timezone.utc),
        raw_transcript=(
            "Sarah Lim says: I have chest pressure. Call me at +65 9123 4567. "
            "My ID is S1234567D."
        ),
        redacted_transcript="pending",
        created_by=patient_user,
        processing_status=ProcessingStatus.PENDING,
    )
    db.add(consult)
    db.commit()
    return db, consult


def valid_response() -> str:
    return """{
      "summary": "Patient reports chest pressure.",
      "facts": [{
        "fact_type": "symptom",
        "entity_name": "chest pressure",
        "value_text": "present",
        "risk_hint": "high",
        "persistence_hint": "transient",
        "source_quote": "I have chest pressure",
        "extraction_confidence": 0.95
      }],
      "tasks": [{
        "description": "Arrange clinical follow-up.",
        "priority": "high",
        "source_quote": "I have chest pressure"
      }]
    }"""


def medication_response() -> str:
    return """{
      "summary": "Patient reports taking atorvastatin 10 mg.",
      "facts": [{
        "fact_type": "medication",
        "entity_name": "Atorvastatin",
        "value_text": "10 mg",
        "value_number": 10,
        "unit": "mg",
        "risk_hint": "medium",
        "persistence_hint": "persistent",
        "source_quote": "I take Atorvastatin 10 mg",
        "extraction_confidence": 0.96
      }],
      "tasks": []
    }"""


def medication_response_for(
    *, entity_name: str, value_text: str, value_number: int, source_quote: str
) -> str:
    return f"""{{
      "summary": "Patient reports {source_quote}.",
      "facts": [{{
        "fact_type": "medication",
        "entity_name": "{entity_name}",
        "value_text": "{value_text}",
        "value_number": {value_number},
        "unit": "mg",
        "risk_hint": "medium",
        "persistence_hint": "persistent",
        "source_quote": "{source_quote}",
        "extraction_confidence": 0.96
      }}],
      "tasks": []
    }}"""


def add_authoritative_medication(
    db: Session, consult: ConsultSession
) -> tuple[User, ClinicalFact]:
    clinician = User(
        clinic=consult.patient.clinic,
        display_name="Dr Priya Nair",
        role=UserRole.CLINICIAN,
    )
    clinician_entry = Entry(
        patient=consult.patient,
        author=clinician,
        author_role=AuthorRole.CLINICIAN,
        entry_type=EntryType.CLINICIAN_NOTE,
        content="Atorvastatin 20 mg once daily.",
        provenance_type=ProvenanceType.MANUAL,
    )
    authoritative_fact = ClinicalFact(
        patient=consult.patient,
        entry=clinician_entry,
        fact_type=FactType.MEDICATION,
        entity_name="atorvastatin",
        value_text="20 mg once daily",
        value_number=20,
        unit="mg",
        risk_level=RiskLevel.MEDIUM,
        persistence_type=PersistenceType.PERSISTENT,
        source_quote="Atorvastatin 20 mg once daily",
        extraction_confidence=1.0,
        review_status=ReviewStatus.CONFIRMED,
        reviewed_by=clinician,
    )
    db.add(authoritative_fact)
    db.commit()
    return clinician, authoritative_fact


def test_success_redacts_before_provider_and_persists_suggested_records() -> None:
    db, consult = make_session()
    provider = SequenceProvider([valid_response()])

    output = asyncio.run(process_consult_session(db, consult.id, provider))

    db.refresh(consult)
    assert output.summary == "Patient reports chest pressure."
    assert consult.processing_status is ProcessingStatus.COMPLETED
    assert consult.processing_error is None
    assert "Sarah Lim" not in consult.redacted_transcript
    assert "+65 9123 4567" not in consult.redacted_transcript
    assert "S1234567D" not in consult.redacted_transcript
    assert provider.calls[0]["transcript"] == consult.redacted_transcript

    entry = db.scalar(select(Entry))
    fact = db.scalar(select(ClinicalFact))
    task = db.scalar(select(Task))
    assert entry is not None and entry.entry_type is EntryType.AI_PATIENT_SESSION_SUMMARY
    assert fact is not None and fact.review_status is ReviewStatus.SUGGESTED
    assert fact.source_start == consult.redacted_transcript.index(fact.source_quote)
    assert task is not None and task.status is TaskStatus.OPEN
    assert task.source_fact_id == fact.id
    assert set(db.scalars(select(Highlight.category))) == {
        HighlightCategory.RECENT_CHANGE,
        HighlightCategory.OPEN_ACTION,
    }
    db.close()


def test_ai_patient_dose_discrepancy_creates_conflict_visible_in_glance() -> None:
    db, consult = make_session()
    clinician, authoritative_fact = add_authoritative_medication(db, consult)
    consult.raw_transcript = "Patient: I take Atorvastatin 10 mg"
    db.commit()

    asyncio.run(
        process_consult_session(db, consult.id, SequenceProvider([medication_response()]))
    )

    conflict = db.scalar(select(Conflict))
    assert conflict is not None
    assert conflict.status is ConflictStatus.DETECTED
    assert conflict.conflicting_fact.value_text == "10 mg"
    assert conflict.authoritative_fact_id == authoritative_fact.id

    from app.glance.service import build_care_state

    glance = build_care_state(db, consult.patient, clinician)
    assert glance.conflicts[0].details.conflicting_value == "10 mg"
    assert glance.conflicts[0].details.authoritative_value == "20 mg once daily"
    db.close()


@pytest.mark.parametrize(
    ("entity_name", "value_text", "value_number", "source_quote"),
    [
        ("Atorvastatin", "20 mg at night", 20, "I take Atorvastatin 20 mg at night"),
        ("Rosuvastatin", "10 mg", 10, "I take Rosuvastatin 10 mg"),
    ],
)
def test_non_dose_discrepancies_do_not_create_medication_conflicts(
    entity_name: str,
    value_text: str,
    value_number: int,
    source_quote: str,
) -> None:
    db, consult = make_session()
    add_authoritative_medication(db, consult)
    consult.raw_transcript = f"Patient: {source_quote}"
    db.commit()

    response = medication_response_for(
        entity_name=entity_name,
        value_text=value_text,
        value_number=value_number,
        source_quote=source_quote,
    )
    asyncio.run(process_consult_session(db, consult.id, SequenceProvider([response])))

    assert db.scalar(select(func.count()).select_from(Conflict)) == 0
    db.close()


def test_latest_clinician_dose_supersedes_older_authoritative_history() -> None:
    db, consult = make_session()
    clinician, older_fact = add_authoritative_medication(db, consult)
    older_fact.created_at = datetime(2026, 8, 20, tzinfo=timezone.utc)
    latest_entry = Entry(
        patient=consult.patient,
        author=clinician,
        author_role=AuthorRole.CLINICIAN,
        entry_type=EntryType.CLINICIAN_NOTE,
        content="Atorvastatin reduced to 10 mg once daily.",
        provenance_type=ProvenanceType.MANUAL,
    )
    latest_fact = ClinicalFact(
        patient=consult.patient,
        entry=latest_entry,
        fact_type=FactType.MEDICATION,
        entity_name="atorvastatin",
        value_text="10 mg once daily",
        value_number=10,
        unit="mg",
        risk_level=RiskLevel.MEDIUM,
        persistence_type=PersistenceType.PERSISTENT,
        source_quote="Atorvastatin reduced to 10 mg once daily",
        extraction_confidence=1.0,
        review_status=ReviewStatus.CONFIRMED,
        reviewed_by=clinician,
        created_at=datetime(2026, 8, 25, tzinfo=timezone.utc),
    )
    consult.raw_transcript = "Patient: I take Atorvastatin 10 mg"
    db.add(latest_fact)
    db.commit()

    asyncio.run(
        process_consult_session(db, consult.id, SequenceProvider([medication_response()]))
    )

    assert db.scalar(select(func.count()).select_from(Conflict)) == 0
    db.close()


def test_invalid_output_gets_at_most_one_correction_retry() -> None:
    db, consult = make_session()
    provider = SequenceProvider(['{"summary":""}', valid_response()])

    asyncio.run(process_consult_session(db, consult.id, provider))

    assert len(provider.calls) == 2
    assert "previous response failed validation" in provider.calls[1]["system_prompt"]
    assert consult.processing_status is ProcessingStatus.COMPLETED
    db.close()


def test_source_quote_absent_from_transcript_triggers_the_single_retry() -> None:
    db, consult = make_session()
    invented_quote = valid_response().replace(
        "I have chest pressure", "I have crushing chest pain"
    )
    provider = SequenceProvider([invented_quote, valid_response()])

    asyncio.run(process_consult_session(db, consult.id, provider))

    assert len(provider.calls) == 2
    assert consult.processing_status is ProcessingStatus.COMPLETED
    db.close()


def test_second_invalid_output_marks_session_failed_without_partial_records() -> None:
    db, consult = make_session()
    provider = SequenceProvider(['{"summary":""}', '{"summary":""}'])

    with pytest.raises(ScribeProcessingError, match="after one retry"):
        asyncio.run(process_consult_session(db, consult.id, provider))

    assert len(provider.calls) == 2
    assert consult.processing_status is ProcessingStatus.FAILED
    assert consult.processing_error == "AI output failed validation after one retry"
    assert db.scalar(select(func.count()).select_from(Entry)) == 0
    assert db.scalar(select(func.count()).select_from(ClinicalFact)) == 0
    assert db.scalar(select(func.count()).select_from(Task)) == 0
    assert db.scalar(select(func.count()).select_from(Highlight)) == 0
    db.close()


def test_completed_session_cannot_be_processed_twice() -> None:
    db, consult = make_session()
    first_provider = SequenceProvider([valid_response()])
    asyncio.run(process_consult_session(db, consult.id, first_provider))
    second_provider = SequenceProvider([valid_response()])

    with pytest.raises(ScribeProcessingError, match="not pending"):
        asyncio.run(process_consult_session(db, consult.id, second_provider))

    assert second_provider.calls == []
    assert db.scalar(select(func.count()).select_from(Entry)) == 1
    db.close()


def test_highlight_generation_failure_marks_session_failed_atomically(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db, consult = make_session()
    provider = SequenceProvider([valid_response()])

    def fail_generation(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("simulated ranking failure")

    monkeypatch.setattr("app.ai.service.generate_highlight_suggestions", fail_generation)

    with pytest.raises(ScribeProcessingError, match="persistence failed"):
        asyncio.run(process_consult_session(db, consult.id, provider))

    db.refresh(consult)
    assert consult.processing_status is ProcessingStatus.FAILED
    assert consult.processing_error == "AI output persistence failed"
    assert db.scalar(select(func.count()).select_from(Entry)) == 0
    assert db.scalar(select(func.count()).select_from(ClinicalFact)) == 0
    assert db.scalar(select(func.count()).select_from(Task)) == 0
    assert db.scalar(select(func.count()).select_from(Highlight)) == 0
    db.close()
