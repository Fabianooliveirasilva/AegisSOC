# Handoff to the Implementation Model (Claude Sonnet)

You are the implementation engineer for AegisSOC. The architecture is owned by the approved documentation and the human maintainer. Preserve the design; maintain strict QA and security standards.

## 0. Preconditions — check before anything else

1. `docs/DECISIONS.md` → the sprint's scope decision **and** the go-ahead to implement are both **Approved** (Sprint 1: D-08 and D-10). `docs/ROADMAP.md` "Current sprint" must agree. If either is missing or they disagree, stop and ask the human. An approved *scope* alone does not authorise implementation.
2. `docs/DECISIONS.md` → every other decision marked blocking for your sprint (or for a task you are about to start, e.g. D-05 before S1-T13) has status **Approved**. If not, stop and list them.
3. ADRs relevant to your sprint have status **Accepted**. If an ADR you need is still *Proposed*, ask.

## 1. Reading order (first session of each sprint)

1. `CLAUDE.md`
2. `docs/ROADMAP.md` (your sprint section) and `docs/sprints/SPRINT_NN.md` (if it exists; for sprints without a detailed file, ask the Architect Agent/human to produce one from the roadmap before coding)
3. `docs/ACCEPTANCE_CRITERIA.md` — the ACs of your sprint
4. `docs/ARCHITECTURE.md`, then the relevant sections of `docs/SYSTEM_DESIGN.md`
5. `docs/DATABASE_DESIGN.md` and `docs/API_SPECIFICATION.md` — the parts your sprint touches
6. `SECURITY.md` and `docs/THREAT_MODEL.md` — the SR/T items in scope
7. `docs/QA_STRATEGY.md`, `docs/TEST_PLAN.md` (your TCs), `docs/DEFINITION_OF_DONE.md`
8. `docs/adr/*` relevant to your sprint
9. `docs/AGENT_SPECIFICATION.md`, `.claude/agents/`, `.claude/skills/`, `.claude/settings.json` (from Sprint 1 onward)

Then present to the human: the implementation sequence, dependencies, and anything missing or contradictory. **Start coding only after the human confirms.**

## 2. Rules

- Work only on the approved sprint. No future-sprint features, no placeholder screens for them.
- Do not invent architectural decisions. If the docs don't answer a question that changes what gets built: stop and ask. If it's a minor detail a sensible engineer could settle without changing the design: decide, and list it under "Decisions made" in your report.
- Architecture change control: explain the problem → propose the change → security and QA implications → draft/update ADR (status *Proposed*) → wait for approval when significant (anything that changes a component, boundary, data ownership, dependency, external integration, security control or API contract).
- Never weaken a test, threshold, gate or hardening flag to get green. Never mark a test skipped without the human's agreement.
- Never claim a test passed without running it; include the command and the relevant output.
- Synthetic data only. Never request or use real credentials or logs.
- For any Claude API / Anthropic SDK code (Sprint 5): consult the `claude-api` skill or the official SDK docs for exact call shapes before writing code; do not rely on memory.
- For library APIs (FastAPI, SQLAlchemy, pySigma, TanStack, Playwright): prefer current docs (Context7 if authorised) over memory.

## 3. Per-task workflow

1. Read the task in the sprint file; list its ACs/SRs/TCs.
2. Identify affected modules and check boundaries (import-linter).
3. Write or extend tests first where practical (`superpowers:test-driven-development` is available).
4. Implement the smallest coherent change.
5. Run: `make lint typecheck test-unit` and the relevant integration/API/E2E suites.
6. Analyse failures with evidence; fix; rerun; then run the regression set for touched areas.
7. Update docs (OpenAPI snapshot, README, DEPLOYMENT) when behaviour/config changes.
8. Invoke **QA Engineer** agent with: task ID, AC/SR/TC IDs, diff summary. Do **not** pass your own test conclusions.
9. Invoke **Security Reviewer** if the change touches auth, sessions, RBAC, ingestion, files, AI, infrastructure or CI.
10. Address findings; open the PR with the report below. The human merges.

## 4. Independence

You cannot approve your own work. A task is done only with a QA validation note `Accepted` (or `Accepted with minor defects` with S3/S4 bugs filed) and, where required, a Security review note without open High/Critical findings. S1/S2 defects block completion.

## 5. Commands

Defined by S1-T01 in the root `Makefile`. Until they exist, Sprint 1 tasks create them.

## 6. Report format (end of every task, also used as PR description body)

```markdown
## Task
S1-T06 — Authentication (AC-PLAT-01…05; SR-01…05)

## Implemented
- …

## Modified files
- apps/api/src/aegissoc/platform/auth/sessions.py — new
- …

## Decisions made (minor, within the design)
- …

## Architectural changes
- None | ADR-00NN proposed (link)

## Tests executed
| Command | Result |
|---|---|
| `make test-unit` | 142 passed, 0 failed (output excerpt below) |

## Security checks
| Tool | Result |
|---|---|
| bandit | 0 issues |
| semgrep | 0 findings |
| gitleaks | no leaks |

## QA validation
Link to QA note — status

## Known limitations
- …

## Documentation updates
- …

## Remaining tasks
- …
```

## 7. When you are blocked

Stop, state what is blocking, what you have tried, the options you see with trade-offs, and your recommendation. Wait for the human.
