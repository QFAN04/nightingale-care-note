import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.dependencies import get_db_session
from app.main import app
from app.models.base import Base
from app.models.timeline import Entry, ProvenanceType
from app.seed.sarah_lim import seed_sarah_lim


def test_every_glance_item_resolves_to_exact_timeline_evidence() -> None:
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
    client = TestClient(app)
    headers = {"X-Demo-User-ID": str(story.clinician_user.id)}

    glance_response = client.get(
        f"/api/v1/patients/{story.patient.id}/glance", headers=headers
    )
    timeline_response = client.get(
        f"/api/v1/patients/{story.patient.id}/timeline", headers=headers
    )

    assert glance_response.status_code == 200
    assert timeline_response.status_code == 200
    timeline_ids = {item["id"] for item in timeline_response.json()}
    glance = glance_response.json()
    items = [
        item
        for section in ("critical", "recent_changes", "open_actions", "conflicts")
        for item in glance[section]
    ]

    for item in items:
        source = item["source"]
        assert source["entry_id"] in timeline_ids
        entry = session.get(Entry, uuid.UUID(source["entry_id"]))
        assert entry is not None
        evidence_text = (
            entry.consult_session.redacted_transcript
            if entry.provenance_type is ProvenanceType.CONSULT_SESSION
            else entry.content
        )
        assert source["source_quote"] in evidence_text

    app.dependency_overrides.clear()
    session.close()
