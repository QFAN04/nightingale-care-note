from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.dependencies import get_db_session
from app.main import app
from app.models.base import Base
from app.models.identity import Clinic, User, UserRole
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


def close_client(session: Session) -> None:
    app.dependency_overrides.clear()
    session.close()


def test_clinician_gets_optimized_care_state_without_raw_scores() -> None:
    client, session, story = make_client()

    response = client.get(
        f"/api/v1/patients/{story.patient.id}/glance",
        headers={"X-Demo-User-ID": str(story.clinician_user.id)},
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "patient",
        "generated_at",
        "critical",
        "recent_changes",
        "open_actions",
        "conflicts",
    }
    assert body["patient"]["display_name"] == "Sarah Lim"
    assert body["critical"][0]["title"] == "Penicillin allergy"
    assert body["recent_changes"][0]["title"] == "Worsening chest pressure"
    assert "persistent safety context" in body["critical"][0]["risk_reason"]
    assert body["open_actions"][0]["details"]["task_priority"] == "high"
    assert body["conflicts"][0]["details"]["authoritative_value"] == "20 mg once daily"
    assert body["conflicts"][0]["details"]["conflicting_value"] == "10 mg"
    assert body["recent_changes"][0]["source"]["source_quote"] in (
        "Last night the chest pressure felt stronger than before."
    )
    serialized = response.text
    assert "base_score" not in serialized
    assert "learned_score" not in serialized
    assert "final_score" not in serialized
    assert "ai_suggestions" not in serialized
    close_client(session)


def test_patient_glance_hides_unreviewed_internal_context() -> None:
    client, session, story = make_client()

    response = client.get(
        f"/api/v1/patients/{story.patient.id}/glance",
        headers={"X-Demo-User-ID": str(story.patient_user.id)},
    )

    assert response.status_code == 200
    body = response.json()
    assert [item["title"] for item in body["critical"]] == ["Penicillin allergy"]
    assert body["recent_changes"] == []
    assert body["open_actions"] == []
    assert body["conflicts"] == []
    close_client(session)


def test_glance_keeps_cross_clinic_patient_undisclosed() -> None:
    client, session, story = make_client()
    other_clinic = Clinic(name="Other Clinic")
    other_clinician = User(
        clinic=other_clinic,
        display_name="Other Clinician",
        role=UserRole.CLINICIAN,
    )
    session.add_all([other_clinic, other_clinician])
    session.commit()

    response = client.get(
        f"/api/v1/patients/{story.patient.id}/glance",
        headers={"X-Demo-User-ID": str(other_clinician.id)},
    )

    assert response.status_code == 404
    close_client(session)
