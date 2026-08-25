from datetime import date

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.base import Base
from app.models.identity import Clinic, Patient, User, UserRole


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as database_session:
        yield database_session


def test_patient_and_patient_user_share_clinic_scope(session: Session) -> None:
    """Catches a patient record or patient identity escaping its clinic scope."""
    clinic = Clinic(name="Nightingale Central Clinic")
    patient = Patient(
        clinic=clinic,
        external_ref="PAT-001",
        display_name="Sarah Lim",
        date_of_birth=date(1984, 5, 18),
        sex="female",
    )
    user = User(
        clinic=clinic,
        patient=patient,
        display_name="Sarah Lim",
        role=UserRole.PATIENT,
    )
    session.add_all([clinic, patient, user])
    session.commit()

    assert patient.clinic_id == clinic.id
    assert user.clinic_id == clinic.id
    assert user.patient_id == patient.id


def test_patient_role_requires_patient_mapping(session: Session) -> None:
    """Catches creation of a patient identity that can access no owned record."""
    clinic = Clinic(name="Nightingale Central Clinic")
    session.add_all(
        [clinic, User(clinic=clinic, display_name="Unmapped Patient", role=UserRole.PATIENT)]
    )

    with pytest.raises(IntegrityError):
        session.commit()


def test_staff_role_rejects_patient_mapping(session: Session) -> None:
    """Catches a staff identity being granted a patient's ownership scope."""
    clinic = Clinic(name="Nightingale Central Clinic")
    patient = Patient(
        clinic=clinic,
        external_ref="PAT-001",
        display_name="Sarah Lim",
        date_of_birth=date(1984, 5, 18),
        sex="female",
    )
    session.add_all(
        [
            clinic,
            patient,
            User(
                clinic=clinic,
                patient=patient,
                display_name="Amanda Wong",
                role=UserRole.STAFF,
            ),
        ]
    )

    with pytest.raises(IntegrityError):
        session.commit()
