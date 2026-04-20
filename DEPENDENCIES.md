# Dependencies

Exact version pins for the fast-churning parts of the stack, plus notes on what
to check before upgrading.

## Fast-churning (upgrade deliberately)

| Package | Pin | Why pinned |
|---|---|---|
| `tailwindcss` | `4.0.0` | v4 changed config format; check migration guide before upgrade |
| `react-router-dom` | `7.1.1` | v7 changed loader semantics and split package names |
| shadcn CLI pin | `2.1.0` | Registry layout + command syntax move; pin the CLI, not components |

## Backend core

| Package | Pin | Notes |
|---|---|---|
| `fastapi` | `>=0.115,<0.120` | |
| `sqlalchemy` | `>=2.0,<2.1` | 2.x async API; avoid 1.x-style patterns |
| `asyncpg` | `>=0.30,<0.31` | Use `statement_cache_size=0` when connecting via pgbouncer transaction mode |
| `alembic` | `>=1.13,<2.0` | |
| `pydantic` | `>=2.9,<3.0` | v2 is load-bearing; v1 compat is off |
| `pydantic-settings` | `>=2.5,<3.0` | |
| `pyjwt[crypto]` | `>=2.9,<3.0` | `algorithms=["RS256"]` must be pinned at call site |
| `structlog` | `>=24.4,<25.0` | |
| `slowapi` | `>=0.1.9,<0.2` | Key off `cf-connecting-ip`, not `request.client.host` |

## Frontend core

| Package | Pin | Notes |
|---|---|---|
| `react` | `18.3.x` | |
| `vite` | `5.4.x` | |
| `typescript` | `5.6.x` | |
| `@tanstack/react-query` | `5.x` | |
| `@supabase/supabase-js` | `2.45.x` | v3 is in preview as of 2026-04; hold until GA |
| `openapi-typescript` | `7.4.x` | Pin; output format changes between majors |
| `tailwindcss` | `4.0.0` | See table above |
| `eslint-plugin-boundaries` | `4.2.x` | Enforces the feature-slice mirror |

## CLI tools

| Tool | Pin |
|---|---|
| `uv` (Python installer) | `>=0.4` |
| `shadcn` CLI | `2.1.0` (see above) |
| Postgres image | `postgres:16.4-alpine` (digest pinned in `docker-compose.yml`) |

## Upgrade checklist

When bumping any pinned package:

1. Read the changelog for breaking changes (the three at the top break often)
2. Run `make test` and `make drift-check` locally
3. Update this file with the new pin and a one-line note on what changed
4. Commit the pin bump in a standalone commit so it can be reverted cleanly
