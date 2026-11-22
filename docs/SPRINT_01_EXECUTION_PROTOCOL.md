# Sprint 1 — Execution Protocol

| | |
|---|---|
| Date | 2026-11-21 (revision 2 after consistency review — see [SPRINT_01_PROTOCOL_REVIEW.md](SPRINT_01_PROTOCOL_REVIEW.md); §5.2 and §7 synced with the guardrails implemented in PR1) |
| Author | Claude Opus (architect / governance) |
| Applies to | S1-T01 … S1-T16 as specified in [sprints/SPRINT_01.md](sprints/SPRINT_01.md) |
| Status | **In effect — D-10 approved 2026-11-21** (Sonnet implements; T12a acknowledged; conditions in [DECISIONS.md](DECISIONS.md)). D-05 still open: S1-T13 cannot complete without it. |

> **Implementation remains unauthorised until the maintainer records D-10 as *Approved* in [DECISIONS.md](DECISIONS.md).** No agent — Sonnet, Opus or any subagent — may create application code, Dockerfiles, workflows or infrastructure before that. This document authorises nothing and changes no decision, ADR or acceptance criterion.

---

## 1. Current approval state (verified in DECISIONS.md, 2026-11-21)

| Item | State |
|---|---|
| Planning baseline | Approved |
| ADR-0001 … ADR-0016 | Accepted (D-06) |
| Sprint 1 scope | Approved (D-08) |
| Login throttling policy | Approved (D-09) |
| **D-10 — start of implementation** | **Open** |
| **D-05 — GitHub repository** | **Open** |
| Sprints 2–5 | Not approved; Sprint 2 needs re-planning (M-5) |
| Repository | git initialised, **no commits**; no `.claude/`, no `.mcp.json`, `.github/workflows/` empty |

## 2. D-05 and D-10 requirements

### D-10 — go-ahead for implementation
- **Required before any task.** Nothing in §3 may start while D-10 is open.
- **Recorded how:** the maintainer states approval explicitly; the row moves to *Approved* in DECISIONS.md with date and source, and ROADMAP "Current sprint" becomes "Sprint 1 — in progress".
- **The approval should state:**
  1. which model runs the implementation session — Sonnet per this protocol (note: the D-10 row text says "Sonnet or Opus"; see review U-1);
  2. whether the implementer may create **local commits on feature branches** (recommended: yes; merging into `main` and pushing stay human-only);
  3. whether work may start before D-05 is done (§2, D-05);
  4. acknowledgement of correction C-4, which pulls the disposable test data services forward as S1-T12a (§3).

  Suggested wording: *"D-10 approved: Sonnet may implement Sprint 1 per SPRINT_01_EXECUTION_PROTOCOL.md rev. 2, committing on local feature branches only; merges to main and pushes are mine."*

### D-05 — GitHub repository
- **What the maintainer must do:**
  1. create the repository and choose visibility (recommended: private now, public at `v0.5.0`);
  2. add it as `origin` and push the planning-baseline commit (agents are denied `git push`);
  3. enable GitHub Actions, Dependabot alerts and updates, and private vulnerability reporting;
  4. after the first CI run, protect `main`: PR required, the blocking CI checks required, linear history, no force pushes.
- **Tasks that require D-05:**

| Task | What needs GitHub | What can be done before D-05 |
|---|---|---|
| **S1-T13** (CI) | Running `ci.yml` on Actions; Dependabot; branch protection; the canary PR proving the gates block (TC-PLAT-13, AC-PLAT-16) | Write `ci.yml`, `dependabot.yml`, scanner configs; lint with `actionlint`; run every scanner locally with `make scan` |
| **S1-T14** — CI evidence part | Suites passing **in CI**; CI run links in the QA report | All local test execution and evidence |
| **S1-T16** — closing part | Security review of the CI configuration *as executed* | Everything else |
| **Sprint 1 acceptance** | AC-PLAT-16 can only be met with D-05 | — |
| *(optional)* GitHub MCP (D-07) | A repository to scope the token to | — |

- **Tasks that do not need D-05:** S1-T15, T01, T02, T03, T04, T05, T06, T07, T08, T09, T10, T11, T12a, T12, and the local parts of T13, T14 and T16.
- **Without D-05, the PR workflow is local:** each change lives on a local feature branch, QA and Security notes are written to files, and the maintainer reviews with `git diff main...<branch>` and merges locally.
- **Recommendation:** complete D-05 **before** approving D-10.

