import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.dependencies import get_db_session
from app.main import app
from app.models.audit import Comment
from app.models.base import Base
from app.models.identity import UserRole
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


def test_staff_adds_comment_with_lightweight_clinician_mention() -> None:
    client, session, story = make_client()
    entry_id = fixed_uuid(13)
    content = "@clinician Please review before tomorrow's appointment."

    response = client.post(
        f"/api/v1/entries/{entry_id}/comments",
        headers={"X-Demo-User-ID": str(story.staff_user.id)},
        json={"content": content},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["content"] == content
    assert body["mentioned_role"] == "clinician"
    assert body["author"]["display_name"] == "Amanda Wong"
    assert body["resolved"] is False
    comment = session.get(Comment, uuid.UUID(body["id"]))
    assert comment is not None
    assert comment.mentioned_role is UserRole.CLINICIAN
    close_client(session)


def test_patient_and_admin_cannot_create_internal_comments() -> None:
    client, session, story = make_client()
    entry_id = fixed_uuid(13)

    patient_response = client.post(
        f"/api/v1/entries/{entry_id}/comments",
        headers={"X-Demo-User-ID": str(story.patient_user.id)},
        json={"content": "Patient must not enter the internal thread."},
    )
    admin_response = client.post(
        f"/api/v1/entries/{entry_id}/comments",
        headers={"X-Demo-User-ID": str(story.admin_user.id)},
        json={"content": "Admin is read-only."},
    )

    assert patient_response.status_code == 403
    assert admin_response.status_code == 403
    close_client(session)


def test_clinician_resolves_comment_and_cannot_resolve_it_twice() -> None:
    client, session, story = make_client()
    comment_id = fixed_uuid(60)
    headers = {"X-Demo-User-ID": str(story.clinician_user.id)}

    first = client.post(f"/api/v1/comments/{comment_id}/resolve", headers=headers)
    second = client.post(f"/api/v1/comments/{comment_id}/resolve", headers=headers)

    assert first.status_code == 200
    body = first.json()
    assert body["id"] == str(comment_id)
    assert body["resolved"] is True
    assert body["resolved_by"]["display_name"] == "Dr Priya Nair"
    assert body["resolved_at"] is not None
    assert second.status_code == 409
    comment = session.get(Comment, comment_id)
    assert comment is not None
    assert comment.resolved is True
    assert comment.resolved_by_id == story.clinician_user.id
    close_client(session)
