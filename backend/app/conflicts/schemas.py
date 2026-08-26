"""API contracts for clinician conflict resolution."""

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.models.clinical import ConflictStatus


ResolutionNote = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=2000),
]


class ConflictResolveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resolution_note: ResolutionNote


class ConflictResolverRead(BaseModel):
    id: uuid.UUID
    display_name: str


class ConflictResolutionRead(BaseModel):
    id: uuid.UUID
    status: ConflictStatus
    resolution_note: str
    resolved_by: ConflictResolverRead
    resolved_at: datetime