## 3. Task authorization matrix

Legend:
- **Skills:** `PB` = `python-backend`, `RF` = `react-frontend` (the only skills created in S1). Other work reads the named documents directly.
- **Validation:** **QA** = independent QA Engineer validation note. **Sec** = Security Reviewer note.
- **Human:** approvals beyond the default merge approval, which applies to every task.

**S1-T12a** is not a new scope item. It is the part of S1-T12 that defines the Postgres/Redis services, pulled forward so T04–T10 can run integration tests against a disposable database (correction C-4).

| Task | Responsible | Skills / reads | Files permitted (create/modify) | ACs / SRs | Validation | Human |
|---|---|---|---|---|---|---|
| **S1-T15** Agents, skills, guardrails | Sonnet (orchestrator) | AGENT_SPECIFICATION, SKILLS_SPECIFICATION | `.claude/agents/{qa-engineer,security-reviewer,devops,documentation}.md`; `.claude/skills/{python-backend,react-frontend}/SKILL.md`; `.claude/settings.json`. `.mcp.json` **only** if D-07 is approved | SR-39 · TC-INF-05 | **Opus review + HC-1**. QA/Sec agents don't exist yet; after HC-1 the Security Reviewer runs the guardrail probe (§5.2) as its first action | **HC-1** |
| **S1-T01** Repo tooling | DevOps | DEVSECOPS §5, DEPLOYMENT §0, §2 | `Makefile` (all targets; later-sprint targets as stubs), `.pre-commit-config.yaml`, `.editorconfig`, `.env.example`, `CHANGELOG.md`, `pnpm-workspace.yaml`, root `package.json`, `scripts/check-prereqs`, `scripts/setup-secrets`, `.gitignore` (additions only). Generated `infrastructure/compose/secrets/*` is git-ignored and **never committed** | B-1, B-8, SR-16 | QA · Sec (secret generation) | — |
| **S1-T02** Backend skeleton | Sonnet | PB | `apps/api/{pyproject.toml,uv.lock,alembic.ini,.importlinter}`, `apps/api/src/aegissoc/**` (skeleton, `main.py`, `cli.py`), `apps/api/tests/unit/**`, `apps/api/tests/fixtures/common_passwords.txt` (+ source/licence note) | AC-QA-07 (config) | QA | **HC-2** for any dependency beyond SPRINT_01 §1 |
| **S1-T03** Core | Sonnet | PB | `apps/api/src/aegissoc/core/**`, `apps/api/tests/unit/core/**` | AC-PLAT-10, SR-18, B-2 | QA · Sec (log redaction, error model, cursor validation) | — |
| **S1-T12a** Test data services | DevOps | DEPLOYMENT, §6 below | `infrastructure/compose/compose.yaml` (**postgres + redis services only**, hardened, internal network), `infrastructure/compose/compose.test.yaml` (tmpfs overlay, project `aegissoc-test`), `infrastructure/compose/postgres/init/01-roles.sh`, Makefile recipes `test-db-up` / `test-db-down` | SR-23, SR-24, SR-27 | QA · Sec (roles script, network) | — |
| **S1-T04** DB + migrations | Sonnet | PB, DATABASE_DESIGN §2.1, §6 | `apps/api/src/aegissoc/core/db.py`, `apps/api/src/aegissoc/migrations/**` (`0001_platform`), `platform/auth/models.py`, `platform/audit/models.py`, tests | AC-PLAT-08 (immutability), SR-17, B-5 | QA (TC-SEC-19, migration cycle §6) · Sec (grants, triggers, SECURITY DEFINER) | **HC-3** privilege model |
| **S1-T05** Health | Sonnet | PB | `apps/api/src/aegissoc/observability/health.py`, router wiring in `main.py`, tests | AC-PLAT-09 | QA (TC-PLAT-07) | — |
| **S1-T09** Security middleware | Sonnet | PB | `core/security_headers.py`, `core/` middleware modules (size limit, trusted proxy), `main.py` wiring, tests | AC-PLAT-11 (app part), SR-22, SR-41 | QA · Sec | — |
| **S1-T06** Authentication | Sonnet | PB, SYSTEM_DESIGN §2, D-09 | `platform/auth/{passwords,sessions,csrf,throttle,service,api,schemas,repository}.py`, tests | AC-PLAT-01…05, SR-01…05 | QA (TC-PLAT-01…04, TC-SEC-01…04, 08, 23) · Sec | — |
| **S1-T07** RBAC + users | Sonnet | PB, SECURITY §3.2 | `platform/auth/rbac.py`, users routes/service/schemas, tests | AC-PLAT-06, AC-PLAT-07, SR-06, SR-07 | QA (TC-PLAT-05, TC-SEC-05, 06, 24) · Sec | — |
| **S1-T08** Audit API | Sonnet | PB | `platform/audit/{service,api,schemas}.py`, tests | AC-PLAT-08, SR-17 | QA (TC-PLAT-06) · Sec | — |
| **S1-T10** CLI + OpenAPI | Sonnet | PB | `cli.py`, `docs/api/openapi.json` (generated), recipes of the existing Makefile targets `openapi` and `bootstrap-admin` only | AC-PLAT-12, AC-PLAT-14 | QA (TC-PLAT-10, 11) · Sec (password input) | — |
| **S1-T11** Web app | Sonnet | RF, UI_UX_SPECIFICATION | `apps/web/**`, `pnpm-lock.yaml` | AC-PLAT-13, SR-10 | QA (Vitest; TC-E2E-01/02 in T14) · Sec (CSRF middleware, no `dangerouslySetInnerHTML`) | **HC-2** for dependencies beyond SPRINT_01 §1 |
| **S1-T12** Infrastructure | DevOps | DEPLOYMENT, deployment diagram | `infrastructure/docker/{backend,edge}.Dockerfile`, `infrastructure/caddy/Caddyfile`, `infrastructure/compose/compose.yaml` (remaining services: edge, api, migrate), `scripts/check-compose`, `.dockerignore` | AC-PLAT-11, AC-PLAT-15, SR-19, SR-20, SR-23, SR-24 | QA (TC-PLAT-09, 12, TC-INF-01, 02, TC-SEC-18) · Sec | — |
| **S1-T13** CI | DevOps | DEVSECOPS §2–4 | `.github/workflows/ci.yml`, `.github/dependabot.yml`, `.semgrep/aegissoc.yml`, `.gitleaks.toml`, `.trivyignore` (empty unless waived) | AC-PLAT-16, SR-26, SR-40 | QA (TC-PLAT-13, TC-INF-03, 04) · Sec | **HC-4** every workflow edit; **HC-5** any scanner allowlist/ignore |
| **S1-T14** QA validation | QA Engineer | QA_STRATEGY, TEST_PLAN | `qa/conftest.py`, `qa/{api,integration,security,e2e}/**` (incl. `qa/e2e/package.json`, `playwright.config.ts`), `qa/reports/sprint-01/**`; `apps/api/tests/**` only on the orchestrator's request. **No application source, no thresholds** | AC-QA-05, AC-QA-07 + verification of all S1 ACs | Security Reviewer reviews the security tests; orchestrator reviews the rest for correctness; acceptance by human | — |
| **S1-T16** Docs + security review | Documentation + Security Reviewer | docs map, THREAT_MODEL | `README.md` (quick start), `docs/DEPLOYMENT.md` (deviations only), `CHANGELOG.md`, `docs/security/reviews/sprint-01.md`, threat-model delta **as a proposal** | DoD §4 | QA verifies the quick start on a clean clone | **HC-6** sprint acceptance |

