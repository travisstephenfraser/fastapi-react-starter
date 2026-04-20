"""Async DB engine + session factory.

CRITICAL security properties — do not edit without re-reading the RLS section of
README and running `tests/test_rls_session.py`:

1. The app connects as a **non-superuser** Postgres role (`settings.app_db_role`).
   Row-level security depends on this. If this role has BYPASSRLS, RLS is
   silently disabled.
2. Claims are injected via `SET LOCAL request.jwt.claims = <json>` inside an
   explicit transaction. `SET LOCAL` is scoped to the transaction; the
   transaction boundary is structural, not convention.
3. On connection return to the pool, `DISCARD ALL` runs to prevent any
   non-LOCAL state from bleeding into the next request.

The only session factory exposed is via the DI helpers in `deps.py`. Do not
import `AsyncSessionLocal` directly from a route handler.
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# For Supabase transaction-mode pooler compatibility, prepared statements must be off.
_connect_args: dict[str, Any] = {"statement_cache_size": 0, "prepared_statement_cache_size": 0}

engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    pool_reset_on_return="rollback",  # always roll back before returning to pool
    connect_args=_connect_args,
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


# Belt-and-suspenders: run DISCARD ALL when a connection is reset. This catches
# the case where someone accidentally used `SET` without `LOCAL`. Event fires on
# the underlying sync engine; SQLAlchemy async wraps it.
@event.listens_for(engine.sync_engine, "reset")
def _discard_all_on_reset(dbapi_connection: Any, _connection_record: Any) -> None:
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("DISCARD ALL")
    finally:
        cursor.close()


async def _get_session_with_claims(claims: dict[str, Any]) -> AsyncGenerator[AsyncSession, None]:
    """Open a session, start a transaction, set the app role + JWT claims, yield.

    The transaction is committed on successful handler return and rolled back on
    exception. `SET LOCAL` scopes the claim to this transaction only.
    """
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # `SET LOCAL role` switches to the app role for this transaction only.
            # `SET LOCAL request.jwt.claims` is what `auth.uid()` reads.
            # Inject only the minimum Supabase-RLS needs: sub, role, email.
            minimal_claims = {
                k: claims[k]
                for k in ("sub", "role", "email", "aud")
                if k in claims
            }
            await session.execute(
                text("SET LOCAL role = :role"), {"role": settings.app_db_role}
            )
            await session.execute(
                text("SET LOCAL request.jwt.claims = :claims"),
                {"claims": json.dumps(minimal_claims)},
            )
            yield session


async def _get_session_service_role() -> AsyncGenerator[AsyncSession, None]:
    """Session that bypasses RLS. Reserved for explicitly-marked admin paths.

    DO NOT use from a normal route. The only callers should decorate their
    endpoint with `@allow_service_role` so CI's dependency-graph test allows it.
    """
    async with AsyncSessionLocal() as session:
        async with session.begin():
            yield session
