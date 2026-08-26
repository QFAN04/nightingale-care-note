from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.auth.policies import (
    can_access_patient,
    can_edit_entry,
    can_view_entry,
)
from app.models.base import Base
from app.models.identity import Clinic, User, UserRole
from app.models.timeline import Entry
from app.seed.sarah_lim import fixed_uuid, seed_sarah_lim


def make_session() -> tuple[Session, object]:
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    session = Session(engine)
    return session, seed_sarah_lim(session)


def test_staff_cannot_edit_clinician_note() -> None:
    session, story = make_session()
    clinician_note = session.get(Entry, fixed_uuid(10))

    assert clinician_note is not None
    assert can_edit_entry(story.staff_user, clinician_note) is False
    assert can_edit_entry(story.clinician_user, clinician_note) is True
    session.close()


def test_clinician_cannot_edit_staff_note() -> None:
    session, story = make_session()
    staff_note = session.get(Entry, fixed_uuid(13))

    assert staff_note is not None
    assert can_edit_entry(story.clinician_user, staff_note) is False
    assert can_edit_entry(story.staff_user, staff_note) is True
    assert can_edit_entry(story.admin_user, staff_note) is False
    session.close()


def test_patient_cannot_view_raw_ai_note() -> None:
    session, story = make_session()
    raw_ai_note = session.get(Entry, fixed_uuid(12))

    assert raw_ai_note is not None
    assert can_view_entry(story.patient_user, raw_ai_note) is False
    assert can_view_entry(story.clinician_user, raw_ai_note) is True
    session.close()


def test_cross_clinic_patient_access_is_denied() -> None:
    session, story = make_session()
    other_clinic = Clinic(name="Other Clinic")
    other_clinician = User(
        clinic=other_clinic,
        display_name="Other Clinician",
        role=UserRole.CLINICIAN,
    )
    session.add_all([other_clinic, other_clinician])
    session.commit()

    assert can_access_patient(other_clinician, story.patient) is False
    assert can_access_patient(story.clinician_user, story.patient) is True
    session.close()
