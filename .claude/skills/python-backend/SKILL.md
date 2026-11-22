---
name: python-backend
description: AegisSOC backend conventions. Use when writing or changing Python code under apps/api (package aegissoc) — FastAPI routes, Pydantic models, SQLAlchemy 2.0 async, Alembic migrations, Redis, structlog, the CLI — or tests for it.
---

# python-backend

Sources of truth: `docs/ARCHITECTURE.md` §3.2, `docs/diagrams/component-diagram.md`, `docs/SYSTEM_DESIGN.md`, `docs/DATABASE_DESIGN.md`, `docs/API_SPECIFICATION.md`, `SECURITY.md`, and the task in `docs/sprints/SPRINT_01.md`. When this skill and those documents disagree, the documents win; report the conflict.

## Stack
Python 3.12 managed by `uv` (committed lockfile), FastAPI, Pydantic v2, SQLAlchemy 2.0 async with asyncpg, Alembic, redis-py asyncio, structlog, argon2-cffi, stdlib `argparse` for the CLI. Do not add a runtime dependency without a justification and licence line in the PR (and the maintainer's approval, HC-2).

## Layout and boundaries
One package `aegissoc`; each module has `api.py` (HTTP only), `service.py` (public interface and logic), `models.py`, `schemas.py`, `repository.py`, and `workers.py` when it has consumers.
- A module writes only its own tables and never imports another module's `models` or `repository`; use the other module's `service`.
- `aegissoc.core` imports no other `aegissoc` package.
- import-linter contracts enforce this; keep `lint-imports` green.

## Rules
- **Every route declares exactly one permission** (`Depends(require(...))`) or the explicit `authenticated` marker. The only anonymous routes are `/auth/login` and `/health/*`. A test enumerates routes.
- Request and response models are strict (`extra="forbid"`), with explicit max lengths and collection sizes.
- Errors are RFC 9457 `application/problem+json` with `request_id`; never a stack trace, never a secret.
- SQL only through SQLAlchemy with bound parameters. No string-built SQL, no user-supplied identifiers.
- Pagination cursors are opaque, **not signed**, and strictly validated (SPRINT_01 S1-T03); invalid cursors return 400.
- Inject the clock (`Clock`) instead of calling `datetime.now()`; time-dependent behaviour must be testable with `FrozenClock`.
- Logging: structlog JSON; never log passwords, session IDs, CSRF tokens, API keys or `Authorization`/`Cookie` values. No `print`.
- Passwords: argon2id (m=64 MiB, t=3, p=4), compared in constant time, dummy verification for unknown users.
- Login throttling follows decision D-09: per-IP limit plus per-username progressive delay, **no hard lockout**.
- Audit every SR-17 action through `audit.service.record`; the application role cannot update or delete audit rows.
- `yaml.load`, `pickle`, `eval`, `subprocess(shell=True)` are forbidden (SR-13).
- Type-complete code: `mypy --strict` clean, no unjustified `Any` or `# type: ignore`.

## Migrations
Alembic, one linear history, `upgrade` and `downgrade` both implemented. Each migration docstring declares `data_loss: none | possible`. Validate with the cycle in `docs/SPRINT_01_EXECUTION_PROTOCOL.md` §6 (upgrade → validate → downgrade → upgrade) on the **disposable** test database only.

## Testing
Unit tests in `apps/api/tests/unit/` (mirroring the package layout); integration and API tests in `qa/` against the disposable database. Tag tests with the requirement they verify (`@pytest.mark.req("AC-PLAT-01")`). Write the test first where practical; never weaken a test or threshold to get green.

## Done when
`ruff check`, `ruff format --check`, `mypy --strict`, `lint-imports` and the mapped tests pass, with the commands and output recorded as evidence, and the QA Engineer (and Security Reviewer where required) have validated independently.
