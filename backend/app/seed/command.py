"""Idempotent and explicitly resettable synthetic Sarah Lim demo story."""

import argparse

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.base import Base
from app.models.identity import Clinic, Patient, User
from app.seed.sarah_lim import fixed_uuid, seed_sarah_lim


SARAH_PATIENT_ID = fixed_uuid(2)
SARAH_CLINIC_ID = fixed_uuid(1)
SARAH_USER_IDS = {fixed_uuid(value) for value in range(3, 7)}


class UnsafeDemoResetError(RuntimeError):
    """Raised when a reset would remove data outside the fixed synthetic story."""


def ensure_sarah_lim_seeded(session: Session) -> bool:
    """Seed the fixed synthetic story once; return whether rows were created."""
    if session.get(Patient, SARAH_PATIENT_ID) is not None:
        return False
    seed_sarah_lim(session)
    return True


def reset_sarah_lim_demo(session: Session) -> None:
    """Replace a synthetic-only database with the canonical Sarah demo state."""
    patient_ids = set(session.scalars(select(Patient.id)))
    clinic_ids = set(session.scalars(select(Clinic.id)))
    user_ids = set(session.scalars(select(User.id)))
    if not patient_ids.issubset({SARAH_PATIENT_ID}):
        raise UnsafeDemoResetError("Refusing to reset a database with other patients")
    if not clinic_ids.issubset({SARAH_CLINIC_ID}):
        raise UnsafeDemoResetError("Refusing to reset a database with other clinics")
    if not user_ids.issubset(SARAH_USER_IDS):
        raise UnsafeDemoResetError("Refusing to reset a database with other users")

    for table in reversed(Base.metadata.sorted_tables):
        session.execute(delete(table))
    session.commit()
    session.expunge_all()
    seed_sarah_lim(session)


def main() -> int:
    from app.db import SessionLocal

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reset-demo",
        action="store_true",
        help="replace synthetic-only application data with the canonical Sarah story",
    )
    args = parser.parse_args()
    with SessionLocal() as session:
        if args.reset_demo:
            reset_sarah_lim_demo(session)
            status = "reset to canonical state"
        else:
            created = ensure_sarah_lim_seeded(session)
            status = "created" if created else "already present"
    print(f"Synthetic Sarah Lim demo data: {status}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
