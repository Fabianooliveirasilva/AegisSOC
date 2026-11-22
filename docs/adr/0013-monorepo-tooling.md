# ADR-0013: Monorepo with uv (Python) and pnpm workspaces (TypeScript)

- **Status:** Accepted (2026-11-21, decision D-06)
- **Date:** 2026-11-21

## Context
Backend, frontend, generator, E2E tests and detection content evolve together and are tested together.

## Decision
Single repository. Python projects (`apps/api`, `services/synthetic-generator`) managed with `uv` and committed lockfiles; TypeScript projects (`apps/web`, `qa/e2e`) as a pnpm workspace with one lockfile. Root `Makefile` is the task runner. Linting: ruff, mypy (strict), eslint, prettier; boundaries: import-linter.

## Alternatives considered
| Option | Pros | Cons |
|---|---|---|
| Poetry / pip-tools | Familiar | Slower; uv is faster with reproducible lock |
| npm/yarn | Default | pnpm stricter dependency isolation, faster |
| Nx/Turborepo | Caching, graphs | Overkill for 4 projects |

## Consequences
- CI caches keyed on `uv.lock` and `pnpm-lock.yaml`.
