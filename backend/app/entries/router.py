import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.auth.policies import can_access_patient, can_edit_entry
from app.dependencies import get_current_user, get_db_session
from app.entries.schemas import EntryUpdateRead, EntryUpdateRequest
from app.entries.service import EntryVersionConflictError, update_entry
from app.models.identity import User
from app.models.timeline import Entry


router = APIRouter(prefix="/api/v1/entries", tags=["entries"])
DatabaseSession = Annotated[Session, Depends(get_db_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.patch("/{entry_id}", response_model=EntryUpdateRead)
def patch_entry(
    entry_id: uuid.UUID,
    request: EntryUpdateRequest,
    session: DatabaseSession,
    user: CurrentUser,
) -> EntryUpdateRead | JSONResponse:
    entry = session.get(Entry, entry_id)
    if entry is None or not can_access_patient(user, entry.patient):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entry not found",
        )
    if not can_edit_entry(user, entry):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Role cannot edit this entry type",
        )

    try:
        updated = update_entry(
            session,
            entry,
            user,
            request.content,
            request.expected_version,
        )
    except EntryVersionConflictError as exc:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": "version_conflict",
                "current_version": exc.current_version,
                "expected_version": exc.expected_version,
            },
        )

    return EntryUpdateRead(
        id=updated.id,
        content=updated.content,
        current_version=updated.current_version,
    )
