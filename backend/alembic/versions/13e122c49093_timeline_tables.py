"""timeline_tables

Revision ID: 13e122c49093
Revises: 32cf30f43cfc
Create Date: 2026-08-25 23:33:20.718814

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "13e122c49093"
down_revision: str | Sequence[str] | None = "32cf30f43cfc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "consult_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column(
            "interaction_type",
            sa.Enum(
                "doctor_patient",
                "nurse_patient",
                "ai_patient",
                name="interaction_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_transcript", sa.Text(), nullable=False),
        sa.Column("redacted_transcript", sa.Text(), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        sa.Column(
            "processing_status",
            sa.Enum(
                "pending",
                "completed",
                "failed",
                name="processing_status",
                native_enum=False,
                create_constraint=True,
            ),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("processing_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_consult_sessions_created_by_id", "consult_sessions", ["created_by_id"]
    )
    op.create_index("ix_consult_sessions_patient_id", "consult_sessions", ["patient_id"])
    op.create_index(
        "ix_consult_sessions_patient_occurred_at",
        "consult_sessions",
        ["patient_id", "occurred_at"],
    )
    op.create_table(
        "entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=True),
        sa.Column(
            "author_role",
            sa.Enum(
                "patient",
                "staff",
                "clinician",
                "system",
                name="entry_author_role",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "entry_type",
            sa.Enum(
                "clinician_note",
                "staff_note",
                "ai_doctor_consult_summary",
                "ai_nurse_consult_summary",
                "ai_patient_session_summary",
                "patient_instruction",
                "system_event",
                name="entry_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("current_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "provenance_type",
            sa.Enum(
                "consult_session",
                "manual",
                "system",
                name="provenance_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("provenance_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(provenance_type = 'consult_session' AND provenance_id IS NOT NULL) OR "
            "(provenance_type <> 'consult_session' AND provenance_id IS NULL)",
            name="ck_entries_consult_provenance",
        ),
        sa.CheckConstraint(
            "current_version >= 1", name="ck_entries_current_version_positive"
        ),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["provenance_id"], ["consult_sessions.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_entries_author_id", "entries", ["author_id"])
    op.create_index("ix_entries_patient_created_at", "entries", ["patient_id", "created_at"])
    op.create_index("ix_entries_patient_id", "entries", ["patient_id"])
    op.create_index("ix_entries_provenance_id", "entries", ["provenance_id"])

    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE public.consult_sessions ENABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE public.entries ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_entries_provenance_id", table_name="entries")
    op.drop_index("ix_entries_patient_id", table_name="entries")
    op.drop_index("ix_entries_patient_created_at", table_name="entries")
    op.drop_index("ix_entries_author_id", table_name="entries")
    op.drop_table("entries")
    op.drop_index("ix_consult_sessions_patient_occurred_at", table_name="consult_sessions")
    op.drop_index("ix_consult_sessions_patient_id", table_name="consult_sessions")
    op.drop_index("ix_consult_sessions_created_by_id", table_name="consult_sessions")
    op.drop_table("consult_sessions")
