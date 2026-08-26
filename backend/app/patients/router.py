import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.policies import allowed_scribe_interaction
from app.ai.dependencies import get_scribe_provider
from app.ai.providers.base import ScribeProvider
from app.ai.schemas import ScribeRequest, ScribeResult
from app.ai.service import ScribeProcessingError, process_consult_session
from app.dependencies import get_current_user, get_db_session
from app.entries.schemas import ManualEntryCreateRequest
from app.entries.service import create_manual_entry
from app.models.identity import User, UserRole
from app.models.timeline import ConsultSession, ProcessingStatus
from app.patients.schemas import PatientRead
from app.patients.service import get_visible_patient, list_visible_patients
from app.patients.timeline import TimelineEntryRead, list_timeline_entries


router = APIRouter(prefix="/api/v1/patients", tags=["patients"])
DatabaseSession = Annotated[Session, Depends(get_db_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]
ConfiguredScribeProvider = Annotated[ScribeProvider, Depends(get_scribe_provider)]


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


@router.post(
    "/{patient_id}/entries",
    response_model=TimelineEntryRead,
    status_code=status.HTTP_201_CREATED,
)
def add_patient_entry(
    patient_id: uuid.UUID,
    request: ManualEntryCreateRequest,
    session: DatabaseSession,
    user: CurrentUser,
) -> TimelineEntryRead:
    patient = get_visible_patient(session, user, patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    if user.role not in (UserRole.STAFF, UserRole.CLINICIAN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Role cannot create manual notes",
        )
    entry = create_manual_entry(session, patient, user, request.content)
    return TimelineEntryRead(
        id=entry.id,
        patient_id=entry.patient_id,
        author_id=entry.author_id,
        author_role=entry.author_role,
        entry_type=entry.entry_type,
        content=entry.content,
        occurred_at=entry.created_at,
        provenance_type=entry.provenance_type,
        provenance_id=entry.provenance_id,
        current_version=entry.current_version,
    )


@router.post("/{patient_id}/scribe", response_model=ScribeResult)
async def run_patient_scribe(
    patient_id: uuid.UUID,
    request: ScribeRequest,
    session: DatabaseSession,
    user: CurrentUser,
    provider: ConfiguredScribeProvider,
) -> ScribeResult:
    patient = get_visible_patient(session, user, patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    allowed_interaction = allowed_scribe_interaction(user)
    if allowed_interaction is None or request.interaction_type is not allowed_interaction:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Role cannot create this scribe interaction",
        )

    consult = ConsultSession(
        patient=patient,
        interaction_type=request.interaction_type,
        occurred_at=datetime.now(timezone.utc),
        raw_transcript=request.raw_text,
        redacted_transcript="pending",
        created_by=user,
        processing_status=ProcessingStatus.PENDING,
    )
    session.add(consult)
    session.commit()

    try:
        return await process_consult_session(session, consult.id, provider)
    except ScribeProcessingError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
