from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, Enum, ForeignKey, Index, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class UserRole(str, enum.Enum):
    PATIENT = "patient"
    STAFF = "staff"
    CLINICIAN = "clinician"
    ADMIN = "admin"


class Clinic(Base):
    __tablename__ = "clinics"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    users: Mapped[list[User]] = relationship(back_populates="clinic")
    patients: Mapped[list[Patient]] = relationship(back_populates="clinic")


class Patient(Base):
    __tablename__ = "patients"
    __table_args__ = (Index("ix_patients_clinic_id", "clinic_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("clinics.id", ondelete="RESTRICT"), nullable=False
    )
    external_ref: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    sex: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    clinic: Mapped[Clinic] = relationship(back_populates="patients")
    users: Mapped[list[User]] = relationship(back_populates="patient")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "(role = 'patient' AND patient_id IS NOT NULL) OR "
            "(role <> 'patient' AND patient_id IS NULL)",
            name="ck_users_patient_role_mapping",
        ),
        Index("ix_users_clinic_id", "clinic_id"),
        Index("ix_users_patient_id", "patient_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("clinics.id", ondelete="RESTRICT"), nullable=False
    )
    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("patients.id", ondelete="RESTRICT"), nullable=True
    )
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
            native_enum=False,
            create_constraint=True,
            values_callable=lambda values: [value.value for value in values],
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    clinic: Mapped[Clinic] = relationship(back_populates="users")
    patient: Mapped[Patient | None] = relationship(back_populates="users")
