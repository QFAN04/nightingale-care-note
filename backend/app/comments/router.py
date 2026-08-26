import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.policies import can_access_patient, can_collaborate_on_entry
from app.comments.schemas import CommentCreateRequest, CommentRead, CommentUserRead
from app.comments.service import (
    CommentAlreadyResolvedError,
    CommentNotFoundError,
    create_comment,
    resolve_comment,
)
from app.dependencies import get_current_user, get_db_session
from app.models.audit import Comment
from app.models.identity import User, UserRole
from app.models.timeline import Entry


router = APIRouter(prefix="/api/v1", tags=["comments"])
DatabaseSession = Annotated[Session, Depends(get_db_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post("/entries/{entry_id}/comments", response_model=CommentRead)
def add_comment(
    entry_id: uuid.UUID,
    request: CommentCreateRequest,
    session: DatabaseSession,
    user: CurrentUser,
) -> CommentRead:
    entry = session.get(Entry, entry_id)
    if entry is None or not can_access_patient(user, entry.patient):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entry not found",
        )
    if not can_collaborate_on_entry(user, entry):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Role cannot comment on this entry",
        )
    return _comment_read(create_comment(session, entry, user, request.content))


@router.post("/comments/{comment_id}/resolve", response_model=CommentRead)
def resolve_comment_thread(
    comment_id: uuid.UUID,
    session: DatabaseSession,
    user: CurrentUser,
) -> CommentRead:
    if user.role not in (UserRole.STAFF, UserRole.CLINICIAN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Role cannot resolve internal comments",
        )
    try:
        comment = resolve_comment(session, comment_id, user)
    except CommentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        ) from exc
    except CommentAlreadyResolvedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Comment has already been resolved",
        ) from exc
    return _comment_read(comment)


def _comment_read(comment: Comment) -> CommentRead:
    return CommentRead(
        id=comment.id,
        entry_id=comment.entry_id,
        content=comment.content,
        mentioned_role=comment.mentioned_role,
        author=CommentUserRead(
            id=comment.author.id,
            display_name=comment.author.display_name,
        ),
        resolved=comment.resolved,
        resolved_by=(
            CommentUserRead(
                id=comment.resolved_by.id,
                display_name=comment.resolved_by.display_name,
            )
            if comment.resolved_by is not None
            else None
        ),
        resolved_at=comment.resolved_at,
        created_at=comment.created_at,
    )
