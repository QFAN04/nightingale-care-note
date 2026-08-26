from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.ai.dependencies import get_scribe_provider
from app.ai.providers.fake import FakeScribeProvider
from app.dependencies import get_db_session
from app.main import app
from app.models.base import Base
from app.models.timeline import ConsultSession, Entry, ProcessingStatus
from app.seed.sarah_lim import seed_sarah_lim


VALID_RESPONSE = """{
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
  "tasks": []
}"""


def make_client() -> tuple[TestClient, Session, object, FakeScribeProvider]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    session = Session(engine)
    story = seed_sarah_lim(session)
    provider = FakeScribeProvider(raw_response=VALID_RESPONSE)

    def override_session():
        yield session

    app.dependency_overrides[get_db_session] = override_session
    app.dependency_overrides[get_scribe_provider] = lambda: provider
    return TestClient(app), session, story, provider


def close_client(session: Session) -> None:
    app.dependency_overrides.clear()
    session.close()


def test_clinician_runs_frozen_scribe_endpoint_and_gets_structured_result() -> None:
    client, session, story, provider = make_client()
    entries_before = session.scalar(select(func.count()).select_from(Entry))

    response = client.post(
        f"/api/v1/patients/{story.patient.id}/scribe",
        headers={"X-Demo-User-ID": str(story.clinician_user.id)},
        json={
            "interaction_type": "doctor_patient",
            "raw_text": "Doctor: Tell me more. Sarah Lim: I have chest pressure.",
        },
    )

    assert response.status_code == 200
    assert response.json()["summary"] == "Patient reports chest pressure."
    assert response.json()["facts"][0]["risk_hint"] == "high"
    assert len(provider.calls) == 1
    assert "Sarah Lim" not in provider.calls[0]["transcript"]
    assert session.scalar(select(func.count()).select_from(Entry)) == entries_before + 1
    consult = session.scalars(
        select(ConsultSession).order_by(ConsultSession.created_at.desc())
    ).first()
    assert consult is not None and consult.processing_status is ProcessingStatus.COMPLETED
    close_client(session)


def test_role_cannot_submit_a_different_interaction_type() -> None:
    client, session, story, provider = make_client()

    response = client.post(
        f"/api/v1/patients/{story.patient.id}/scribe",
        headers={"X-Demo-User-ID": str(story.patient_user.id)},
        json={
            "interaction_type": "doctor_patient",
            "raw_text": "I have chest pressure.",
        },
    )

    assert response.status_code == 403
    assert provider.calls == []
    close_client(session)


def test_admin_remains_read_only_for_scribe() -> None:
    client, session, story, provider = make_client()

    response = client.post(
        f"/api/v1/patients/{story.patient.id}/scribe",
        headers={"X-Demo-User-ID": str(story.admin_user.id)},
        json={
            "interaction_type": "doctor_patient",
            "raw_text": "I have chest pressure.",
        },
    )

    assert response.status_code == 403
    assert provider.calls == []
    close_client(session)
