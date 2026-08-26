from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.dependencies import get_db_session
from app.main import app
from app.models.audit import AuditEvent
from app.models.base import Base
from app.models.clinical import Conflict, ConflictStatus
from app.models.identity import Clinic, User, UserRole
from app.seed.sarah_lim import fixed_uuid, seed_sarah_lim


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


def test_clinician_resolves_conflict_and_glance_hides_it() -> None:
    client, session, story = make_client()
    conflict_id = fixed_uuid(51)
    headers = {"X-Demo-User-ID": str(story.clinician_user.id)}
    resolution_note = "Medication dose verified as 20 mg."

    before = client.get(
        f"/api/v1/patients/{story.patient.id}/glance", headers=headers
    )
    response = client.post(
        f"/api/v1/conflicts/{conflict_id}/resolve",
        headers=headers,
        json={"resolution_note": resolution_note},
    )
    after = client.get(
        f"/api/v1/patients/{story.patient.id}/glance", headers=headers
    )

    assert len(before.json()["conflicts"]) == 1
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(conflict_id)
    assert body["status"] == "resolved"
    assert body["resolution_note"] == resolution_note
    assert body["resolved_by"]["display_name"] == "Dr Priya Nair"
    assert body["resolved_at"] is not None
    assert after.json()["conflicts"] == []

    conflict = session.get(Conflict, conflict_id)
    audit = session.scalar(
        select(AuditEvent).where(AuditEvent.resource_id == conflict_id)
    )
    assert conflict is not None and conflict.status is ConflictStatus.RESOLVED
    assert conflict.resolution == resolution_note
    assert conflict.resolved_by_id == story.clinician_user.id
    assert audit is not None
    assert audit.action == "conflict.resolved"
    assert audit.event_metadata == {
        "from_status": "detected",
        "to_status": "resolved",
    }
    assert resolution_note not in str(audit.event_metadata)
    close_client(session)


def test_conflict_cannot_be_resolved_twice() -> None:
    client, session, story = make_client()
    conflict_id = fixed_uuid(51)
    headers = {"X-Demo-User-ID": str(story.clinician_user.id)}
    payload = {"resolution_note": "Medication dose verified as 20 mg."}

    first = client.post(
        f"/api/v1/conflicts/{conflict_id}/resolve", headers=headers, json=payload
    )
    second = client.post(
        f"/api/v1/conflicts/{conflict_id}/resolve", headers=headers, json=payload
    )

    assert first.status_code == 200
    assert second.status_code == 409
    close_client(session)


def test_patient_staff_and_admin_cannot_resolve_conflict() -> None:
    client, session, story = make_client()
    conflict_id = fixed_uuid(51)
    payload = {"resolution_note": "Unauthorized resolution."}

    for user in (story.patient_user, story.staff_user, story.admin_user):
        response = client.post(
            f"/api/v1/conflicts/{conflict_id}/resolve",
            headers={"X-Demo-User-ID": str(user.id)},
            json=payload,
        )
        assert response.status_code == 403

    conflict = session.get(Conflict, conflict_id)
    assert conflict is not None and conflict.status is ConflictStatus.DETECTED
    close_client(session)


def test_cross_clinic_conflict_is_not_disclosed() -> None:
    client, session, _story = make_client()
    other_clinic = Clinic(name="Other Clinic")
    other_clinician = User(
        clinic=other_clinic,
        display_name="Other Clinician",
        role=UserRole.CLINICIAN,
    )
    session.add(other_clinician)
    session.commit()

    response = client.post(
        f"/api/v1/conflicts/{fixed_uuid(51)}/resolve",
        headers={"X-Demo-User-ID": str(other_clinician.id)},
        json={"resolution_note": "Must not reach another clinic."},
    )

    assert response.status_code == 404
    close_client(session)
