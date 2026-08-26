import pytest
from pydantic import ValidationError

from app.ai.schemas import ScribeOutput
from app.models.clinical import FactType, PersistenceType, RiskLevel, TaskPriority


def valid_payload() -> dict[str, object]:
    return {
        "summary": "Patient reports worsening chest pressure over three days.",
        "facts": [
            {
                "fact_type": "symptom",
                "entity_name": "chest pressure",
                "value_text": "worsening",
                "risk_hint": "high",
                "persistence_hint": "transient",
                "source_quote": "the chest pressure felt stronger than before",
                "extraction_confidence": 0.92,
            }
        ],
        "tasks": [
            {
                "description": "Arrange staff follow-up for the reported symptom.",
                "priority": "high",
                "source_quote": "the chest pressure felt stronger than before",
            }
        ],
    }


def test_scribe_output_parses_strict_supported_structure() -> None:
    output = ScribeOutput.model_validate(valid_payload())

    assert output.facts[0].fact_type is FactType.SYMPTOM
    assert output.facts[0].risk_hint is RiskLevel.HIGH
    assert output.facts[0].persistence_hint is PersistenceType.TRANSIENT
    assert output.tasks[0].priority is TaskPriority.HIGH


def test_scribe_output_forbids_uncontracted_fields() -> None:
    payload = valid_payload()
    payload["diagnosis"] = "unstable angina"

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ScribeOutput.model_validate(payload)


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_fact_confidence_must_be_between_zero_and_one(confidence: float) -> None:
    payload = valid_payload()
    payload["facts"][0]["extraction_confidence"] = confidence  # type: ignore[index]

    with pytest.raises(ValidationError):
        ScribeOutput.model_validate(payload)


def test_fact_requires_a_value_and_nonempty_source_quote() -> None:
    payload = valid_payload()
    fact = payload["facts"][0]  # type: ignore[index]
    fact["value_text"] = None
    fact["source_quote"] = "   "

    with pytest.raises(ValidationError):
        ScribeOutput.model_validate(payload)
