from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.clinical import Conflict, ConflictStatus, Highlight, HighlightStatus
from app.models.identity import Patient
from app.seed import command as seed_command
from app.seed.sarah_lim import fixed_uuid, seed_sarah_lim


def test_reset_restores_the_canonical_synthetic_demo_state() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = Session(engine)
    seed_sarah_lim(session)

    chest = session.get(Highlight, fixed_uuid(41))
    conflict = session.get(Conflict, fixed_uuid(51))
    assert chest is not None and conflict is not None
    chest.status = HighlightStatus.REJECTED
    conflict.status = ConflictStatus.RESOLVED
    session.commit()

    reset_demo = getattr(seed_command, "reset_sarah_lim_demo")
    reset_demo(session)

    patient_ids = list(session.scalars(select(Patient.id)))
    highlights = list(session.scalars(select(Highlight).order_by(Highlight.id)))
    conflicts = list(session.scalars(select(Conflict).order_by(Conflict.id)))
    assert patient_ids == [fixed_uuid(2)]
    assert [(item.text, item.status) for item in highlights] == [
        ("Penicillin allergy", HighlightStatus.ACCEPTED),
        ("Worsening chest pressure", HighlightStatus.SUGGESTED),
        ("Atorvastatin dose discrepancy", HighlightStatus.SUGGESTED),
    ]
    assert [(item.entity_name, item.status) for item in conflicts] == [
        ("atorvastatin", ConflictStatus.DETECTED)
    ]
    session.close()
