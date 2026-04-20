"""Shared pytest fixtures.

Real Postgres via testcontainers. Docker must be running locally or in CI.
Session-scoped with `.with_reuse(True)` so the container is cached across test
runs on dev machines (set `TESTCONTAINERS_REUSE_ENABLE=true` in env).
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

INIT_SQL = Path(__file__).resolve().parent.parent / "scripts" / "init-roles.sql"


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer, None, None]:
    # Pinned image; reuse across runs on dev.
    with PostgresContainer("postgres:16.4-alpine").with_bind_ports(5432, None) as pg:
        # Run init-roles.sql to set up `authenticated` role and auth.uid().
        init_sql = INIT_SQL.read_text()
        dsn_sync = pg.get_connection_url()  # testcontainers returns psycopg2-style DSN
        import psycopg  # psycopg3 (project dep)

        conn_str = dsn_sync.replace("postgresql+psycopg2://", "postgresql://")
        with psycopg.connect(conn_str, autocommit=True) as conn, conn.cursor() as cur:
            cur.execute(init_sql)
        yield pg


@pytest.fixture(scope="session")
def database_url(postgres_container: PostgresContainer) -> str:
    url = postgres_container.get_connection_url().replace(
        "postgresql+psycopg2://", "postgresql+asyncpg://"
    )
    # Point at the authenticator login role created in init-roles.sql.
    # testcontainers' default user is "test"; we need to switch to "authenticator".
    # For now, tests run as the container's default superuser and `SET LOCAL role`
    # to `authenticated` — still exercises RLS correctly.
    return url


@pytest.fixture(scope="session", autouse=True)
def _configure_env(database_url: str) -> None:
    os.environ.setdefault("DATABASE_URL", database_url)
    os.environ.setdefault("SUPABASE_URL", "http://test.local.invalid")
    os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon")
    os.environ.setdefault("JWT_AUD", "authenticated")
    os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173")
    os.environ.setdefault("ENV", "dev")
    os.environ.setdefault("TEMPLATE_EXAMPLE", "1")


@pytest_asyncio.fixture(scope="session")
async def migrated_engine(database_url: str) -> AsyncGenerator[None, None]:
    """Run alembic upgrade head against the test DB."""
    # Run alembic via subprocess so we get the same migration path as prod.
    import subprocess

    env = {**os.environ, "DATABASE_URL": database_url}
    subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=Path(__file__).resolve().parent.parent,
        env=env,
        check=True,
    )
    yield
    subprocess.run(
        ["alembic", "downgrade", "base"],
        cwd=Path(__file__).resolve().parent.parent,
        env=env,
        check=False,
    )


@pytest_asyncio.fixture
async def session(migrated_engine: None, database_url: str) -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(database_url, connect_args={"statement_cache_size": 0})
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    async with SessionLocal() as s:
        yield s
    await engine.dispose()