**Out of bounds for every task:**
- files of other sprints' features;
- ADR files (changes only via a new ADR, reviewed by Opus and accepted by the human);
- `docs/DECISIONS.md` (maintainer only);
- acceptance criteria;
- any production data;
- `git push`, and merges into `main`.

### 3.1 Machine-checkable dependency table

`hard` = from SPRINT_01 §2 graph plus ROADMAP "Depends on" (union). `process` = added by this protocol: an agent must exist and be reviewed (T15/HC-1) before it works, and integration tests need the disposable data services (T12a). `pr` = PR group (§4).

```csv
task,hard,process,pr,agent
T15,,D-10,PR1,orchestrator
T01,,T15,PR2,devops
T02,T01,,PR2,orchestrator
T03,T02,,PR3,orchestrator
T12a,,T15;T01,PR4,devops
T04,T03,T12a,PR5,orchestrator
T05,T04,,PR5,orchestrator
T09,T03,,PR6,orchestrator
T06,T04,,PR7,orchestrator
T07,T06,,PR8,orchestrator
T08,T04;T07,,PR8,orchestrator
T10,T07,,PR8,orchestrator
T11,T10,,PR9,orchestrator
T12,T05;T09;T11,T12a,PR10,devops
T13,T12,T15;D-05(completion),PR11,devops
T14,T06;T07;T08;T09;T10;T11;T12;T13,T15,PR12,qa-engineer
T16,ALL,T15,PR12,documentation+security-reviewer
```

