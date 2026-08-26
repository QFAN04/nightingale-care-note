import uuid
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ManualEntryCreateRequest(BaseModel):
    content: str

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        content = value.strip()
        if not content:
            raise ValueError("content must not be blank")
        return content


class EntryUpdateRequest(BaseModel):
    content: str
    expected_version: int = Field(ge=1)


class EntryUpdateRead(BaseModel):
    id: uuid.UUID
    content: str
    current_version: int


class EntryDiffPart(BaseModel):
    type: Literal["unchanged", "added", "removed"]
    text: str


class EntryDiffRead(BaseModel):
    from_version: int
    to_version: int
    diff: list[EntryDiffPart]


class EntryRevertRequest(BaseModel):
    target_version: int = Field(ge=1)
    expected_version: int = Field(ge=1)


class EntryRevertRead(BaseModel):
    entry_id: uuid.UUID
    new_version: int
    reverted_from: int
