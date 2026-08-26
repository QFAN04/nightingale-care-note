"""Atomic orchestration for redaction, extraction, validation, and persistence."""

import uuid
from datetime import datetime, timezone

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.ai.prompts.scribe import build_scribe_system_prompt
from app.ai.providers.base import ScribeProvider
from app.ai.redaction import redact_phi
from app.ai.schemas import ScribeResult
from app.glance.generation import generate_highlight_suggestions
from app.models.clinical import (
    ClinicalFact,
    ReviewStatus,
    Task,
    TaskStatus,
)
from app.models.identity import UserRole
from app.models.timeline import (
    AuthorRole,
    ConsultSession,
    Entry,
    EntryType,
    InteractionType,
    ProcessingStatus,
    ProvenanceType,
)


class ScribeProcessingError(RuntimeError):
    """Raised when a consult cannot be safely converted into records."""


class SourceQuoteError(ValueError):
    """Raised when the model cites text that is absent from the transcript."""


ENTRY_TYPE_BY_INTERACTION = {
    InteractionType.DOCTOR_PATIENT: EntryType.AI_DOCTOR_CONSULT_SUMMARY,
    InteractionType.NURSE_PATIENT: EntryType.AI_NURSE_CONSULT_SUMMARY,
    InteractionType.AI_PATIENT: EntryType.AI_PATIENT_SESSION_SUMMARY,
}


async def process_consult_session(
    db: Session,
    consult_session_id: uuid.UUID,
    provider: ScribeProvider,
) -> ScribeResult:
    consult = db.get(ConsultSession, consult_session_id)
    if consult is None:
        raise ScribeProcessingError("consult session was not found")
    if consult.processing_status is not ProcessingStatus.PENDING:
        raise ScribeProcessingError("consult session is not pending")

    known_names = {consult.patient.display_name}
    known_names.update(
        user.display_name
        for user in consult.patient.users
        if user.role is UserRole.PATIENT
    )
    redaction = redact_phi(consult.raw_transcript, known_names=known_names)
    consult.redacted_transcript = redaction.text
    consult.processing_status = ProcessingStatus.PENDING
    consult.processing_error = None
    db.commit()

    base_prompt = build_scribe_system_prompt(consult.interaction_type)
    output: ScribeResult | None = None
    for attempt in range(2):
        prompt = base_prompt
        if attempt == 1:
            prompt += (
                "\nYour previous response failed validation. Correct the structure and "
                "ensure every source_quote is copied verbatim from the transcript."
            )
        try:
            raw_output = await provider.generate(
                system_prompt=prompt,
                transcript=consult.redacted_transcript,
            )
        except Exception as exc:
            consult.processing_status = ProcessingStatus.FAILED
            consult.processing_error = "AI provider request failed"
            db.commit()
            raise ScribeProcessingError("AI provider request failed") from exc

        try:
            candidate = ScribeResult.model_validate_json(raw_output)
            _validate_source_quotes(candidate, consult.redacted_transcript)
            output = candidate
            break
        except (ValidationError, SourceQuoteError):
            if attempt == 1:
                consult.processing_status = ProcessingStatus.FAILED
                consult.processing_error = "AI output failed validation after one retry"
                db.commit()
                raise ScribeProcessingError(
                    "AI output failed validation after one retry"
                )

    if output is None:  # Defensive guard; both loop exits assign or raise.
        raise ScribeProcessingError("AI output processing ended unexpectedly")

    try:
        _persist_validated_output(db, consult, output)
    except Exception as exc:
        db.rollback()
        failed_consult = db.get(ConsultSession, consult_session_id)
        if failed_consult is not None:
            failed_consult.processing_status = ProcessingStatus.FAILED
            failed_consult.processing_error = "AI output persistence failed"
            db.commit()
        raise ScribeProcessingError("AI output persistence failed") from exc
    return output


def _persist_validated_output(
    db: Session,
    consult: ConsultSession,
    output: ScribeResult,
) -> None:
    entry = Entry(
        patient=consult.patient,
        author_role=AuthorRole.SYSTEM,
        entry_type=ENTRY_TYPE_BY_INTERACTION[consult.interaction_type],
        content=output.summary,
        provenance_type=ProvenanceType.CONSULT_SESSION,
        consult_session=consult,
    )
    db.add(entry)

    facts_by_quote: dict[str, ClinicalFact] = {}
    for extracted in output.facts:
        source_start = consult.redacted_transcript.index(extracted.source_quote)
        fact = ClinicalFact(
            patient=consult.patient,
            entry=entry,
            fact_type=extracted.fact_type,
            entity_name=extracted.entity_name,
            value_text=extracted.value_text,
            value_number=extracted.value_number,
            unit=extracted.unit,
            risk_level=extracted.risk_hint,
            persistence_type=extracted.persistence_hint,
            source_quote=extracted.source_quote,
            source_start=source_start,
            source_end=source_start + len(extracted.source_quote),
            extraction_confidence=extracted.extraction_confidence,
            review_status=ReviewStatus.SUGGESTED,
        )
        db.add(fact)
        facts_by_quote.setdefault(extracted.source_quote, fact)

    for suggested in output.tasks:
        db.add(
            Task(
                patient=consult.patient,
                source_entry=entry,
                source_fact=facts_by_quote.get(suggested.source_quote),
                description=suggested.description,
                priority=suggested.priority,
                status=TaskStatus.OPEN,
                assigned_role=UserRole.STAFF,
            )
        )

    db.flush()
    generate_highlight_suggestions(
        db,
        consult.patient_id,
        now=datetime.now(timezone.utc),
    )
    consult.processing_status = ProcessingStatus.COMPLETED
    consult.processing_error = None
    db.commit()


def _validate_source_quotes(output: ScribeResult, transcript: str) -> None:
    quotes = [fact.source_quote for fact in output.facts]
    quotes.extend(task.source_quote for task in output.tasks)
    if any(quote not in transcript for quote in quotes):
        raise SourceQuoteError("AI output contains a source quote absent from transcript")
