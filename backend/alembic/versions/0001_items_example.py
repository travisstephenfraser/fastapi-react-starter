# TEMPLATE: example — `make clean-example` removes this migration.
"""items example feature — table + RLS.

Creates `public.items`, enables RLS, adds policies scoped per-user via
`auth.uid()`. The policies are split by command (SELECT / INSERT / UPDATE /
DELETE) so INSERT carries its own `WITH CHECK` and a client can't create rows
with someone else's `user_id`.

Revision ID: 0001_items_example
Revises:
Create Date: 2026-04-19
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_items_example"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "items",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, index=True
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.String(2000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_items_user_id", "items", ["user_id"])

    # Enable RLS. Without this, policies do nothing.
    op.execute("ALTER TABLE public.items ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.items FORCE ROW LEVEL SECURITY")

    # Policies split by command so INSERT has an explicit WITH CHECK.
    op.execute(
        """
        CREATE POLICY items_select_own
          ON public.items
          FOR SELECT
          TO authenticated
          USING (user_id = auth.uid())
        """
    )
    op.execute(
        """
        CREATE POLICY items_insert_own
          ON public.items
          FOR INSERT
          TO authenticated
          WITH CHECK (user_id = auth.uid())
        """
    )
    op.execute(
        """
        CREATE POLICY items_update_own
          ON public.items
          FOR UPDATE
          TO authenticated
          USING (user_id = auth.uid())
          WITH CHECK (user_id = auth.uid())
        """
    )
    op.execute(
        """
        CREATE POLICY items_delete_own
          ON public.items
          FOR DELETE
          TO authenticated
          USING (user_id = auth.uid())
        """
    )

    # Grants — RLS still applies on top; this grants access to the table surface.
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON public.items TO authenticated")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS items_delete_own ON public.items")
    op.execute("DROP POLICY IF EXISTS items_update_own ON public.items")
    op.execute("DROP POLICY IF EXISTS items_insert_own ON public.items")
    op.execute("DROP POLICY IF EXISTS items_select_own ON public.items")
    op.drop_index("ix_items_user_id", table_name="items")
    op.drop_table("items")
