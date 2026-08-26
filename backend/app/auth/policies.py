"""Clinic-scoped role policies shared by API and service layers."""

from sqlalchemy import and_
from sqlalchemy.sql.elements import ColumnElement

from app.models.clinical import Highlight
from app.models.identity import Patient, User, UserRole
from app.models.timeline import Entry, EntryType, InteractionType


def can_access_patient(user: User, patient: Patient) -> bool:
    if user.role is UserRole.PATIENT:
        return user.patient_id == patient.id and user.clinic_id == patient.clinic_id
    return user.clinic_id == patient.clinic_id


def can_view_entry(user: User, entry: Entry) -> bool:
    if not can_access_patient(user, entry.patient):
        return False
    if user.role is UserRole.PATIENT:
        return entry.entry_type is EntryType.PATIENT_INSTRUCTION
    return True


def can_edit_entry(user: User, entry: Entry) -> bool:
    if not can_access_patient(user, entry.patient):
        return False
    editable_type = {
        UserRole.STAFF: EntryType.STAFF_NOTE,
        UserRole.CLINICIAN: EntryType.CLINICIAN_NOTE,
    }.get(user.role)
    return editable_type is not None and entry.entry_type is editable_type


def patient_scope_filter(user: User) -> ColumnElement[bool]:
    if user.role is UserRole.PATIENT:
        return and_(Patient.id == user.patient_id, Patient.clinic_id == user.clinic_id)
    return Patient.clinic_id == user.clinic_id


def entry_visibility_filter(user: User) -> ColumnElement[bool]:
    clinic_scope = Entry.patient.has(Patient.clinic_id == user.clinic_id)
    if user.role is UserRole.PATIENT:
        return and_(
            clinic_scope,
            Entry.patient_id == user.patient_id,
            Entry.entry_type == EntryType.PATIENT_INSTRUCTION,
        )
    return clinic_scope


def highlight_scope_filter(user: User) -> ColumnElement[bool]:
    clinic_scope = Highlight.patient.has(Patient.clinic_id == user.clinic_id)
    if user.role is UserRole.PATIENT:
        return and_(clinic_scope, Highlight.patient_id == user.patient_id)
    return clinic_scope


def can_review_highlights(user: User) -> bool:
    return user.role is UserRole.CLINICIAN


def allowed_scribe_interaction(user: User) -> InteractionType | None:
    return {
        UserRole.PATIENT: InteractionType.AI_PATIENT,
        UserRole.STAFF: InteractionType.NURSE_PATIENT,
        UserRole.CLINICIAN: InteractionType.DOCTOR_PATIENT,
    }.get(user.role)


def can_view_unreviewed_context(user: User) -> bool:
    return user.role is not UserRole.PATIENT
