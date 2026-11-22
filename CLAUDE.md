# CLAUDE.md — AegisSOC project rules

Read [docs/HANDOFF_SONNET.md](docs/HANDOFF_SONNET.md) before doing any implementation work. It defines the reading order, workflow and reporting format.

## Non-negotiables

- Work only on the sprint the human has approved. Current sprint is recorded in [docs/ROADMAP.md](docs/ROADMAP.md) ("Current sprint").
- Human decisions live in [docs/DECISIONS.md](docs/DECISIONS.md). A decision is binding only when its status is **Approved**.
- Do not change an architectural decision silently. Propose an ADR change in `docs/adr/` and wait for approval when it is significant (see ADR-0001).
- Never claim a test passed without running it and showing the output.
- The developer never approves their own work: QA validation and security review happen as separate agent passes (see [docs/AGENT_SPECIFICATION.md](docs/AGENT_SPECIFICATION.md)).
- Defensive only. Synthetic data only. No real credentials, no real logs.
- Never commit secrets. `.env` files are git-ignored; use `.env.example` with placeholders.
- Adding a runtime dependency requires a line in the PR description justifying it and a licence check.

## Where things live

- Backend: `apps/api` (Python 3.12, FastAPI, package `aegissoc`). API and worker are the same codebase, different entrypoints.
- Frontend: `apps/web` (React + TypeScript + Vite).
- Detection content: `detections/` (Sigma rules, correlation rules, scenarios).
- Tests outside unit level: `qa/`. Unit tests live next to the code they test (`apps/api/tests/unit`, `apps/web/src/**/*.test.tsx`).
- Requirement IDs: `AC-*` in [docs/ACCEPTANCE_CRITERIA.md](docs/ACCEPTANCE_CRITERIA.md); security requirements `SR-*` in [SECURITY.md](SECURITY.md); threats `T-*` in [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md); test cases `TC-*` in [docs/TEST_PLAN.md](docs/TEST_PLAN.md). Reference these IDs in commits, tests and PRs.

## Commands (available from Sprint 1)

Defined in Sprint 1 task S1-T01 (`Makefile` at repo root). Until then there is nothing to run.
