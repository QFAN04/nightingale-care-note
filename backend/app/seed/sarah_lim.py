from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.models.audit import ChangeReason, Comment, EntryVersion
from app.models.clinical import (
    ClinicalFact, Conflict, ConflictStatus, ConflictType, FactType, Highlight,
    HighlightCategory, HighlightStatus, PersistenceType, ReviewStatus, RiskLevel,
    Task, TaskPriority, TaskStatus,
)
from app.models.identity import Clinic, Patient, User, UserRole
from app.models.timeline import (
    AuthorRole, ConsultSession, Entry, EntryType, InteractionType,
    ProcessingStatus, ProvenanceType,
)


def fixed_uuid(value: int) -> uuid.UUID:
    return uuid.UUID(int=value)


def at(month: int, day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, month, day, hour, minute, tzinfo=timezone.utc)


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SarahLimStory:
    clinic: Clinic
    patient: Patient
    patient_user: User
    staff_user: User
    clinician_user: User
    admin_user: User
    august_patient_session: ConsultSession
    august_doctor_session: ConsultSession


def seed_sarah_lim(session: Session) -> SarahLimStory:
    """Insert the canonical, entirely synthetic Nightingale demo story."""
    clinic = Clinic(id=fixed_uuid(1), name="Nightingale Central Clinic")
    patient = Patient(
        id=fixed_uuid(2), clinic=clinic, external_ref="PAT-001",
        display_name="Sarah Lim", date_of_birth=date(1984, 5, 18), sex="female",
    )
    patient_user = User(
        id=fixed_uuid(3), clinic=clinic, patient=patient,
        display_name="Sarah Lim", role=UserRole.PATIENT,
    )
    staff_user = User(
        id=fixed_uuid(4), clinic=clinic, display_name="Amanda Wong", role=UserRole.STAFF,
    )
    clinician_user = User(
        id=fixed_uuid(5), clinic=clinic, display_name="Dr Priya Nair",
        role=UserRole.CLINICIAN,
    )
    admin_user = User(
        id=fixed_uuid(6), clinic=clinic, display_name="Daniel Tan", role=UserRole.ADMIN,
    )

    april_content = (
        "Penicillin allergy confirmed; previous reaction was urticaria. "
        "Atorvastatin 20 mg once daily remains the clinician-confirmed medication dose."
    )
    april_entry = Entry(
        id=fixed_uuid(10), patient=patient, author=clinician_user,
        author_role=AuthorRole.CLINICIAN, entry_type=EntryType.CLINICIAN_NOTE,
        content=april_content, provenance_type=ProvenanceType.MANUAL,
        created_at=at(4, 15, 9), updated_at=at(4, 15, 9),
    )
    july_entry = Entry(
        id=fixed_uuid(11), patient=patient, author=staff_user,
        author_role=AuthorRole.STAFF, entry_type=EntryType.STAFF_NOTE,
        content=(
            "Routine telephone follow-up completed. Sarah reports no chest pain or "
            "chest pressure and no new medication concerns."
        ),
        provenance_type=ProvenanceType.MANUAL,
        created_at=at(7, 12, 11), updated_at=at(7, 12, 11),
    )

    august_patient_session = ConsultSession(
        id=fixed_uuid(20), patient=patient,
        interaction_type=InteractionType.AI_PATIENT,
        occurred_at=at(8, 23, 20, 15),
        raw_transcript=(
            "Patient: I have had new chest pressure for three days. "
            "Last night the chest pressure felt stronger than before."
        ),
        redacted_transcript=(
            "Patient: I have had new chest pressure for three days. "
            "Last night the chest pressure felt stronger than before."
        ),
        created_by=patient_user, processing_status=ProcessingStatus.COMPLETED,
    )
    august_patient_entry = Entry(
        id=fixed_uuid(12), patient=patient, author_role=AuthorRole.SYSTEM,
        entry_type=EntryType.AI_PATIENT_SESSION_SUMMARY,
        content=(
            "Patient reports worsening chest pressure, newly present for three days and "
            "stronger last night. "
            "This is an AI-extracted report pending clinician review."
        ),
        provenance_type=ProvenanceType.CONSULT_SESSION,
        consult_session=august_patient_session,
        created_at=at(8, 23, 20, 16), updated_at=at(8, 23, 20, 16),
    )
    august_staff_entry = Entry(
        id=fixed_uuid(13), patient=patient, author=staff_user,
        author_role=AuthorRole.STAFF, entry_type=EntryType.STAFF_NOTE,
        content=(
            "Follow-up call after the AI session: chest pressure remains present. "
            "Escalated to the clinician for review."
        ),
        provenance_type=ProvenanceType.MANUAL,
        created_at=at(8, 24, 9), updated_at=at(8, 24, 9),
    )

    raw_doctor_transcript = (
        "Doctor: Please confirm your details.\n"
        "Patient: I am Sarah Lim, phone 91234567, ID S1234567A.\n"
        "Doctor: How is the chest pressure?\n"
        "Patient: It is still present but not as strong as last night. "
        "I thought I was taking Atorvastatin 10 mg.\n"
        "Doctor: The clinician record states Atorvastatin 20 mg; we will reconcile it."
    )
    redacted_doctor_transcript = (
        "Doctor: Please confirm your details.\n"
        "Patient: I am [PATIENT_NAME], phone [PHONE], ID [ID].\n"
        "Doctor: How is the chest pressure?\n"
        "Patient: It is still present but not as strong as last night. "
        "I thought I was taking Atorvastatin 10 mg.\n"
        "Doctor: The clinician record states Atorvastatin 20 mg; we will reconcile it."
    )
    august_doctor_session = ConsultSession(
        id=fixed_uuid(21), patient=patient,
        interaction_type=InteractionType.DOCTOR_PATIENT,
        occurred_at=at(8, 25, 9, 30), raw_transcript=raw_doctor_transcript,
        redacted_transcript=redacted_doctor_transcript,
        created_by=clinician_user, processing_status=ProcessingStatus.COMPLETED,
    )
    august_doctor_entry = Entry(
        id=fixed_uuid(14), patient=patient, author_role=AuthorRole.SYSTEM,
        entry_type=EntryType.AI_DOCTOR_CONSULT_SUMMARY,
        content=(
            "Chest pressure remains present but is less intense than last night. "
            "Patient reported Atorvastatin 10 mg, conflicting with the clinician-confirmed "
            "20 mg record; medication reconciliation is required."
        ),
        provenance_type=ProvenanceType.CONSULT_SESSION,
        consult_session=august_doctor_session,
        created_at=at(8, 25, 9, 31), updated_at=at(8, 25, 9, 31),
    )

    allergy_fact = ClinicalFact(
        id=fixed_uuid(30), patient=patient, entry=april_entry,
        fact_type=FactType.ALLERGY, entity_name="penicillin", value_text="urticaria",
        risk_level=RiskLevel.CRITICAL, persistence_type=PersistenceType.PERSISTENT,
        source_quote="Penicillin allergy confirmed; previous reaction was urticaria.",
        extraction_confidence=1.0, review_status=ReviewStatus.CONFIRMED,
        reviewed_by=clinician_user, reviewed_at=at(4, 15, 9), created_at=at(4, 15, 9),
    )
    dose_20_fact = ClinicalFact(
        id=fixed_uuid(31), patient=patient, entry=april_entry,
        fact_type=FactType.MEDICATION, entity_name="atorvastatin",
        value_text="20 mg once daily", value_number=20, unit="mg",
        risk_level=RiskLevel.MEDIUM, persistence_type=PersistenceType.PERSISTENT,
        source_quote="Atorvastatin 20 mg once daily", extraction_confidence=1.0,
        review_status=ReviewStatus.CONFIRMED, reviewed_by=clinician_user,
        reviewed_at=at(4, 15, 9), created_at=at(4, 15, 9),
    )
    chest_fact = ClinicalFact(
        id=fixed_uuid(32), patient=patient, entry=august_patient_entry,
        fact_type=FactType.SYMPTOM, entity_name="chest pressure", value_text="worsening",
        risk_level=RiskLevel.HIGH, persistence_type=PersistenceType.TRANSIENT,
        source_quote="Last night the chest pressure felt stronger than before.",
        extraction_confidence=0.92, review_status=ReviewStatus.SUGGESTED,
        created_at=at(8, 23, 20, 16),
    )
    dose_10_fact = ClinicalFact(
        id=fixed_uuid(33), patient=patient, entry=august_doctor_entry,
        fact_type=FactType.MEDICATION, entity_name="atorvastatin",
        value_text="10 mg", value_number=10, unit="mg",
        risk_level=RiskLevel.MEDIUM, persistence_type=PersistenceType.PERSISTENT,
        source_quote="I thought I was taking Atorvastatin 10 mg.",
        extraction_confidence=0.96, review_status=ReviewStatus.SUGGESTED,
        created_at=at(8, 25, 9, 31),
    )

    allergy_highlight = Highlight(
        id=fixed_uuid(40), patient=patient, clinical_fact=allergy_fact,
        text="Penicillin allergy", category=HighlightCategory.CRITICAL,
        risk_level=RiskLevel.CRITICAL,
        risk_reason="Clinician-confirmed · critical allergy · persistent safety context",
        base_score=20, learned_score=0, status=HighlightStatus.ACCEPTED,
        reviewed_by=clinician_user, reviewed_at=at(4, 15, 9), created_at=at(4, 15, 9),
    )
    chest_highlight = Highlight(
        id=fixed_uuid(41), patient=patient, clinical_fact=chest_fact,
        text="Worsening chest pressure", category=HighlightCategory.RECENT_CHANGE,
        risk_level=RiskLevel.HIGH,
        risk_reason="High-risk symptom · recent change · clinical follow-up unresolved",
        base_score=16, learned_score=0, status=HighlightStatus.SUGGESTED,
        created_at=at(8, 23, 20, 16),
    )
    conflict_highlight = Highlight(
        id=fixed_uuid(42), patient=patient, clinical_fact=dose_10_fact,
        text="Atorvastatin dose discrepancy", category=HighlightCategory.CONFLICT,
        risk_level=RiskLevel.MEDIUM,
        risk_reason="Patient-reported dose conflicts with clinician-confirmed record",
        base_score=13, learned_score=0, status=HighlightStatus.SUGGESTED,
        created_at=at(8, 25, 9, 31),
    )
    open_task = Task(
        id=fixed_uuid(50), patient=patient, source_entry=august_staff_entry,
        source_fact=chest_fact,
        description="Clinician to review persistent chest pressure and document next steps",
        priority=TaskPriority.HIGH, status=TaskStatus.OPEN,
        assigned_role=UserRole.CLINICIAN, created_at=at(8, 24, 9),
    )
    conflict = Conflict(
        id=fixed_uuid(51), patient=patient,
        conflict_type=ConflictType.MEDICATION_DOSE, entity_name="atorvastatin",
        conflicting_fact=dose_10_fact, authoritative_fact=dose_20_fact,
        description="Patient reported 10 mg; clinician-confirmed record states 20 mg.",
        status=ConflictStatus.DETECTED, created_at=at(8, 25, 9, 31),
    )
    comment = Comment(
        id=fixed_uuid(60), entry=august_staff_entry, author=staff_user,
        content="@clinician Please review the persistent chest pressure before today's consult.",
        created_at=at(8, 24, 9, 5),
    )
    april_version = EntryVersion(
        id=fixed_uuid(70), entry=april_entry, version_number=1, content=april_content,
        changed_by=clinician_user, changed_at=at(4, 15, 9),
        change_reason=ChangeReason.CREATED, content_hash=content_hash(april_content),
    )

    session.add_all([
        clinic, patient, patient_user, staff_user, clinician_user, admin_user,
        april_entry, july_entry, august_patient_entry, august_staff_entry,
        august_doctor_entry, allergy_fact, dose_20_fact, chest_fact, dose_10_fact,
        allergy_highlight, chest_highlight, conflict_highlight, open_task, conflict,
        comment, april_version,
    ])
    session.commit()

    return SarahLimStory(
        clinic=clinic, patient=patient, patient_user=patient_user,
        staff_user=staff_user, clinician_user=clinician_user, admin_user=admin_user,
        august_patient_session=august_patient_session,
        august_doctor_session=august_doctor_session,
    )
