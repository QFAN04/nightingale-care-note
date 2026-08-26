import uuid

from pydantic import BaseModel, Field


class EntryUpdateRequest(BaseModel):
    content: str
    expected_version: int = Field(ge=1)


class EntryUpdateRead(BaseModel):
    id: uuid.UUID
    content: str
    current_version: int
