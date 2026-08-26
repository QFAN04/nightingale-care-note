import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.auth.policies import highlight_scope_filter
from app.models.audit import AuditEvent, FeedbackAction, ImportanceFeedback
from app.models.clinical import ClinicalFact, Highlight, HighlightStatus
from app.models.identity import User


class HighlightReviewAction(str, enum.Enum):
    ACCEPT = "accept"
    REJECT = "reject"


class HighlightNotFoundError(Exception):
    pass


class HighlightAlreadyReviewedError(Exception):
    pass


def review_highlight(
    db: Session,
    highlight_id: uuid.UUID,
    reviewer: User,
    action: HighlightReviewAction,
    *,
    now: datetime | None = None,
) -> Highlight:
    highlight = db.scalar(
        select(Highlight)
        .options(joinedload(Highlight.clinical_fact))
        .where(
            Highlight.id == highlight_id,
            highlight_scope_filter(reviewer),
        )
    )
    if highlight is None:
        raise HighlightNotFoundError
    if highlight.status is not HighlightStatus.SUGGESTED:
        raise HighlightAlreadyReviewedError

    reviewed_at = now or datetime.now(timezone.utc)
    target_status = (
        HighlightStatus.ACCEPTED
        if action is HighlightReviewAction.ACCEPT
        else HighlightStatus.REJECTED
    )
    feedback_action = (
        FeedbackAction.ACCEPT
        if action is HighlightReviewAction.ACCEPT
        else FeedbackAction.REJECT
    )
    ranking_delta = 0.25 if action is HighlightReviewAction.ACCEPT else -0.2

    highlight.status = target_status
    highlight.reviewed_by = reviewer
    highlight.reviewed_at = reviewed_at
    db.add_all(
        [
            ImportanceFeedback(
                patient_id=highlight.patient_id,
                actor=reviewer,
                highlight=highlight,
                entity_key=highlight.clinical_fact.entity_name.casefold(),
                action=feedback_action,
                ranking_delta=ranking_delta,
                created_at=reviewed_at,
            ),
            AuditEvent(
                clinic_id=reviewer.clinic_id,
                patient_id=highlight.patient_id,
                actor=reviewer,
                action=f"highlight.{target_status.value}",
                resource_type="highlight",
                resource_id=highlight.id,
                event_metadata={
                    "from_status": HighlightStatus.SUGGESTED.value,
                    "to_status": target_status.value,
                },
                created_at=reviewed_at,
            ),
        ]
    )
    db.commit()
    return highlight