Validity rules (checked by the review script, see SPRINT_01_PROTOCOL_REVIEW §2):
1. Every edge in the SPRINT_01 graph and every ROADMAP dependency appears in `hard`, directly or transitively.
2. The linear order in §4 is a topological order of `hard ∪ process`.
3. No task is in an earlier PR than one of its dependencies.
4. Every task run by a subagent has T15 in its `process` dependencies.

## 4. Execution sequence

```
HC-0  D-10 approved (ideally D-05 done; planning-baseline commit on main)
  │
  PR1  S1-T15 ──► Opus review ──► HC-1 ──► guardrail probe (§5.2)
  PR2  S1-T01 ─► S1-T02
  PR3  S1-T03
  PR4  S1-T12a  (postgres + redis, disposable test overlay)
  PR5  S1-T04 ─► S1-T05             ──► HC-3 (privilege model) at PR5 review
  PR6  S1-T09
  PR7  S1-T06
  PR8  S1-T07 ─► S1-T08 ─► S1-T10
  PR9  S1-T11
  PR10 S1-T12   (edge, api, migrate, Dockerfiles, Caddy)
  PR11 S1-T13   (completion needs D-05) ──► HC-4
  PR12 S1-T14 ─► S1-T16             ──► HC-6 (sprint acceptance)
```

**Linear order:** T15 → T01 → T02 → T03 → T12a → T04 → T05 → T09 → T06 → T07 → T08 → T10 → T11 → T12 → T13 → T14 → T16.

**Rules:**
- A PR (or a local branch offered for merge) is opened only when its QA note exists, and its Security note where required.
- PRs are merged strictly in order.
- PR1 must be merged (HC-1 passed) before any subagent works.

## 5. Agent permissions

### 5.1 Roles

| Role | Tasks | May | May not |
|---|---|---|---|
| **Maintainer** | approvals | Approve decisions, merge to `main`, push, create/configure GitHub, accept the sprint, approve waivers and dependencies | — |
| **Opus** | reviews T15, ADR proposals, deviations, sprint | Architecture and technical decisions *as proposals*; reviews; planning docs | Implement; approve its own proposals; change DECISIONS.md or ADR status |
| **Sonnet** (orchestrator / implementer) — after D-10 | T15, T02–T11 | Implement within §3 file bounds; local commits on feature branches (if D-10 allows); run tests/scanners; invoke subagents | Push, merge, tag, release; edit DECISIONS.md, ADRs (may draft *Proposed* ADRs), ACs; write its own QA or Security notes; touch out-of-bounds files |
| **QA Engineer** | T14 + validation of every other task | Run tests; write tests under `qa/` (and `apps/api/tests/**` on request); file bugs; write validation notes and the QA report | Edit application source, infrastructure or CI; change coverage thresholds or skip/disable tests; git writes; validate a task it authored (T14 is reviewed by Security Reviewer + orchestrator + human) |
| **Security Reviewer** | Sec notes; T16 security part | Read everything; run scanners; write `docs/security/reviews/**`; block on ≥ High | Edit source, tests, CI, scanner configs or waivers; waive findings |
| **DevOps** | T01, T12a, T12, T13 | Create/modify the infrastructure, CI and script files listed for its tasks; run docker/compose/make | Weaken hardening flags, gates or scanner coverage without ADR + HC-5; edit requirements, ACs, SRs or threat model; handle secret values; publish images; push |
| **Documentation** | T16 docs part | Docs in its scope | Change requirements, decisions, ADRs |

### 5.2 Enforcement and how it is tested

