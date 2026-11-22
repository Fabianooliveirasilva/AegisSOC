# AegisSOC developer entrypoint (S1-T01). See docs/DEVSECOPS.md section 5.
# Targets for later sprints print "available from Sprint N" and exit 0.

SHELL := /bin/sh
export PATH := $(HOME)/.local/bin:$(PATH)

COMPOSE_FILE := infrastructure/compose/compose.yaml
COMPOSE      := docker compose -p aegissoc -f $(COMPOSE_FILE)
API_DIR      := apps/api
WEB_DIR      := apps/web
GITLEAKS_IMG := ghcr.io/gitleaks/gitleaks:v8.30.1

# Fixed, relative cache locations removed by `make clean` (never secrets or volumes).
CLEAN_PATHS := $(API_DIR)/.ruff_cache $(API_DIR)/.mypy_cache $(API_DIR)/.pytest_cache \
               $(API_DIR)/htmlcov $(API_DIR)/.coverage $(API_DIR)/coverage.xml \
               .ruff_cache .mypy_cache .pytest_cache

.DEFAULT_GOAL := help

.PHONY: help setup setup-ci bootstrap-admin up down logs psql trust-ca seed \
        test-unit test-integration test-api test-e2e test-detections \
        lint typecheck scan openapi docs-check traceability demo-data \
        backup restore reset upgrade clean \
        _hooks _need-compose _need-api

help: ## List targets
	@grep -hE '^[a-zA-Z0-9_-]+:.*## ' $(MAKEFILE_LIST) | awk -F ':.*## ' '{printf "  %-18s %s\n", $$1, $$2}'

# ---- setup (host only; no containers) ------------------------------------

setup: ## Check prerequisites, install pre-commit hooks, generate secrets (no users)
	@scripts/check-prereqs
	@$(MAKE) --no-print-directory _hooks
	@scripts/setup-secrets

setup-ci: ## Same as setup, plus bootstrap_admin_password (CI only)
	@scripts/check-prereqs
	@$(MAKE) --no-print-directory _hooks
	@scripts/setup-secrets --ci

_hooks:
	@pre-commit install --install-hooks

bootstrap-admin: _need-compose ## Create the first admin (password prompted, no echo)
	$(COMPOSE) exec -it api aegissoc admin create --username admin

# ---- stack (core arrives with S1-T12) -------------------------------------

_need-compose:
	@test -f $(COMPOSE_FILE) || { echo "$(COMPOSE_FILE) not present yet (arrives with S1-T12/T12a)"; exit 1; }

up: _need-compose ## Start the core stack and wait for healthchecks
	$(COMPOSE) up -d --build --wait

down: _need-compose ## Stop the stack (keeps volumes)
	$(COMPOSE) down

logs: _need-compose ## Follow logs (SERVICE=name to filter)
	$(COMPOSE) logs -f $(SERVICE)

psql: _need-compose ## psql as the application role inside the postgres container
	$(COMPOSE) exec postgres sh -c 'PGPASSWORD="$$(cat /run/secrets/postgres_app_password)" psql -U aegis_app -d aegissoc'

trust-ca: ## Trust Caddy's local CA
	@echo "trust-ca: available from Sprint 1 stretch (after S1-T12)"

seed: ## Seed demo data
	@echo "seed: available from Sprint 2"

demo-data: ## Generator baseline + storylines
	@echo "demo-data: available from Sprint 2"

# ---- quality --------------------------------------------------------------

_need-api:
	@test -f $(API_DIR)/pyproject.toml || { echo "$(API_DIR)/pyproject.toml not present yet (arrives with S1-T02)"; exit 1; }

test-unit: _need-api ## Backend unit tests (+ web unit tests when present)
	cd $(API_DIR) && uv run pytest tests/unit
	@if [ -f $(WEB_DIR)/package.json ]; then pnpm --filter ./$(WEB_DIR) --if-present run test; fi

test-integration: _need-api ## Backend integration tests (needs the disposable test DB, S1-T12a)
	cd $(API_DIR) && uv run pytest tests/integration

test-api: ## API contract/security tests (qa/api)
	@echo "test-api: available from Sprint 1 (after S1-T06)"

test-e2e: ## Playwright end-to-end smoke
	@echo "test-e2e: available from Sprint 1 (after S1-T11)"

test-detections: ## Detection rule tests
	@echo "test-detections: available from Sprint 3"

lint: ## ruff + prettier via pre-commit hooks
	@if [ -f $(API_DIR)/pyproject.toml ]; then cd $(API_DIR) && uv run ruff check . && uv run ruff format --check .; else echo "lint: $(API_DIR) not present yet (S1-T02); running pre-commit only"; fi
	pre-commit run --all-files

typecheck: ## mypy + import-linter (+ tsc when web exists)
	@if [ -f $(API_DIR)/pyproject.toml ]; then cd $(API_DIR) && uv run mypy && uv run lint-imports; else echo "typecheck: $(API_DIR) not present yet (arrives with S1-T02)"; fi
	@if [ -f $(WEB_DIR)/package.json ]; then pnpm --filter ./$(WEB_DIR) --if-present run typecheck; fi

scan: ## Secret scan now; Semgrep/Trivy from container images after S1-T13
	docker run --rm -v "$(CURDIR):/repo:ro" $(GITLEAKS_IMG) dir /repo --redact --no-banner
	@echo "scan: Semgrep and Trivy stages are available after S1-T13"

openapi: ## Regenerate docs/api/openapi.json
	@echo "openapi: available after S1-T10"

docs-check: ## Link and ID checks for docs
	@echo "docs-check: available from Sprint 1 (S1-T16)"

traceability: ## AC/SR to TC matrix
	@echo "traceability: available from Sprint 2"

backup: ## pg_dump + evidence archive
	@echo "backup: available from Sprint 6"

restore: ## Restore from FILE=...
	@echo "restore: available from Sprint 6"

upgrade: ## Pull/build, migrate, restart
	@echo "upgrade: available from Sprint 6"

reset: ## Destroy volumes (confirmation) and reseed
	@echo "reset: not implemented yet (destructive; arrives with S1-T12 with a confirmation prompt)"

clean: ## Remove local caches and coverage artefacts (never secrets or volumes)
	@for p in $(CLEAN_PATHS); do \
	  if [ -e "$$p" ]; then rm -r -- "$$p" && echo "removed $$p"; fi; \
	done
