"""enable RLS on Alembic metadata

Revision ID: c4e71d9a2f30
Revises: 9a31c0de782f
Create Date: 2026-08-27 00:25:00

"""
from collections.abc import Sequence

from alembic import op


revision: str = "c4e71d9a2f30"
down_revision: str | Sequence[str] | None = "9a31c0de782f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE public.alembic_version ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE public.alembic_version DISABLE ROW LEVEL SECURITY")
