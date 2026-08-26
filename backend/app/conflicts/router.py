"""Clinician-only conflict resolution endpoint."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.conflicts.schemas import (
    ConflictResolutionRead,
    ConflictResolveRequest,
    ConflictResolverRead,
)
from app.conflicts.service import (
    ConflictAlreadyClosedError,
    ConflictNotFoundError,
    resolve_conflict,
)
from app.dependencies import get_current_user, get_db_session
from app.models.identity import User, UserRole


router = APIRouter(prefix="/api/v1/conflicts", tags=["conflicts"])
DatabaseSession = Annotated[Session, Depends(get_db_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post("/{conflict_id}/resolve", response_model=ConflictResolutionRead)
def resolve_detected_conflict(
    conflict_id: uuid.UUID,
    request: ConflictResolveRequest,
    session: DatabaseSession,
    user: CurrentUser,
) -> ConflictResolutionRead:
    if user.role is not UserRole.CLINICIAN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinicians can resolve conflicts",
        )
    try:
        conflict = resolve_conflict(
            session,
            conflict_id,
            user,
            request.resolution_note,
        )
    except ConflictNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conflict not found",
        ) from exc
    except ConflictAlreadyClosedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflict has already been resolved or dismissed",
        ) from exc

    return ConflictResolutionRead(
        id=conflict.id,
        status=conflict.status,
        resolution_note=conflict.resolution or "",
        resolved_by=ConflictResolverRead(
            id=user.id,
            display_name=user.display_name,
        ),
        resolved_at=conflict.resolved_at,
    )
