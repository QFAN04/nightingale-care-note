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


def test_diff_returns_explainable_version_segments() -> None:
    client, session, story = make_client()
    entry_id = fixed_uuid(10)
    headers = {"X-Demo-User-ID": str(story.clinician_user.id)}
    original = session.get(Entry, entry_id)
    assert original is not None
    updated = original.content + " Review again in four weeks."
    patch_response = client.patch(
        f"/api/v1/entries/{entry_id}",
        headers=headers,
        json={"content": updated, "expected_version": 1},
    )
    assert patch_response.status_code == 200

    response = client.get(
        f"/api/v1/entries/{entry_id}/diff",
        params={"from_version": 1, "to_version": 2},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["from_version"] == 1
    assert body["to_version"] == 2
    assert any(
        part["type"] == "unchanged" and "Penicillin allergy" in part["text"]
        for part in body["diff"]
    )
    assert any(
        part["type"] == "added" and "Review again in four weeks." in part["text"]
        for part in body["diff"]
    )
    close_client(session)


def test_revert_appends_new_full_snapshot_without_deleting_history() -> None:
    client, session, story = make_client()
    entry_id = fixed_uuid(10)
    headers = {"X-Demo-User-ID": str(story.clinician_user.id)}
    entry = session.get(Entry, entry_id)
    assert entry is not None
    original_content = entry.content
    edit_response = client.patch(
        f"/api/v1/entries/{entry_id}",
        headers=headers,
        json={"content": "Temporary edit to be reverted.", "expected_version": 1},
    )
    assert edit_response.status_code == 200

    response = client.post(
        f"/api/v1/entries/{entry_id}/revert",
        headers=headers,
        json={"target_version": 1, "expected_version": 2},
    )

    assert response.status_code == 200
    assert response.json() == {
        "entry_id": str(entry_id),
        "new_version": 3,
        "reverted_from": 1,
    }
    session.refresh(entry)
    versions = list(
        session.scalars(
            select(EntryVersion)
            .where(EntryVersion.entry_id == entry_id)
            .order_by(EntryVersion.version_number)
        )
    )
    audit = session.scalar(
        select(AuditEvent).where(
            AuditEvent.resource_id == entry_id,
            AuditEvent.action == "entry.reverted",
        )
    )
    assert entry.content == original_content
    assert entry.current_version == 3
    assert [version.version_number for version in versions] == [1, 2, 3]
    assert versions[1].content == "Temporary edit to be reverted."
    assert versions[2].content == original_content
    assert versions[2].change_reason is ChangeReason.REVERT
    assert versions[2].source_version == 2
    assert versions[2].reverted_from_version == 1
    assert audit is not None
    assert audit.event_metadata == {
        "from_version": 2,
        "to_version": 3,
        "reverted_from": 1,
    }
    assert original_content not in str(audit.event_metadata)
    close_client(session)
