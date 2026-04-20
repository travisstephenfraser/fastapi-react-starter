# fastapi-react-starter — orchestration
#
# Cross-dir targets for a monorepo with `backend/` + `frontend/` siblings.
# Windows: use Git Bash or WSL; plain `make` from cmd.exe will not work.

SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c

.PHONY: help setup dev test lint format \
	be-install be-dev be-test be-lint \
	fe-install fe-dev fe-test fe-lint \
	openapi types drift-check \
	db-up db-down db-snapshot migrate \
	shadcn-add clean-example

help:
	@echo "Top-level targets"
	@echo "  setup          install backend + frontend deps, then run openapi + types"
	@echo "  dev            run backend and frontend dev servers concurrently"
	@echo "  test           run backend and frontend tests"
	@echo "  lint           run ruff, mypy, eslint, prettier --check"
	@echo "  format         ruff format + prettier --write"
	@echo ""
	@echo "Codegen / contracts"
	@echo "  openapi        dump backend/openapi.json (no server needed)"
	@echo "  types          regenerate frontend/src/types/api.d.ts from openapi.json"
	@echo "  drift-check    fail if openapi.json or api.d.ts is stale"
	@echo ""
	@echo "Database"
	@echo "  db-up          start docker-compose Postgres"
	@echo "  db-down        stop docker-compose Postgres"
	@echo "  db-snapshot    pg_dump --schema-only to backend/snapshots/ before migrating"
	@echo "  migrate        alembic upgrade head (snapshots first)"
	@echo ""
	@echo "Scoped"
	@echo "  be-install | be-dev | be-test | be-lint"
	@echo "  fe-install | fe-dev | fe-test | fe-lint"
	@echo ""
	@echo "Template hygiene"
	@echo "  clean-example  remove the items example slice and flip TEMPLATE_EXAMPLE=0"
	@echo "  shadcn-add NAME=x  add a shadcn component via the pinned CLI"

# -----------------------------------------------------------------------------
# Top-level

setup: be-install fe-install openapi types
	@echo "Setup complete. Run 'make dev' to start both servers."

dev:
	@echo "Starting backend and frontend. Ctrl-C stops both."
	@trap 'kill 0' EXIT; \
		( cd backend && uv run uvicorn app.main:app --reload --port 8000 ) & \
		( cd frontend && npm run dev ) & \
		wait

test: be-test fe-test
lint: be-lint fe-lint
format:
	cd backend && uv run ruff format .
	cd frontend && npm run format

# -----------------------------------------------------------------------------
# Backend

be-install:
	cd backend && uv sync

be-dev:
	cd backend && uv run uvicorn app.main:app --reload --port 8000

be-test:
	cd backend && uv run pytest -q

be-lint:
	cd backend && uv run ruff check . && uv run mypy app

# -----------------------------------------------------------------------------
# Frontend

fe-install:
	cd frontend && npm ci

fe-dev:
	cd frontend && npm run dev

fe-test:
	cd frontend && npm run test

fe-lint:
	cd frontend && npm run lint

# -----------------------------------------------------------------------------
# Codegen

openapi:
	cd backend && uv run python scripts/export_openapi.py

types: openapi
	cd frontend && npm run gen:types

drift-check:
	@# Regenerate into tempfiles and fail on any diff against committed files.
	@tmp_openapi=$$(mktemp); tmp_types=$$(mktemp); \
		( cd backend && uv run python scripts/export_openapi.py --stdout ) > $$tmp_openapi; \
		diff -u backend/openapi.json $$tmp_openapi || { echo "openapi.json is stale — run 'make openapi'"; exit 1; }; \
		( cd frontend && npx --no-install openapi-typescript ../backend/openapi.json ) > $$tmp_types; \
		diff -u frontend/src/types/api.d.ts $$tmp_types || { echo "types/api.d.ts is stale — run 'make types'"; exit 1; }; \
		echo "drift check OK"

# -----------------------------------------------------------------------------
# Database

db-up:
	docker compose up -d postgres

db-down:
	docker compose down

db-snapshot:
	@mkdir -p backend/snapshots
	@ts=$$(date +%Y%m%d-%H%M%S); \
		cd backend && \
		uv run python -c "from app.core.config import settings; print(settings.database_url_sync)" | xargs -I{} pg_dump --schema-only -d {} -f snapshots/schema-$$ts.sql; \
		echo "snapshot → backend/snapshots/schema-$$ts.sql"

migrate: db-snapshot
	cd backend && uv run alembic upgrade head

# -----------------------------------------------------------------------------
# Template hygiene

clean-example:
	@echo "Removing items example slice..."
	rm -rf backend/app/features/items
	rm -f backend/alembic/versions/0001_items_example.py
	rm -rf frontend/src/features/items frontend/src/pages/Items.tsx
	@# Flip the flag in .env.example so new clones don't inherit the example wiring.
	sed -i.bak 's/TEMPLATE_EXAMPLE=1/TEMPLATE_EXAMPLE=0/' backend/.env.example && rm backend/.env.example.bak
	@echo "Done. Commit the removal: git add -A && git commit -m 'chore: strip starter example'"

shadcn-add:
	@if [ -z "$(NAME)" ]; then echo "Usage: make shadcn-add NAME=<component>"; exit 1; fi
	cd frontend && npx shadcn@$$(cat ../DEPENDENCIES.md | grep 'shadcn CLI pin:' | awk '{print $$4}') add $(NAME)
