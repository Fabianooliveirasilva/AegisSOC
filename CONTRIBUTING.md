# Contributing to AegisSOC

## Workflow

1. Every change starts from a roadmap task ID (e.g. `S2-T04`) and the requirement IDs it implements (`AC-SIEM-03`).
2. Branch from `main`: `feat/S2-T04-normaliser-linux-auth`, `fix/…`, `docs/…`, `chore/…`.
3. Commits follow [Conventional Commits](https://www.conventionalcommits.org/): `feat(siem): parse linux auth logs (AC-SIEM-03)`.
4. Open a pull request using the template. CI must be green; all blocking gates in [docs/DEVSECOPS.md](docs/DEVSECOPS.md) must pass.
5. A PR needs: an independent QA validation note, a security review note for any change touching auth, ingestion, file handling, AI or infrastructure, and human approval. The author cannot provide their own QA sign-off.
6. Squash-merge to `main`.

## Coding standards

- Python: `ruff` (lint + format), `mypy --strict` for `aegissoc`, type hints everywhere, no bare `except`, no `print`.
- TypeScript: `strict: true`, ESLint + Prettier, no `any` without a justifying comment, no `dangerouslySetInnerHTML`.
- SQL only through SQLAlchemy Core/ORM with bound parameters. No string-built SQL.
- Tests are part of the change, not a follow-up.

## Detection content

Detection rules follow the lifecycle in [docs/SYSTEM_DESIGN.md §4](docs/SYSTEM_DESIGN.md#4-module-b--detection-engineering). A rule PR must include at least one positive and one negative scenario.

## Architecture changes

Use [docs/adr/0000-template.md](docs/adr/0000-template.md). Significant changes need human approval before implementation.
