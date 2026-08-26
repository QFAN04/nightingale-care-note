import uuid
from datetime import datetime

from pydantic import BaseModel


class GlancePatient(BaseModel):
    id: uuid.UUID
    external_ref: str
    display_name: str


class GlanceSource(BaseModel):
    entry_id: uuid.UUID
    entry_type: str
    occurred_at: datetime
    provenance_type: str
    provenance_id: uuid.UUID | None = None
    source_quote: str
    source_start: int | None = None
    source_end: int | None = None


class GlanceDetails(BaseModel):
    entity_name: str | None = None
    value_text: str | None = None
    value_number: float | None = None
    unit: str | None = None
    fact_review_status: str | None = None
    task_priority: str | None = None
    task_status: str | None = None
    authoritative_value: str | None = None
    conflicting_value: str | None = None


class GlanceItem(BaseModel):
    id: uuid.UUID
    title: str
    category: str
    status: str
    risk_level: str
    risk_reason: str
    source: GlanceSource
    details: GlanceDetails


class CareStateResponse(BaseModel):
    patient: GlancePatient
    generated_at: datetime
    critical: list[GlanceItem]
    recent_changes: list[GlanceItem]
    open_actions: list[GlanceItem]
    conflicts: list[GlanceItem]
