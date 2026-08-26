"""patient care query indexes

Revision ID: 9a31c0de782f
Revises: 8f3d92c1a7be
Create Date: 2026-08-26 19:00:00

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "9a31c0de782f"
down_revision: str | Sequence[str] | None = "8f3d92c1a7be"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_clinical_facts_patient_entry",
        "clinical_facts",
        ["patient_id", "entry_id"],
        unique=False,
    )
    op.create_index(
        "ix_highlights_patient_status_score",
        "highlights",
        [
            "patient_id",
            "status",
            sa.text("(base_score + learned_score) DESC"),
        ],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_highlights_patient_status_score",
        table_name="highlights",
    )
    op.drop_index(
        "ix_clinical_facts_patient_entry",
        table_name="clinical_facts",
    )
