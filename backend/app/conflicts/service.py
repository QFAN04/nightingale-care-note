"""Detect narrowly scoped medication dose conflicts from structured facts."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.clinical import (
    ClinicalFact,
    Conflict,
    ConflictStatus,
    ConflictType,
    FactType,
    ReviewStatus,
)
from app.models.identity import UserRole
from app.models.audit import AuditEvent
from app.models.identity import Patient, User
from app.models.timeline import AuthorRole


_DOSE_PATTERN = re.compile(
    r"(?<![\w.])(?P<amount>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>mcg|μg|ug|mg|g|ml)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Dose:
    amount: float
    unit: str


class ConflictNotFoundError(Exception):
    pass


class ConflictAlreadyClosedError(Exception):
    pass


def resolve_conflict(
    db: Session,
    conflict_id: uuid.UUID,
    resolver: User,
    resolution_note: str,
    *,
    now: datetime | None = None,
) -> Conflict:
    conflict = db.scalar(
        select(Conflict).where(
            Conflict.id == conflict_id,
            Conflict.patient.has(Patient.clinic_id == resolver.clinic_id),
        )
    )
    if conflict is None:
        raise ConflictNotFoundError
    if conflict.status is not ConflictStatus.DETECTED:
        raise ConflictAlreadyClosedError

    resolved_at = now or datetime.now(timezone.utc)
    conflict.status = ConflictStatus.RESOLVED
    conflict.resolution = resolution_note
    conflict.resolved_by = resolver
    conflict.resolved_at = resolved_at
    db.add(
        AuditEvent(
            clinic_id=resolver.clinic_id,
            patient_id=conflict.patient_id,
            actor=resolver,
            action="conflict.resolved",
            resource_type="conflict",
            resource_id=conflict.id,
            event_metadata={
                "from_status": ConflictStatus.DETECTED.value,
                "to_status": ConflictStatus.RESOLVED.value,
            },
            created_at=resolved_at,
        )
    )
    db.commit()
    return conflict


def detect_medication_dose_conflicts(
    db: Session,
    patient_id: uuid.UUID,
    new_facts: list[ClinicalFact],
) -> list[Conflict]:
    """Create conflicts for new non-authoritative medication dose facts only."""
    medication_facts = [
        fact
        for fact in new_facts
        if fact.fact_type is FactType.MEDICATION and not _is_clinician_authoritative(fact)
    ]
    if not medication_facts:
        return []

    existing_facts = list(
        db.scalars(
            select(ClinicalFact)
            .options(joinedload(ClinicalFact.entry), joinedload(ClinicalFact.reviewed_by))
            .where(
                ClinicalFact.patient_id == patient_id,
                ClinicalFact.fact_type == FactType.MEDICATION,
            )
        )
    )
    authoritative_by_entity: dict[str, list[ClinicalFact]] = {}
    new_ids = {fact.id for fact in medication_facts}
    for fact in existing_facts:
        if fact.id not in new_ids and _is_clinician_authoritative(fact):
            authoritative_by_entity.setdefault(_entity_key(fact.entity_name), []).append(fact)

    existing_pairs = set(
        db.execute(
            select(Conflict.conflicting_fact_id, Conflict.authoritative_fact_id).where(
                Conflict.patient_id == patient_id,
                Conflict.status == ConflictStatus.DETECTED,
            )
        ).all()
    )
    created: list[Conflict] = []
    for fact in medication_facts:
        conflicting_dose = _dose(fact)
        if conflicting_dose is None:
            continue
        candidates = authoritative_by_entity.get(_entity_key(fact.entity_name), [])
        candidates.sort(key=lambda item: (item.created_at, item.id), reverse=True)
        if not candidates:
            continue
        authoritative = candidates[0]
        authoritative_dose = _dose(authoritative)
        if authoritative_dose is None or authoritative_dose == conflicting_dose:
            continue
        pair = (fact.id, authoritative.id)
        if pair in existing_pairs:
            continue
        conflict = Conflict(
            patient_id=patient_id,
            conflict_type=ConflictType.MEDICATION_DOSE,
            entity_name=fact.entity_name.strip().casefold(),
            conflicting_fact=fact,
            authoritative_fact=authoritative,
            description=(
                f"Patient/AI record states {_display_value(fact)}; clinician record "
                f"states {_display_value(authoritative)}."
            ),
            status=ConflictStatus.DETECTED,
        )
        db.add(conflict)
        created.append(conflict)
        existing_pairs.add(pair)
    db.flush()
    return created


def _is_clinician_authoritative(fact: ClinicalFact) -> bool:
    if fact.entry.author_role is AuthorRole.CLINICIAN:
        return True
    return (
        fact.review_status is ReviewStatus.CONFIRMED
        and fact.reviewed_by is not None
        and fact.reviewed_by.role is UserRole.CLINICIAN
    )


def _entity_key(entity_name: str) -> str:
    return " ".join(entity_name.split()).casefold()


def _dose(fact: ClinicalFact) -> Dose | None:
    if fact.value_number is not None and fact.unit is not None:
        return Dose(float(fact.value_number), _unit_key(fact.unit))
    if fact.value_text is None:
        return None
    match = _DOSE_PATTERN.search(fact.value_text)
    if match is None:
        return None
    return Dose(float(match.group("amount")), _unit_key(match.group("unit")))


def _unit_key(unit: str) -> str:
    normalized = unit.strip().casefold()
    return "mcg" if normalized in {"μg", "ug"} else normalized


def _display_value(fact: ClinicalFact) -> str:
    if fact.value_text is not None:
        return fact.value_text
    return f"{fact.value_number:g} {fact.unit}"
