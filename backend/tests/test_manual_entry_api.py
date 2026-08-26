import uuid
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.dependencies import get_db_session
from app.main import app
from app.models.audit import AuditEvent, ChangeReason, EntryVersion
from app.models.base import Base
from app.models.identity import Clinic, Patient
from app.models.timeline import AuthorRole, Entry, EntryType, ProvenanceType
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


def test_staff_creates_manual_note_with_initial_snapshot_and_metadata_only_audit() -> None:
    client, session, story = make_client()
    content = "Patient confirmed that chest pressure is improving today."

    response = client.post(
        f"/api/v1/patients/{story.patient.id}/entries",
        headers={"X-Demo-User-ID": str(story.staff_user.id)},
        json={"content": content},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["content"] == content
    assert body["author_id"] == str(story.staff_user.id)
    assert body["author_role"] == "staff"
    assert body["entry_type"] == "staff_note"
    assert body["provenance_type"] == "manual"
    assert body["provenance_id"] is None
    assert body["current_version"] == 1

    entry_id = uuid.UUID(body["id"])
    entry = session.get(Entry, entry_id)
    version = session.scalar(
        select(EntryVersion).where(EntryVersion.entry_id == entry_id)
    )
    audit = session.scalar(
        select(AuditEvent).where(
            AuditEvent.resource_id == entry_id,
            AuditEvent.action == "entry.created",
        )
    )
    assert entry is not None
    assert entry.author_role is AuthorRole.STAFF
    assert entry.entry_type is EntryType.STAFF_NOTE
    assert entry.provenance_type is ProvenanceType.MANUAL
    assert version is not None
    assert version.version_number == 1
    assert version.content == content
    assert version.change_reason is ChangeReason.CREATED
    assert version.source_version is None
    assert audit is not None
    assert audit.event_metadata == {"version": 1, "entry_type": "staff_note"}
    assert content not in str(audit.event_metadata)
    close_client(session)


def test_clinician_entry_type_is_derived_from_the_authenticated_role() -> None:
    client, session, story = make_client()

    response = client.post(
        f"/api/v1/patients/{story.patient.id}/entries",
        headers={"X-Demo-User-ID": str(story.clinician_user.id)},
        json={"content": "Reviewed symptoms and documented the follow-up plan."},
    )

    assert response.status_code == 201
    assert response.json()["entry_type"] == "clinician_note"
    assert response.json()["author_role"] == "clinician"
    close_client(session)


def test_patient_and_admin_cannot_create_manual_notes() -> None:
    client, session, story = make_client()

    for user in (story.patient_user, story.admin_user):
        response = client.post(
            f"/api/v1/patients/{story.patient.id}/entries",
            headers={"X-Demo-User-ID": str(user.id)},
            json={"content": "This must not be created."},
        )
        assert response.status_code == 403

    assert session.scalar(
        select(Entry).where(Entry.content == "This must not be created.")
    ) is None
    close_client(session)


def test_manual_note_does_not_disclose_a_cross_clinic_patient() -> None:
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

    response = client.post(
        f"/api/v1/patients/{other_patient.id}/entries",
        headers={"X-Demo-User-ID": str(story.staff_user.id)},
        json={"content": "Cross-clinic note"},
    )

    assert response.status_code == 404
    close_client(session)


def test_manual_note_rejects_blank_content() -> None:
    client, session, story = make_client()

    response = client.post(
        f"/api/v1/patients/{story.patient.id}/entries",
        headers={"X-Demo-User-ID": str(story.staff_user.id)},
        json={"content": "   "},
    )

    assert response.status_code == 422
    close_client(session)
