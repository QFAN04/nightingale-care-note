import json

from app.ai.prompts.scribe import build_scribe_system_prompt
from app.ai.schemas import ScribeResult
from app.models.timeline import InteractionType


def test_prompt_contains_frozen_clinical_safety_rules() -> None:
    prompt = build_scribe_system_prompt(InteractionType.AI_PATIENT)

    assert "only information explicitly supported by the transcript" in prompt
    assert "Do not invent or infer a diagnosis" in prompt
    assert "Do not present a medication statement as a new prescription" in prompt
    assert "source_quote must be copied verbatim" in prompt
    assert "risk_hint is advisory" in prompt
    assert "Do not rank facts" in prompt
    assert "Return only one JSON object" in prompt
    assert "ai_patient" in prompt


def test_prompt_embeds_the_runtime_validation_schema() -> None:
    prompt = build_scribe_system_prompt(InteractionType.DOCTOR_PATIENT)
    compact_schema = json.dumps(
        ScribeResult.model_json_schema(),
        ensure_ascii=False,
        separators=(",", ":"),
    )

    assert compact_schema in prompt
    assert "doctor_patient" in prompt
