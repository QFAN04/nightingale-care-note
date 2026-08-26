import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.policies import patient_scope_filter
from app.models.identity import Patient, User


def list_visible_patients(session: Session, user: User) -> list[Patient]:
    statement = select(Patient).where(patient_scope_filter(user))
    return list(session.scalars(statement.order_by(Patient.display_name)))


def get_visible_patient(session: Session, user: User, patient_id: uuid.UUID) -> Patient | None:
    statement = select(Patient).where(
        Patient.id == patient_id,
        patient_scope_filter(user),
    )
    return session.scalar(statement)