| Mechanism | What it enforces | Test |
|---|---|---|
| Subagent `tools:` lists | Tool types per agent (e.g. Security Reviewer has no Edit tool, and its Write is limited to `docs/security/reviews/` by instruction; Documentation has no Bash) | HC-1 review of each agent file against AGENT_SPECIFICATION §3 |
| `.claude/settings.json` **deny** | `git push` (incl. `git -C <dir> push`), `git tag`, `gh pr merge`, `gh release`, `curl`, `wget`, `rm -rf` / `-fr` / `-Rf` / `-r -f`, `docker system prune`, `docker volume rm`, reads of `infrastructure/compose/secrets/**`, `.env`, `.env.local`, `.env.*.local` (exact list: AGENT_SPECIFICATION §2) | **Guardrail probe** by the Security Reviewer after HC-1, using only harmless variants (`--dry-run`, `--help`, `--version`, a scratch directory, a nonexistent secrets path); recorded as `docs/security/reviews/EV-S01-000-guardrail-probe.md` and listed in the evidence manifest |
| `.claude/settings.json` **ask** | `docker compose … down -v` / `--volumes` (with or without global flags); `make reset`; `uv add`, `pnpm add`; `git reset --hard`; `git clean`; edits of `.github/workflows/**`, `.gitleaks.toml`, `.trivyignore`, `.semgrep/**`, `docs/security/waivers.md`, `.claude/**`, `docs/DECISIONS.md`, `docs/adr/**`, `CLAUDE.md` | Probe: Bash rules are triggered by the Security Reviewer with variants that are harmless even if approved by mistake (`--help`, `make reset -n`); `Edit` rules are triggered by the orchestrator with an `old_string` that does not exist, so an accidental approval changes nothing. The human declines each prompt; results go into EV-S01-000 |
| Path bounds per agent | Instruction-based; tool lists can't express paths | Every PR's "paths changed by agent" table is compared with §3 by the Security Reviewer (`git diff --stat`); any out-of-bounds path blocks the PR |
| No self-approval | Notes are written by a different role than the author | The PR template records author agent and validator agent; equal names block the PR |

**Legitimate operations the guardrails still allow:**
- `git add`, `git commit` and `git checkout -b` on feature branches;
- `uv sync` and `pnpm install` from lockfiles;
- `docker compose up` / `down` without `-v`;
- disposable test DB cycles, which use tmpfs volumes, so no `down -v` is needed (§6);
- `make clean` for build artefacts instead of `rm -rf`;
- HTTP checks through pytest + HTTPX instead of `curl`;
- scanners via `make scan`, with Semgrep and Trivy run from their official container images (no new host prerequisites).

## 6. Database rollback safety

**Environments:**

| Environment | Data | Destructive operations |
|---|---|---|
| **Disposable test DB** — compose project `aegissoc-test`, `compose.test.yaml` overlay, data on **tmpfs**, throwaway passwords generated into a temp dir per run | none worth keeping | allowed (it vanishes on `down`) |
| CI service containers | ephemeral | allowed |
| **Persistent local stack** — project `aegissoc`, named volumes `pg_data`, `redis_data`, `evidence_data` | the maintainer's local data | **prohibited without explicit maintainer approval**: `alembic downgrade`, `DROP`, `TRUNCATE`, `docker compose down -v`, `make reset`, `make restore`, volume removal |

**Mandatory migration validation cycle** (every migration, run by QA on the disposable DB and in CI):
1. `make test-db-up` — fresh disposable Postgres/Redis, wait until healthy.
2. `alembic upgrade head`.
3. **Validate:** schema assertions (tables, columns, constraints, indexes), role grants, triggers, owner functions, and the migration's own tests (e.g. TC-SEC-19 for `0001_platform`).
4. `alembic downgrade base` (or `-1` for later migrations), then assert the objects are gone.
5. `alembic upgrade head` again, then repeat step 3.
6. `make test-db-down`.

The migration is rejected if any step fails.

**Data-loss escalation:**
- Every migration docstring declares `data_loss: none | possible`.
- `possible` (e.g. dropping or narrowing a column, changing types, deleting rows) requires:
  - an Opus review;
  - an expand/contract plan (DATABASE_DESIGN §5);
  - maintainer approval **before** it is applied to any persistent environment.
- A backup (`make backup`) precedes it.
- Sprint 1's `0001_platform` is `data_loss: none` (it only creates objects).

## 7. Evidence requirements

**Evidence is the artefact, not a statement about it.**

