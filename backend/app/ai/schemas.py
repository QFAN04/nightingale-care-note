"""Strict validation boundary for untrusted AI scribe output."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.models.clinical import FactType, PersistenceType, RiskLevel, TaskPriority


NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class StrictAIModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExtractedClinicalFact(StrictAIModel):
    fact_type: FactType
    entity_name: NonEmptyText
    value_text: NonEmptyText | None = None
    value_number: float | None = None
    unit: NonEmptyText | None = None
    risk_hint: RiskLevel
    persistence_hint: PersistenceType
    source_quote: NonEmptyText
    extraction_confidence: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def require_extracted_value(self) -> "ExtractedClinicalFact":
        if self.value_text is None and self.value_number is None:
            raise ValueError("an extracted fact must include a text or numeric value")
        return self


class SuggestedTask(StrictAIModel):
    description: NonEmptyText
    priority: TaskPriority
    source_quote: NonEmptyText


class ScribeResult(StrictAIModel):
    summary: NonEmptyText
    facts: list[ExtractedClinicalFact] = Field(default_factory=list, max_length=50)
    tasks: list[SuggestedTask] = Field(default_factory=list, max_length=20)
