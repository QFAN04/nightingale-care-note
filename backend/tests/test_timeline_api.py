from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.dependencies import get_db_session
from app.main import app
from app.models.base import Base
from app.seed.sarah_lim import seed_sarah_lim


def make_client() -> tuple[TestClient, Session, object]:
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

    def override_session():
        yield session

    app.dependency_overrides[get_db_session] = override_session
    return TestClient(app), session, story


def test_clinician_timeline_is_newest_first_and_keeps_provenance() -> None:
    client, session, story = make_client()
    expected_session_id = str(story.august_doctor_session.id)

    response = client.get(
        f"/api/v1/patients/{story.patient.id}/timeline",
        headers={"X-Demo-User-ID": str(story.clinician_user.id)},
    )

    app.dependency_overrides.clear()
    session.close()
    assert response.status_code == 200
    timeline = response.json()
    assert len(timeline) == 5
    assert [item["occurred_at"] for item in timeline] == sorted(
        [item["occurred_at"] for item in timeline], reverse=True
    )
    assert timeline[0]["entry_type"] == "ai_doctor_consult_summary"
    assert timeline[0]["provenance_id"] == expected_session_id


def test_patient_timeline_hides_internal_and_raw_ai_entries() -> None:
    client, session, story = make_client()

    response = client.get(
        f"/api/v1/patients/{story.patient.id}/timeline",
        headers={"X-Demo-User-ID": str(story.patient_user.id)},
    )

    app.dependency_overrides.clear()
    session.close()
    assert response.status_code == 200
    assert response.json() == []
