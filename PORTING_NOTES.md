# Porting Notes — Flask + SQLite → FastAPI + Postgres + React

This file is a **concept translation table**, not a step-by-step migration guide. Your app's cutover order is yours to decide; this document tells you what each Flask idea maps to on this stack so you don't have to discover it twice.

For running a legacy Flask app and this FastAPI service side-by-side on one database, see [`docs/strangler-fig.md`](docs/strangler-fig.md).

## Concept map

| Flask | FastAPI + this template | Notes |
|---|---|---|
| `Flask(__name__)` | `FastAPI(title=..., docs_url=None if prod)` | `/docs` must be gated by env |
| `Blueprint("items", __name__)` | `APIRouter(prefix="/items", tags=["items"])` in `app/features/items/router.py` | One router per feature; feature-slice layout |
| `@app.route("/items", methods=["GET"])` | `@router.get("/items", response_model=ItemOut)` | Response model drives OpenAPI + TS types |
| `request.get_json()` | Typed Pydantic body: `payload: ItemCreate` | Validation at the boundary, no manual schema check |
| `g.db` (Flask-SQLAlchemy session) | `db: AsyncSession = Depends(get_db_with_claims)` | Scoped per-request; transaction-wrapped |
| `flask-login` / `@login_required` / `current_user` | `user: dict = Depends(get_current_user)` | JWT verified against Supabase JWKS |
| `session["user_id"]` (server-side session) | No server-side session — JWT is the source of truth | JWT in `Authorization: Bearer` header |
| `flash("saved")` | Return structured JSON; render a `toast` on the client | `components/ui/toast.tsx` wraps it |
| Jinja template (`render_template("items.html")`) | React route returning JSX | Data fetched via TanStack Query |
| `url_for("items.show", id=x)` | `useNavigate()` + `<Link to={`/items/${x}`}>` | React Router v7 |
| `@app.errorhandler(404)` | `@app.exception_handler(HTTPException)` or Pydantic `ValidationError` handler | |
| Flask-Migrate / Alembic (same) | **Alembic** | RLS policies live inside migrations (`op.execute`), not a parallel SQL file |
| SQLAlchemy 1.x sync (`db.session`) | SQLAlchemy 2.x async (`async with session.begin():`) | Style shift; see below |
| `request.form["x"]` | Rarely needed — API is JSON. For file uploads, `file: UploadFile = File(...)` | |
| `render_template` with template inheritance | React layouts: a `<Root/>` component wrapping `<Outlet/>` | |

## SQLAlchemy sync → async

The biggest sharp edge. Sync code that "just worked" under Flask becomes an async bug magnet if ported literally.

| Sync | Async | Notes |
|---|---|---|
| `db.session.query(Item).filter(...).all()` | `result = await session.execute(select(Item).where(...)); items = result.scalars().all()` | `Query` is legacy in 2.x; prefer `select()` |
| `db.session.add(x); db.session.commit()` | `session.add(x); await session.commit()` | Commit is awaited; flushes are implicit inside a transaction |
| `Model.query.get(id)` | `await session.get(Model, id)` | |
| `with db.session.begin():` | `async with session.begin():` | |
| Synchronous helper called from a view | `run_in_threadpool(sync_fn, ...)` | `from starlette.concurrency import run_in_threadpool` |

**Gotcha:** a blocking call (`requests.get`, `time.sleep`, raw `open()`, `boto3`) inside an async route handler blocks the entire event loop. The template ships a lint rule forbidding known-sync libraries in `app/features/*/router.py`; `run_in_threadpool` is the escape hatch.

## SQLite → Postgres gotchas

Five things that bite during port:

1. **Case sensitivity.** SQLite is case-insensitive in identifier collation by default; Postgres is case-sensitive. `SELECT * FROM Items` fails if you created `items`.
2. **`AUTOINCREMENT` / `INTEGER PRIMARY KEY`.** Replace with `BigInteger` + `Sequence` / `Identity`, or use `uuid_v4()`. SQLAlchemy models translate — pay attention during model review.
3. **Dates.** SQLite stores dates as ISO strings; Postgres has real `TIMESTAMP` / `TIMESTAMPTZ`. Queries using string comparison on dates silently work in SQLite and break in Postgres. Always `TIMESTAMPTZ`.
4. **Booleans.** SQLite treats `0`/`1` as booleans; Postgres wants `TRUE`/`FALSE`. SQLAlchemy 2.x handles this, but raw SQL migrated from SQLite won't.
5. **`INSERT OR REPLACE`.** Postgres uses `INSERT ... ON CONFLICT ... DO UPDATE`. Any SQLite-specific upsert needs rewriting.

## Auth migration

Flask apps typically use server-side sessions (`flask-login`, `flask-session`). This template uses stateless JWT:

- Frontend signs in via `supabase.auth.signInWithPassword(...)` → Supabase issues an RS256 JWT.
- The JWT goes to the backend as `Authorization: Bearer ...`.
- `get_current_user` verifies it against Supabase's JWKS and returns the claims dict.
- `get_db_with_claims` additionally injects `request.jwt.claims` as a Postgres `SET LOCAL` so RLS sees the right `auth.uid()`.

**Porting a Flask session-based app:**

1. Move user rows from your Flask `users` table into Supabase Auth (Supabase provides a CSV import). Keep the same UUIDs if you can — RLS policies will reference them.
2. Replace `@login_required` with `Depends(get_current_user)`.
3. Replace `current_user.id` with `user["sub"]`.
4. Add a `user_id UUID` column to every user-scoped table if you don't have one already. Add an RLS policy `USING (user_id = auth.uid())`.
5. In the frontend, replace form-posts to `/login` with the Supabase JS client.

## What does *not* port cleanly

Be honest with yourself:

- **Large single-file Flask apps** (anything over ~1000 lines in one `app.py`) do not "port" — they get rewritten feature by feature using the strangler-fig pattern. See `docs/strangler-fig.md`.
- **Jinja templates with heavy server-side logic** — the data model behind them is the thing that ports; the view layer is a rewrite in React.
- **Custom Flask extensions** — usually easier to replace with a FastAPI dependency than port. Rate limiting → `slowapi`. File uploads → `UploadFile`. Background jobs → your existing queue (Celery, RQ, or something new like Arq if you're starting fresh).

When in doubt, do not migrate — run the legacy app alongside this one, share the database, and migrate one feature at a time.
