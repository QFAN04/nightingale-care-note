"""add comment mentions

Revision ID: 8f3d92c1a7be
Revises: 0042f75ab123
Create Date: 2026-08-26 14:30:00

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "8f3d92c1a7be"
down_revision: str | Sequence[str] | None = "0042f75ab123"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("comments") as batch_op:
        batch_op.add_column(sa.Column("mentioned_role", sa.Text(), nullable=True))
        batch_op.create_check_constraint(
            "comment_mentioned_role",
            "mentioned_role IS NULL OR mentioned_role IN "
            "('patient', 'staff', 'clinician', 'admin')",
        )


def downgrade() -> None:
    with op.batch_alter_table("comments") as batch_op:
        batch_op.drop_constraint("comment_mentioned_role", type_="check")
        batch_op.drop_column("mentioned_role")
