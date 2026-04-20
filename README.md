# fastapi-react-starter

Opinionated starter for a FastAPI + Postgres + React + Vite app with JWT auth via Supabase, row-level security end-to-end, and typed contracts between frontend and backend.

Use it two ways:

1. **Greenfield project.** Clone, strip the example, ship.
2. **Strangler-fig sidecar** for a legacy Flask/SQLite app. Drop this FastAPI service alongside the legacy app, share a Postgres database, migrate features one at a time. See [`docs/strangler-fig.md`](docs/strangler-fig.md).

## Quickstart

```bash
git clone https://github.com/travisstephenfraser/fastapi-react-starter.git
cd fastapi-react-starter
make setup          # install deps, generate openapi.json + types
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
make db-up          # start local Postgres (or point at Supabase, see below)
make migrate        # apply schema + RLS policies
make dev            # backend on :8000, frontend on :5173
```

Open `http://localhost:5173`, sign up, create an item. That exercises the full path: React → FastAPI → Postgres with RLS scoping the query to the authenticated user.

## Stack

| Layer | Choice | Why |
|---|---|---|
| Backend framework | **FastAPI** | Async I/O, Pydantic at the boundary, auto OpenAPI |
| ORM | **SQLAlchemy 2.x async** + asyncpg | Mature, works with Alembic, no Supabase lock-in |
| Migrations | **Alembic** | Schema + RLS policies in one tool; no dashboard drift |
| Auth | **Supabase Auth** (JWT, validated via JWKS) | Frontend uses `@supabase/supabase-js`; backend verifies RS256 |
| Database | **Supabase Postgres** (default) or self-hosted Postgres | Row-level security enforces per-user scoping |
| Frontend framework | **React + Vite + TypeScript** | Fast dev loop, typed end-to-end |
| Router | **React Router v7** | Familiar |
| Server state | **TanStack Query** | Handles cache, invalidation, retries |
| Components | **shadcn/ui + Tailwind v4** | Code you own, not a framework dependency |
| Type bridge | **openapi-typescript** | Regenerates TS types from FastAPI's OpenAPI |

## Regulated data — read first

**Supabase Free is not a BAA-covered provider.** If you're handling HIPAA, FERPA, PHI, or similar regulated data, do **not** ship against Supabase Free. Two paths:

1. **Self-host Postgres.** `docker-compose.yml` works as a starting point; for production, use a managed Postgres with a BAA (AWS RDS, GCP Cloud SQL, Neon's enterprise tier) or your own Postgres on infrastructure under your BAA.
2. **Swap auth.** `@supabase/supabase-js` on the frontend assumes Supabase Auth; if you swap IdPs, you also replace `backend/app/core/jwt.py`'s issuer + JWKS URL with your provider's.

The template ships with `SUPABASE_URL` / `SUPABASE_ANON_KEY` wiring as the common case. Swap them; don't extend.

## The `items` example

The repo ships with an example `items` feature that exercises:

- FastAPI router with Pydantic request/response schemas
- SQLAlchemy async model + Alembic migration
- Row-level security enforcing `user_id = auth.uid()`
- React feature slice with TanStack Query hooks
- Typed API client (types auto-generated from backend OpenAPI)

**First thing to do in your fork:**

```bash
make clean-example
git add -A && git commit -m "chore: strip starter example"
```

That removes the `items/` slice from both backend and frontend and flips `TEMPLATE_EXAMPLE=0` in `.env.example`. Your app starts with `/health` + auth middleware + migrations framework and nothing else.

## Security notes

- **Never use Supabase's service-role key in the backend.** The template connects as a dedicated `authenticated` Postgres role and injects JWT claims per-request via `SET LOCAL request.jwt.claims`, so `auth.uid()` resolves correctly for RLS. If you need admin-level access, there is a separate `get_db_service_role` dependency gated behind an `@allow_service_role` marker — if you reach for it, write a comment explaining why.
- **`.env.example` lists only `SUPABASE_URL` and `SUPABASE_ANON_KEY`.** Service-role key handling is documented in `docs/admin-scripts.md` — kept out of the default env so it can't be copy-pasted into the app.
- **JWT verification pins `algorithms=["RS256"]`, `iss`, and `aud="authenticated"`.** Wrong-project tokens are rejected. Startup fetches JWKS once and fails fast if the project URL is mis-configured.
- **RLS policies live in Alembic migrations.** Supabase dashboard is read-only by convention. CI diffs locally-produced schema vs. `backend/schema.sql` and fails on unmanaged drift.

See [`docs/security.md`](docs/security.md) for the full list.

## Make targets

Run `make help` for the current list. Most common:

- `make setup` — install deps + codegen
- `make dev` — backend + frontend concurrently
- `make test` — both test suites
- `make migrate` — snapshot DB, then `alembic upgrade head`
- `make drift-check` — fails CI if `openapi.json` or `types/api.d.ts` is stale
- `make clean-example` — strip the `items` slice

## Contributing / adopting

- [`PORTING_NOTES.md`](PORTING_NOTES.md) — concept translation table for Flask + SQLite apps
- [`docs/strangler-fig.md`](docs/strangler-fig.md) — running this next to a legacy app
- [`DEPENDENCIES.md`](DEPENDENCIES.md) — version pins and what moves fast

## License

MIT.
