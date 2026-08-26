from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.dependencies import get_db_session
from app.main import app
from app.models.base import Base
from app.seed.sarah_lim import seed_sarah_lim


def test_demo_identity_header_is_required_and_resolves_a_database_user() -> None:
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

    missing = client.get("/api/v1/patients")
    invalid = client.get(
        "/api/v1/patients", headers={"X-Demo-User-ID": "not-a-uuid"}
    )
    clinician = client.get(
        "/api/v1/patients",
        headers={"X-Demo-User-ID": str(story.clinician_user.id)},
    )

    assert missing.status_code == 401
    assert invalid.status_code == 401
    assert clinician.status_code == 200
    assert clinician.json()[0]["display_name"] == "Sarah Lim"
    app.dependency_overrides.clear()
    session.close()
