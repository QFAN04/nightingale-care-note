"""enable_rls_identity_tables

Revision ID: 32cf30f43cfc
Revises: 5cc8461bc983
Create Date: 2026-08-25 23:27:29.987811

"""
from collections.abc import Sequence

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "32cf30f43cfc"
down_revision: str | Sequence[str] | None = "5cc8461bc983"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


RLS_TABLES = ("clinics", "patients", "users")


def upgrade() -> None:
    """Enable deny-by-default RLS for the current public tables."""
    if op.get_bind().dialect.name != "postgresql":
        return

    for table in RLS_TABLES:
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    """Restore the pre-RLS state."""
    if op.get_bind().dialect.name != "postgresql":
        return

    for table in reversed(RLS_TABLES):
        op.execute(f"ALTER TABLE public.{table} DISABLE ROW LEVEL SECURITY")
