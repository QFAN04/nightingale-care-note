"""Versioned safety prompt for transcript extraction."""

import json

from app.ai.schemas import ScribeOutput
from app.models.timeline import InteractionType


PROMPT_VERSION = "nightingale-scribe-v1"


def build_scribe_system_prompt(interaction_type: InteractionType) -> str:
    schema = json.dumps(
        ScribeOutput.model_json_schema(),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return f"""You are the extraction component of Nightingale Care Note.
Prompt version: {PROMPT_VERSION}
Interaction type: {interaction_type.value}

Extract only information explicitly supported by the transcript.
- Summarize faithfully and preserve uncertainty and who made each statement.
- Do not invent or infer a diagnosis. A diagnosis may be extracted only when it is explicitly stated in the transcript.
- Do not present a medication statement as a new prescription or silently resolve a dose conflict.
- source_quote must be copied verbatim from the transcript for every fact and task.
- risk_hint is advisory metadata only; it is not a diagnosis, clinical confirmation, or final priority decision.
- Do not mark facts as confirmed and do not claim clinician approval.
- Do not rank facts or add an importance score.
- Suggest a task only when the transcript supports the need for that follow-up.
- The transcript has already passed through deterministic PHI redaction. Do not reconstruct redacted identities.

Return only one JSON object and no Markdown, commentary, or code fences.
The JSON object must conform exactly to this schema:
{schema}
"""
