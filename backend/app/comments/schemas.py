import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.identity import UserRole


class CommentCreateRequest(BaseModel):
    content: str


class CommentUserRead(BaseModel):
    id: uuid.UUID
    display_name: str


class CommentRead(BaseModel):
    id: uuid.UUID
    entry_id: uuid.UUID
    content: str
    mentioned_role: UserRole | None
    author: CommentUserRead
    resolved: bool
    resolved_by: CommentUserRead | None
    resolved_at: datetime | None
    created_at: datetime
