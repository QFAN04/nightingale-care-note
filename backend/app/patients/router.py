import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db_session
from app.models.identity import User
from app.patients.schemas import PatientRead
from app.patients.service import get_visible_patient, list_visible_patients
from app.patients.timeline import TimelineEntryRead, list_timeline_entries


router = APIRouter(prefix="/api/v1/patients", tags=["patients"])
DatabaseSession = Annotated[Session, Depends(get_db_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("", response_model=list[PatientRead])
def list_patients(session: DatabaseSession, user: CurrentUser) -> list[PatientRead]:
    return [PatientRead.model_validate(patient) for patient in list_visible_patients(session, user)]


@router.get("/{patient_id}", response_model=PatientRead)
def get_patient(
    patient_id: uuid.UUID,
    session: DatabaseSession,
    user: CurrentUser,
) -> PatientRead:
    patient = get_visible_patient(session, user, patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return PatientRead.model_validate(patient)


@router.get("/{patient_id}/timeline", response_model=list[TimelineEntryRead])
def get_patient_timeline(
    patient_id: uuid.UUID,
    session: DatabaseSession,
    user: CurrentUser,
) -> list[TimelineEntryRead]:
    patient = get_visible_patient(session, user, patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return list_timeline_entries(session, user, patient_id)
