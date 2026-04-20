# Running This Alongside a Legacy App (Strangler Fig)

Most real migrations are not migrations. They are **strangler-fig adoptions** — the legacy app keeps running, this FastAPI service lands next to it, they share a Postgres database, and features move across one at a time. Over months, the legacy app's surface area shrinks until it can be retired.

This doc is the opinionated version: what not to do, and four non-negotiables that keep two apps on one DB from destroying each other.

## The topology

```
       ┌────────────────────┐     ┌────────────────────┐
       │  Legacy Flask app  │     │  FastAPI (this)    │
       │  (port 5000)       │     │  (port 8000)       │
       └─────────┬──────────┘     └─────────┬──────────┘
                 │                          │
                 │  reads/writes            │  reads/writes
                 ▼                          ▼
               ┌──────────────────────────────┐
               │  Postgres                    │
               │  (shared, one source of      │
               │   truth; RLS enforces        │
               │   boundaries)                │
               └──────────────────────────────┘
```

The legacy app and this app never talk to each other over HTTP. They talk through the database. Row-level security is the boundary.

## The four non-negotiables

Skip any of these and the setup silently corrupts data within weeks.

### 1. One migration tool owns the DB

Alembic (in this repo) owns schema. **The legacy app's migration tool is read-only on tables it used to manage.** No parallel `alembic_version` table, no "let me just add one column" via the legacy app's tooling.

Practical enforcement:

- The legacy app connects as a Postgres role that has `SELECT` on all tables it reads and `INSERT/UPDATE/DELETE` only on the specific tables it still owns.
- That role has `USAGE` on the schema but **not** `CREATE`.
- New tables are added via Alembic in this repo. Period.

If the legacy app's ORM auto-creates tables on boot (Flask-SQLAlchemy with `db.create_all()`), **remove that call immediately** before either app touches production. The boot path becomes silent schema mutation otherwise.

### 2. Shared tables get a `source` column

Every table that both apps write to carries:

```sql
source TEXT NOT NULL CHECK (source IN ('legacy', 'fastapi'))
```

Every write sets it. This is not for correctness — RLS handles that. It is for **auditing**: when a row looks wrong, you need to know which code path wrote it. Without this column, every incident becomes a forensic database dive.

Backfill existing rows as `'legacy'` in a one-off migration before this app writes anything.

### 3. Legacy uses a DB role that RLS denies on FastAPI-owned tables

The legacy app does **not** connect as `authenticated` with claims. It connects as a distinct Postgres role (`legacy_app`) whose grants are explicit: `SELECT/INSERT/UPDATE/DELETE` on the tables it owns, `SELECT` on tables it reads from FastAPI-land, nothing else.

On tables FastAPI fully owns (new features moved across), RLS policies include:

```sql
CREATE POLICY "deny_legacy_writes" ON new_feature_table
  FOR INSERT, UPDATE, DELETE
  TO legacy_app
  USING (false)
  WITH CHECK (false);
```

This makes "accidentally ported a feature half-way and the legacy app still writes to its table" impossible, not just unlikely.

### 4. Document the cutover order in `docs/adoption-plan.md` (per-app)

This template does not ship a cutover plan because the cutover order depends on your app. Create `docs/adoption-plan.md` in your fork with:

- **Feature inventory** — every Flask route, classified as `stay` / `port` / `drop`
- **Sequence** — which feature moves first and why (usually: highest-value + lowest-coupling, not the feature you're most tired of)
- **Shared-table boundary** — which tables are co-owned during the overlap, which are owned by which app, and when ownership flips
- **Rollback criteria** — what would make you roll back a ported feature, and how (the legacy app's route stays code-alive behind a feature flag until the rollback window closes)

Without this file, the adoption drifts. With it, every review has an artifact to argue with.

## How a feature moves

The canonical port:

1. **Pick a feature** with well-defined input/output and few cross-feature dependencies.
2. **Write the FastAPI feature slice** — model, schema, router, RLS policies, tests. Ship to prod behind a route that does not replace the legacy route yet.
3. **Dual-write for a week.** Both apps' writes land in Postgres. The FastAPI version reads from the same tables; responses match.
4. **Divert reads.** Frontend (or an edge proxy) starts calling the FastAPI route for reads. Legacy route keeps responding but is no longer the canonical reader.
5. **Divert writes.** Frontend calls the FastAPI route for writes. Legacy route returns `410 Gone` or a 301 to the new route.
6. **Delete the legacy route.** Not immediately — wait until logs show zero traffic for a week, then remove.
7. **Tighten RLS.** Update the `deny_legacy_writes` policy to include this table.

If a feature fails dual-write or divert-reads, revert in one step (remove the frontend routing change) and diagnose.

## Operational reality

Two apps on one database introduce failure modes neither app has alone:

- **Connection pool pressure.** Supabase Free has 60 direct connections; a pooler helps. Size each app's pool conservatively and use transaction-mode pooling.
- **Migrations during traffic.** `alembic upgrade` during live traffic can lock tables. Use the **expand-migrate-contract** pattern: add new columns nullable, deploy code that writes both old and new, backfill, deploy code that reads new, drop old column in a later migration. `make db-snapshot` before every migration; Free tier has no point-in-time restore.
- **Time-zone drift.** Legacy Python 2-style `datetime` (naive, no tz) vs. FastAPI's tz-aware pattern — pick `TIMESTAMPTZ` in Postgres and UTC at every boundary. Document it once, enforce it.
- **Session vs. JWT during overlap.** Legacy app's users have Flask sessions; FastAPI's users have JWTs. For a period, users may be "signed in" on one but not the other. Ship a `/session-to-jwt` bridge endpoint on the FastAPI side (reads the legacy session cookie, issues a Supabase-compatible JWT) to make the transition seamless. Remove it when the legacy auth surface is gone.

## When to abandon strangler fig

Adoption via strangler fig is the right move when:

- Legacy app is in production with real users
- Downtime is expensive
- The rewrite would take longer than the dual-run

It is the wrong move when:

- Legacy app is a pre-production prototype (just rewrite)
- Legacy schema is so tangled that dual-write produces data loss (simpler to dump, transform, load into this template fresh)
- You are the sole user and can take a weekend offline (rewrite is faster than engineering the bridge)

The honest question is: how many weeks of bridge-engineering would let you avoid the rewrite? If the answer is less than the rewrite's worst-case, strangler fig. Otherwise, rewrite.