| Rule | Detail |
|---|---|
| Original artefacts retained | Small machine-readable artefacts (JUnit XML, coverage XML, scanner JSON/SARIF, k6 summaries, `docker stats` captures) are **committed** under `qa/reports/sprint-01/evidence/`. Large artefacts (Playwright traces/videos/HTML) stay in CI artefacts with `retention-days: 90`, and a local copy is kept outside git. Both are listed in `qa/reports/sprint-01/evidence/MANIFEST.md` with their SHA-256 |
| Required metadata per record | evidence ID, requirement(s), test case(s), **git commit SHA**, **date/time UTC**, **environment** (OS, Docker, Python, Node and tool versions), **exact command**, **exit status**, **artefact path(s) + SHA-256**, producer |
| Template | `qa/templates/EVIDENCE_RECORD_TEMPLATE.md` |
| Not accepted | Textual claims ("all tests pass"), screenshots of a terminal without the artefact, results from a SHA other than the one under review, edited artefacts |
| Independent reproduction | For each task, QA re-runs the recorded command(s) **at the recorded SHA in a clean checkout** (`git archive <sha> | tar -x -C "$(mktemp -d)"`, which needs no git write, consistent with the QA Engineer's restrictions), against a fresh disposable DB, and compares the outcome (exit status, pass/fail counts, finding counts). A mismatch is logged as a bug (or flaky-test investigation) and blocks the task |
| Per-task notes | QA validation note: `qa/reports/sprint-01/validation/<task>.md`. Security note: section in `docs/security/reviews/sprint-01.md`. Implementation report: PR description, or `qa/reports/sprint-01/tasks/<task>.md` before D-05 |
| Traceability | `qa/reports/sprint-01/QA_REPORT.md` §4: requirement → TC → evidence ID → result |

## 8. Capacity controls

- **Estimate preserved:** ≈ 29.5 h of maintainer time against 20–30 h (PLANNING_AUDIT_REPORT §12.6). T12a moves existing T12 work earlier; it is estimated at ≤ 0.25 h of added overhead and covered by the existing buffer.
- **Tracking:** hours per task are logged in `docs/sprints/SPRINT_01_TIME_LOG.md`, created at sprint start by the orchestrator and filled in by the maintainer.

| Trigger | Action | Who decides |
|---|---|---|
| A task exceeds its estimate by > 50 % | Note it in the time log with the cause | — |
| **> 25 h logged by day 10** | Apply the **cut line**: the Users admin UI moves to Sprint 2 (API and tests stay) | Maintainer confirms |
| Projected total > 30 h after the cut line | Stop. Opus proposes options: move stretch items, move non-security UI polish, or extend the sprint by calendar time | Maintainer chooses |
| Any proposal to save time by removing a security control, mandatory test or scanner | **Rejected by rule** — not an option | — |

**Never removed to save time:**
- argon2id;
- sessions + CSRF;
- D-09 login throttling;
- RBAC matrix and route-permission tests;
- audit immutability and its tests;
- container hardening and `check-compose`;
- every CI security scanner;
- the migration validation cycle;
- E2E smoke;
- coverage thresholds;
- independent QA and Security notes.

## 9. QA and security gates

A task is complete only when all of the following hold:

| Gate | Applies | Blocking |
|---|---|---|
| Lint, format, type-check (`ruff`, `mypy --strict`, `eslint`, `tsc`), import-linter | every code task | yes |
| Unit tests + coverage thresholds (QA_STRATEGY §6) | T02–T11 | yes |
| Integration/API tests for mapped TCs on the disposable DB | T04–T10 | yes |
| Migration validation cycle (§6) | T04 and every later migration | yes |
| E2E `@smoke` (login/logout, role nav, axe) | T11–T14 | yes |
| Scanners: Bandit, Semgrep, Gitleaks, pip-audit, pnpm audit, Trivy fs/image/config | every PR (locally before D-05, CI after) | yes on High/Critical (with fix) or any secret |
| OpenAPI snapshot fresh | T10 onward | yes |
| `scripts/check-compose` hardening | T12a onward | yes |
| QA validation note = *Accepted* (only S3/S4 bugs open) | every task except T15 (validated by Opus review + HC-1 + guardrail probe) and T14 (reviewed as stated in §3) | yes; S1/S2 bugs block |
| Security note without open ≥ High | tasks with **Sec** in §3 | yes |
| Independent reproduction (§7) | every task with test evidence | yes |

**Non-negotiable controls:** see the list in §8. They are never weakened, skipped or waived to pass a gate.

## 10. Rollback and escalation

| Situation | Action | Escalate to |
|---|---|---|
| Task fails QA or Security | Fix on the branch, re-validate; nothing merges | Maintainer if it can't be fixed within the task |
| Need to change architecture, a boundary, a dependency outside SPRINT_01 §1, an API contract or a security control | **Stop.** Draft an ADR (*Proposed*) with security and QA implications | Opus review → maintainer |
| Ambiguous or contradictory spec | Stop; list the options with a recommendation | Opus, then maintainer |
| Migration fails validation | Fix on the disposable DB; re-run the full cycle (§6) | Maintainer if `data_loss: possible` |
| Destructive DB/volume operation needed on the persistent stack | Do not run it | Maintainer approval first |
| Secret committed locally | Do not push. Rotate (delete the file, re-run `make setup`), rewrite the local branch, re-run Gitleaks on the full history | Maintainer immediately |
| Agent exceeded its file bounds | Revert those changes on the branch; record it in the PR | Maintainer |
| Gate cannot pass for an external reason (no fix available) | Waiver request: Security Reviewer review → maintainer approval → entry in `docs/security/waivers.md`, ≤ 30-day expiry | Maintainer (**HC-5**) |
| Capacity triggers | §8 | Maintainer |
| D-05 still open at T13 | Finish T13's local part; continue T14/T16 locally; Sprint 1 cannot be accepted until AC-PLAT-16 is met | Maintainer: complete D-05, or extend/close the sprint with AC-PLAT-16 recorded as unmet |
| Anything offensive, real data or real credentials requested | Refuse | Maintainer |

Rollback of a merged change: a revert commit on a branch, through the normal gates. No force pushes to `main`.

## 11. Human approval checkpoints

| ID | When | Maintainer decides |
|---|---|---|
| **HC-0** | Before anything | Approve D-10 (wording in §2); preferably complete D-05; approve the planning-baseline commit |
| **HC-1** | After S1-T15 (PR1) | Agents, skills and `.claude/settings.json` match the spec; `.mcp.json` only if D-07 is approved; then the guardrail probe runs |
| **HC-2** | Any dependency outside SPRINT_01 §1 | Approve or reject (justification + licence) |
| **HC-3** | PR5 review (S1-T04) | Database privilege model (roles, grants, triggers, SECURITY DEFINER function) |
| **HC-4** | During S1-T13 | Every workflow edit (`ask` rule); the canary PR result |
| **HC-5** | Any waiver, or any scanner allowlist/ignore change | Approve with expiry, or reject |
| **Merge** | Every PR / branch, in order | Merge after QA and Security notes, and push |
| **HC-6** | End of sprint | Sprint DoD (DEFINITION_OF_DONE §4), QA report, Security review; log in at `https://localhost:8443` and create a second user; record acceptance |

## 12. Authorization statement

**Implementation of Sprint 1 remains unauthorised until the maintainer approves D-10 in `docs/DECISIONS.md`.** Until then:
- no application code, Dockerfiles, workflows or infrastructure files may be created;
- no agent files are created;
- Sonnet is not authorised;
- no repository is created or modified on GitHub;
- nothing is pushed.

This protocol changes no decision, ADR or acceptance criterion.

---

## Readiness assessment

| Area | State |
|---|---|
| Governance | Ready. The only gate to start is **D-10**; one wording point (U-1) should be settled in the approval |
| GitHub (D-05) | Not ready. Blocks completion of S1-T13 and Sprint 1 acceptance, not T01–T12; recommended before D-10 |
| Dependencies | Consistent and machine-checked (§3.1); PR groups re-cut to remove two ordering violations |
| Permissions | Defined per role, with an enforcement test (guardrail probe) and review checks; path bounds remain instruction-based (U-2) |
| Database safety | Disposable-DB procedure and mandatory up → validate → down → up cycle defined; destructive operations on persistent data require approval |
| Evidence | Artefact-based, SHA-bound, independently reproducible |
| Capacity | ≈ 29.5 h, cut line at 25 h by day 10, escalation defined; no security control is removable |

**STOP.** Waiting for the maintainer: D-10, and D-05 (recommended first).
