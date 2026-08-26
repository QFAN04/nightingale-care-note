from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

from app.entries.service import EntryVersionConflictError, update_entry
from app.models.audit import EntryVersion
from app.models.base import Base
from app.models.timeline import Entry
from app.seed.sarah_lim import fixed_uuid, seed_sarah_lim


def make_engine(database_path: Path):
    engine = create_engine(f"sqlite+pysqlite:///{database_path}")

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as seed_session:
        seed_sarah_lim(seed_session)
    return engine


def test_two_sessions_cannot_overwrite_with_the_same_expected_version(
    tmp_path: Path,
) -> None:
    engine = make_engine(tmp_path / "concurrent.sqlite3")
    entry_id = fixed_uuid(10)

    with Session(engine) as first_session, Session(engine) as stale_session:
        first_entry = first_session.get(Entry, entry_id)
        stale_entry = stale_session.get(Entry, entry_id)
        first_actor = first_entry.author if first_entry is not None else None
        stale_actor = stale_entry.author if stale_entry is not None else None
        assert first_entry is not None and first_actor is not None
        assert stale_entry is not None and stale_actor is not None

        update_entry(first_session, first_entry, first_actor, "Winning edit", 1)

        with pytest.raises(EntryVersionConflictError) as conflict:
            update_entry(stale_session, stale_entry, stale_actor, "Stale edit", 1)

        assert conflict.value.current_version == 2
        assert conflict.value.expected_version == 1

    with Session(engine) as verification_session:
        entry = verification_session.get(Entry, entry_id)
        versions = list(
            verification_session.scalars(
                select(EntryVersion)
                .where(EntryVersion.entry_id == entry_id)
                .order_by(EntryVersion.version_number)
            )
        )
        assert entry is not None
        assert entry.content == "Winning edit"
        assert entry.current_version == 2
        assert [version.version_number for version in versions] == [1, 2]


def test_edits_to_different_entries_do_not_overwrite_each_other(tmp_path: Path) -> None:
    engine = make_engine(tmp_path / "independent.sqlite3")
    clinician_entry_id = fixed_uuid(10)
    staff_entry_id = fixed_uuid(13)

    with Session(engine) as session:
        clinician_entry = session.get(Entry, clinician_entry_id)
        staff_entry = session.get(Entry, staff_entry_id)
        assert clinician_entry is not None and clinician_entry.author is not None
        assert staff_entry is not None and staff_entry.author is not None

        update_entry(
            session,
            clinician_entry,
            clinician_entry.author,
            "Clinician entry edit",
            1,
        )
        update_entry(
            session,
            staff_entry,
            staff_entry.author,
            "Staff entry edit",
            1,
        )

    with Session(engine) as verification_session:
        clinician_entry = verification_session.get(Entry, clinician_entry_id)
        staff_entry = verification_session.get(Entry, staff_entry_id)
        assert clinician_entry is not None
        assert staff_entry is not None
        assert clinician_entry.content == "Clinician entry edit"
        assert staff_entry.content == "Staff entry edit"
        assert clinician_entry.current_version == 2
        assert staff_entry.current_version == 2
