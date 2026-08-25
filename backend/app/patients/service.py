import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.identity import Patient, User, UserRole


def list_visible_patients(session: Session, user: User) -> list[Patient]:
    statement = select(Patient)
    if user.role is UserRole.PATIENT:
        statement = statement.where(Patient.id == user.patient_id)
    else:
        statement = statement.where(Patient.clinic_id == user.clinic_id)
    return list(session.scalars(statement.order_by(Patient.display_name)))


def get_visible_patient(session: Session, user: User, patient_id: uuid.UUID) -> Patient | None:
    statement = select(Patient).where(Patient.id == patient_id)
    if user.role is UserRole.PATIENT:
        statement = statement.where(Patient.id == user.patient_id)
    else:
        statement = statement.where(Patient.clinic_id == user.clinic_id)
    return session.scalar(statement)
