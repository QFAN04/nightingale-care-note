import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.audit import Comment
from app.models.identity import Patient, User, UserRole
from app.models.timeline import Entry


class CommentNotFoundError(Exception):
    pass


class CommentAlreadyResolvedError(Exception):
    pass


def create_comment(db: Session, entry: Entry, author: User, content: str) -> Comment:
    comment = Comment(
        entry=entry,
        author=author,
        content=content,
        mentioned_role=_mentioned_role(content),
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


def resolve_comment(
    db: Session,
    comment_id: uuid.UUID,
    actor: User,
) -> Comment:
    comment = db.scalar(
        select(Comment)
        .join(Entry, Comment.entry_id == Entry.id)
        .join(Patient, Entry.patient_id == Patient.id)
        .options(joinedload(Comment.author), joinedload(Comment.resolved_by))
        .where(Comment.id == comment_id, Patient.clinic_id == actor.clinic_id)
    )
    if comment is None:
        raise CommentNotFoundError
    if comment.resolved:
        raise CommentAlreadyResolvedError

    comment.resolved = True
    comment.resolved_by = actor
    comment.resolved_at = datetime.now(timezone.utc)
    db.commit()
    return comment


def _mentioned_role(content: str) -> UserRole | None:
    if re.search(r"(?i)(?<!\w)@clinician\b", content):
        return UserRole.CLINICIAN
    return None
