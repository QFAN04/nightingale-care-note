import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db_session
from app.glance.schemas import CareStateResponse
from app.glance.service import build_care_state
from app.models.identity import User
from app.patients.service import get_visible_patient


router = APIRouter(prefix="/api/v1/patients", tags=["glance"])
DatabaseSession = Annotated[Session, Depends(get_db_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("/{patient_id}/glance", response_model=CareStateResponse)
def get_patient_glance(
    patient_id: uuid.UUID,
    session: DatabaseSession,
    user: CurrentUser,
) -> CareStateResponse:
    patient = get_visible_patient(session, user, patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return build_care_state(session, patient, user)
