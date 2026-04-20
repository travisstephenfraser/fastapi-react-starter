-- Initial Postgres role setup for local docker-compose Postgres.
-- Supabase projects come with these roles pre-created; this script is only for
-- local parity.
--
-- Runs once on first container start (mounted in docker-compose.yml).

-- The `authenticated` role is what the app connects as after JWT verification.
-- It explicitly does NOT have BYPASSRLS.
CREATE ROLE authenticated NOLOGIN;

-- The Supabase convention: `authenticator` can log in and can SET ROLE to
-- `authenticated` or `anon`. Our app DSN connects as `authenticator`, then the
-- transaction-scoped `SET LOCAL role authenticated` switches.
CREATE ROLE authenticator WITH LOGIN PASSWORD 'starter_dev_password_change_me'
  NOINHERIT NOCREATEROLE NOCREATEDB;
GRANT authenticated TO authenticator;

-- Grants — adjust per feature. The example `items` migration adds its own.
GRANT USAGE ON SCHEMA public TO authenticated;

-- Mimic Supabase's `auth.uid()` function for local parity. On Supabase this is
-- provided by the `auth` extension; here it reads from `request.jwt.claims`
-- (set per-transaction by `get_db_with_claims`). Returns NULL when no claims
-- are set, which RLS policies using `user_id = auth.uid()` correctly reject.
CREATE SCHEMA IF NOT EXISTS auth;
CREATE OR REPLACE FUNCTION auth.uid() RETURNS uuid
  LANGUAGE sql STABLE
  AS $$
    SELECT (
      COALESCE(
        NULLIF(current_setting('request.jwt.claims', true), ''),
        '{}'
      )::jsonb->>'sub'
    )::uuid
  $$;

-- `authenticated` role needs to reach into the `auth` schema so RLS policies
-- that reference `auth.uid()` evaluate correctly.
GRANT USAGE ON SCHEMA auth TO authenticated;
GRANT EXECUTE ON FUNCTION auth.uid() TO authenticated;
