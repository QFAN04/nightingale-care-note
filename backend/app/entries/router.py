import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.auth.policies import can_access_patient, can_edit_entry, can_view_entry
from app.dependencies import get_current_user, get_db_session
from app.entries.schemas import (
    EntryDiffPart,
    EntryDiffRead,
    EntryRevertRead,
    EntryRevertRequest,
    EntryUpdateRead,
    EntryUpdateRequest,
)
from app.entries.service import (
    EntryVersionConflictError,
    EntryVersionNotFoundError,
    get_entry_diff,
    revert_entry,
    update_entry,
)
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


@router.get("/{entry_id}/diff", response_model=EntryDiffRead)
def diff_entry(
    entry_id: uuid.UUID,
    session: DatabaseSession,
    user: CurrentUser,
    from_version: Annotated[int, Query(ge=1)],
    to_version: Annotated[int, Query(ge=1)],
) -> EntryDiffRead:
    entry = _visible_entry(session, user, entry_id)
    if not can_view_entry(user, entry):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Role cannot view this entry",
        )
    try:
        parts = get_entry_diff(session, entry.id, from_version, to_version)
    except EntryVersionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entry version not found",
        ) from exc
    return EntryDiffRead(
        from_version=from_version,
        to_version=to_version,
        diff=[EntryDiffPart.model_validate(part) for part in parts],
    )


@router.post("/{entry_id}/revert", response_model=EntryRevertRead)
def revert_entry_version(
    entry_id: uuid.UUID,
    request: EntryRevertRequest,
    session: DatabaseSession,
    user: CurrentUser,
) -> EntryRevertRead | JSONResponse:
    entry = _visible_entry(session, user, entry_id)
    if not can_edit_entry(user, entry):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Role cannot edit this entry type",
        )
    try:
        version = revert_entry(
            session,
            entry,
            user,
            request.target_version,
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
    except EntryVersionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entry version not found",
        ) from exc
    return EntryRevertRead(
        entry_id=entry.id,
        new_version=version.version_number,
        reverted_from=request.target_version,
    )


def _visible_entry(session: Session, user: User, entry_id: uuid.UUID) -> Entry:
    entry = session.get(Entry, entry_id)
    if entry is None or not can_access_patient(user, entry.patient):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entry not found",
        )
    return entry
