import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.policies import can_review_highlights
from app.dependencies import get_current_user, get_db_session
from app.highlights.schemas import HighlightReviewRead, HighlightReviewerRead
from app.highlights.service import (
    HighlightAlreadyReviewedError,
    HighlightNotFoundError,
    HighlightReviewAction,
    review_highlight,
)
from app.models.identity import User


router = APIRouter(prefix="/api/v1/highlights", tags=["highlights"])
DatabaseSession = Annotated[Session, Depends(get_db_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post("/{highlight_id}/accept", response_model=HighlightReviewRead)
def accept_highlight(
    highlight_id: uuid.UUID,
    session: DatabaseSession,
    user: CurrentUser,
) -> HighlightReviewRead:
    return _review(highlight_id, HighlightReviewAction.ACCEPT, session, user)


@router.post("/{highlight_id}/reject", response_model=HighlightReviewRead)
def reject_highlight(
    highlight_id: uuid.UUID,
    session: DatabaseSession,
    user: CurrentUser,
) -> HighlightReviewRead:
    return _review(highlight_id, HighlightReviewAction.REJECT, session, user)


def _review(
    highlight_id: uuid.UUID,
    action: HighlightReviewAction,
    session: Session,
    user: User,
) -> HighlightReviewRead:
    if not can_review_highlights(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinicians can review highlight suggestions",
        )
    try:
        highlight = review_highlight(session, highlight_id, user, action)
    except HighlightNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Highlight not found",
        ) from exc
    except HighlightAlreadyReviewedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Highlight has already been reviewed",
        ) from exc

    return HighlightReviewRead(
        id=highlight.id,
        status=highlight.status.value,
        reviewed_by=HighlightReviewerRead(
            id=user.id,
            display_name=user.display_name,
        ),
        reviewed_at=highlight.reviewed_at,
    )
