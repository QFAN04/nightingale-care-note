"""Idempotent command entry point for the synthetic Sarah Lim demo story."""

from sqlalchemy.orm import Session

from app.models.identity import Patient
from app.seed.sarah_lim import fixed_uuid, seed_sarah_lim


SARAH_PATIENT_ID = fixed_uuid(2)


def ensure_sarah_lim_seeded(session: Session) -> bool:
    """Seed the fixed synthetic story once; return whether rows were created."""
    if session.get(Patient, SARAH_PATIENT_ID) is not None:
        return False
    seed_sarah_lim(session)
    return True


def main() -> int:
    from app.db import SessionLocal

    with SessionLocal() as session:
        created = ensure_sarah_lim_seeded(session)
    status = "created" if created else "already present"
    print(f"Synthetic Sarah Lim demo data: {status}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
