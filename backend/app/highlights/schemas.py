import uuid
from datetime import datetime

from pydantic import BaseModel


class HighlightReviewerRead(BaseModel):
    id: uuid.UUID
    display_name: str


class HighlightReviewRead(BaseModel):
    id: uuid.UUID
    status: str
    reviewed_by: HighlightReviewerRead
    reviewed_at: datetime
