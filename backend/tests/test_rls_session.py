"""RLS + session isolation regression tests.

These tests exist because the v2 reviewers found three CRITICAL ways the
dep-level claim-injection pattern can silently break:

1. Plain `get_db` bypasses RLS (no claims injected) — we delete `get_db` and
   test for its absence (see test_dependency_graph.py).
2. `SET LOCAL` + pool reuse leaks claims across requests — test here.
3. Session touched outside a transaction leaves claims unset / stale — test here.

If any of these flip to pass-without-intent, RLS is not enforcing anything.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import pytest
import sqlalchemy.exc
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

USER_A = uuid.UUID("00000000-0000-0000-0000-000000000001")
USER_B = uuid.UUID("00000000-0000-0000-0000-000000000002")


async def _set_claims(session: AsyncSession, user_id: uuid.UUID) -> None:
    await session.execute(text("SET LOCAL role = 'authenticated'"))
    await session.execute(
        text("SET LOCAL request.jwt.claims = :c"),
        {"c": json.dumps({"sub": str(user_id), "role": "authenticated"})},
    )


async def _auth_uid(session: AsyncSession) -> Any:
    row = await session.execute(text("SELECT auth.uid()"))
    return row.scalar()


@pytest.mark.asyncio
async def test_rls_scopes_select_per_user(session: AsyncSession) -> None:
    """User A creates an item; user B cannot see it."""
    async with session.begin():
        await _set_claims(session, USER_A)
        await session.execute(
            text("INSERT INTO items (user_id, name) VALUES (:u, :n)"),
            {"u": str(USER_A), "n": "alpha"},
        )

    async with session.begin():
        await _set_claims(session, USER_B)
        result = await session.execute(text("SELECT name FROM items"))
        rows = result.scalars().all()
        assert rows == [], f"User B saw User A's rows: {rows}"


@pytest.mark.asyncio
async def test_rls_rejects_cross_user_insert(session: AsyncSession) -> None:
    """User A cannot INSERT a row with user_id = USER_B (WITH CHECK must reject)."""
    async with session.begin():
        await _set_claims(session, USER_A)
        # RLS rejects cross-user INSERTs at the DB layer; asyncpg surfaces it
        # as a DBAPIError (subclass of sqlalchemy.exc.DBAPIError).
        with pytest.raises(sqlalchemy.exc.DBAPIError):
            await session.execute(
                text("INSERT INTO items (user_id, name) VALUES (:u, :n)"),
                {"u": str(USER_B), "n": "malicious"},
            )


@pytest.mark.asyncio
async def test_claims_do_not_leak_across_transactions(session: AsyncSession) -> None:
    """`SET LOCAL` must be scoped to the transaction. After commit, auth.uid() is NULL."""
    async with session.begin():
        await _set_claims(session, USER_A)
        uid = await _auth_uid(session)
        assert uid == USER_A

    # New transaction, no claims set — auth.uid() must be NULL.
    async with session.begin():
        uid = await _auth_uid(session)
        assert uid is None, f"Claims leaked across transactions: {uid}"
