from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.dependencies import get_db_session
from app.main import app
from app.models.audit import AuditEvent, FeedbackAction, ImportanceFeedback
from app.models.base import Base
from app.models.clinical import Highlight, HighlightStatus
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


def test_clinician_accepts_suggestion_with_feedback_and_metadata_only_audit() -> None:
    client, session, story = make_client()
    highlight_id = fixed_uuid(41)

    response = client.post(
        f"/api/v1/highlights/{highlight_id}/accept",
        headers={"X-Demo-User-ID": str(story.clinician_user.id)},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "accepted"
    assert body["reviewed_by"]["display_name"] == "Dr Priya Nair"
    assert body["reviewed_at"] is not None

    highlight = session.get(Highlight, highlight_id)
    feedback = session.scalar(
        select(ImportanceFeedback).where(ImportanceFeedback.highlight_id == highlight_id)
    )
    audit = session.scalar(
        select(AuditEvent).where(AuditEvent.resource_id == highlight_id)
    )
    assert highlight is not None and highlight.status is HighlightStatus.ACCEPTED
    assert feedback is not None
    assert feedback.action is FeedbackAction.ACCEPT
    assert feedback.ranking_delta == 0.25
    assert feedback.entity_key == "chest pressure"
    assert audit is not None
    assert audit.action == "highlight.accepted"
    assert audit.event_metadata == {"from_status": "suggested", "to_status": "accepted"}
    assert "source_quote" not in str(audit.event_metadata)
    close_client(session)


def test_clinician_rejects_suggestion_and_cannot_review_it_twice() -> None:
    client, session, story = make_client()
    highlight_id = fixed_uuid(42)
    headers = {"X-Demo-User-ID": str(story.clinician_user.id)}

    first = client.post(f"/api/v1/highlights/{highlight_id}/reject", headers=headers)
    second = client.post(f"/api/v1/highlights/{highlight_id}/accept", headers=headers)

    assert first.status_code == 200
    assert first.json()["status"] == "rejected"
    assert second.status_code == 409
    feedback = list(
        session.scalars(
            select(ImportanceFeedback).where(
                ImportanceFeedback.highlight_id == highlight_id
            )
        )
    )
    assert len(feedback) == 1
    assert feedback[0].action is FeedbackAction.REJECT
    assert feedback[0].ranking_delta == -0.2
    close_client(session)


def test_non_clinician_cannot_review_highlight() -> None:
    client, session, story = make_client()
    highlight_id = fixed_uuid(41)

    response = client.post(
        f"/api/v1/highlights/{highlight_id}/accept",
        headers={"X-Demo-User-ID": str(story.staff_user.id)},
    )

    assert response.status_code == 403
    highlight = session.get(Highlight, highlight_id)
    assert highlight is not None and highlight.status is HighlightStatus.SUGGESTED
    assert session.scalar(
        select(ImportanceFeedback).where(ImportanceFeedback.highlight_id == highlight_id)
    ) is None
    close_client(session)
