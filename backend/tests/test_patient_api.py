import uuid
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.dependencies import get_db_session
from app.main import app
from app.models.base import Base
from app.models.identity import Clinic, Patient, User, UserRole
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


def test_clinician_lists_only_patients_in_own_clinic() -> None:
    client, session, story = make_client()
    other_clinic = Clinic(name="Other Clinic")
    other_patient = Patient(
        clinic=other_clinic,
        external_ref="OTHER-001",
        display_name="Other Patient",
        date_of_birth=date(1990, 1, 1),
        sex="female",
    )
    session.add_all([other_clinic, other_patient])
    session.commit()

    response = client.get(
        "/api/v1/patients",
        headers={"X-Demo-User-ID": str(story.clinician_user.id)},
    )

    app.dependency_overrides.clear()
    session.close()
    assert response.status_code == 200
    assert [patient["display_name"] for patient in response.json()] == ["Sarah Lim"]


def test_patient_can_read_own_record() -> None:
    client, session, story = make_client()

    response = client.get(
        f"/api/v1/patients/{story.patient.id}",
        headers={"X-Demo-User-ID": str(story.patient_user.id)},
    )

    app.dependency_overrides.clear()
    session.close()
    assert response.status_code == 200
    assert response.json()["external_ref"] == "PAT-001"


def test_cross_clinic_patient_is_not_disclosed() -> None:
    client, session, story = make_client()
    other_clinic = Clinic(name="Other Clinic")
    other_patient = Patient(
        id=uuid.uuid4(),
        clinic=other_clinic,
        external_ref="OTHER-001",
        display_name="Other Patient",
        date_of_birth=date(1990, 1, 1),
        sex="female",
    )
    session.add_all([other_clinic, other_patient])
    session.commit()

    response = client.get(
        f"/api/v1/patients/{other_patient.id}",
        headers={"X-Demo-User-ID": str(story.clinician_user.id)},
    )

    app.dependency_overrides.clear()
    session.close()
    assert response.status_code == 404
