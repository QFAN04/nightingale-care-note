import hashlib

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.dependencies import get_db_session
from app.main import app
from app.models.audit import AuditEvent, ChangeReason, EntryVersion
from app.models.base import Base
from app.models.timeline import Entry
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


def test_patch_creates_immutable_full_snapshot_and_metadata_only_audit() -> None:
    client, session, story = make_client()
    entry_id = fixed_uuid(10)
    updated_content = "Penicillin allergy confirmed. Continue atorvastatin 20 mg daily."

    response = client.patch(
        f"/api/v1/entries/{entry_id}",
        headers={"X-Demo-User-ID": str(story.clinician_user.id)},
        json={"content": updated_content, "expected_version": 1},
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": str(entry_id),
        "content": updated_content,
        "current_version": 2,
    }

    entry = session.get(Entry, entry_id)
    versions = list(
        session.scalars(
            select(EntryVersion)
            .where(EntryVersion.entry_id == entry_id)
            .order_by(EntryVersion.version_number)
        )
    )
    audit = session.scalar(
        select(AuditEvent).where(
            AuditEvent.resource_type == "entry",
            AuditEvent.resource_id == entry_id,
            AuditEvent.action == "entry.updated",
        )
    )

    assert entry is not None
    assert entry.content == updated_content
    assert entry.current_version == 2
    assert [version.version_number for version in versions] == [1, 2]
    assert versions[0].content != versions[1].content
    assert versions[1].content == updated_content
    assert versions[1].source_version == 1
    assert versions[1].change_reason is ChangeReason.MANUAL_EDIT
    assert versions[1].content_hash == hashlib.sha256(
        updated_content.encode("utf-8")
    ).hexdigest()
    assert audit is not None
    assert audit.event_metadata == {"from_version": 1, "to_version": 2}
    assert updated_content not in str(audit.event_metadata)
    close_client(session)


def test_patch_returns_frozen_version_conflict_contract_without_mutation() -> None:
    client, session, story = make_client()
    entry_id = fixed_uuid(10)
    entry = session.get(Entry, entry_id)
    assert entry is not None
    original_content = entry.content

    response = client.patch(
        f"/api/v1/entries/{entry_id}",
        headers={"X-Demo-User-ID": str(story.clinician_user.id)},
        json={"content": "Stale client edit", "expected_version": 2},
    )

    assert response.status_code == 409
    assert response.json() == {
        "error": "version_conflict",
        "current_version": 1,
        "expected_version": 2,
    }
    session.refresh(entry)
    assert entry.content == original_content
    assert entry.current_version == 1
    assert session.scalar(
        select(AuditEvent).where(AuditEvent.resource_id == entry_id)
    ) is None
    close_client(session)


def test_patch_enforces_entry_type_ownership() -> None:
    client, session, story = make_client()
    staff_entry_id = fixed_uuid(13)

    response = client.patch(
        f"/api/v1/entries/{staff_entry_id}",
        headers={"X-Demo-User-ID": str(story.clinician_user.id)},
        json={"content": "Clinician must not edit this.", "expected_version": 1},
    )

    assert response.status_code == 403
    entry = session.get(Entry, staff_entry_id)
    assert entry is not None and entry.current_version == 1
    close_client(session)
