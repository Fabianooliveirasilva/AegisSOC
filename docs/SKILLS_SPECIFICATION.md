# AegisSOC — Skills Specification

| | |
|---|---|
| Status | **Specified only. No project skill has been created or installed.** Skill files (`.claude/skills/<name>/SKILL.md`) are created after approval of this design (task S1-T15 creates only `python-backend` and `react-frontend` — audit R1; the rest are created just in time, see §3). |
| Format | Claude Code Agent Skills: a folder with `SKILL.md` (frontmatter `name`, `description`) plus optional reference files |

## 1. Already available in this environment (not project skills)

The maintainer's Claude Code setup currently lists these plugin skills, which the workflow may use. They are external and not versioned with this repo:
`superpowers:test-driven-development`, `superpowers:systematic-debugging`, `superpowers:verification-before-completion`, `superpowers:requesting-code-review`, `superpowers:writing-plans`, `superpowers:executing-plans`, `claude-api` (Claude API/SDK reference), `security-review`, `code-review`, `frontend-design`.

The project skills below are AegisSOC-specific: they encode this repository's conventions, not general knowledge.

## 2. Project skills

Each entry: **Purpose · Required knowledge · Execution guidelines · Tools · Quality standards · References · Deliverables.**

### 2.1 `blue-team-operations`
- **Purpose:** apply defensive SOC practice to product content (alerts, playbooks, triage UX).
- **Knowledge:** SOC tiers, triage, NIST SP 800-61r3 phases, containment vs eradication, chain of custody.
- **Guidelines:** every recommendation must be a human-executed step; never generate response automation against external systems; tie steps to evidence to collect.
- **Tools:** Read, Write (playbooks).
- **Quality:** steps verifiable, phase-tagged, ATT&CK-linked; no vendor-specific commands unless labelled as example.
- **References:** NIST SP 800-61r3; SYSTEM_DESIGN §5.
- **Deliverables:** playbook YAML, triage notes.

### 2.2 `soc-analysis`
- **Purpose:** analyse alerts/events the way an analyst would; define good AI analyst outputs.
- **Knowledge:** common log sources (Windows Security, Sysmon, Linux auth, web, cloud audit), benign vs malicious patterns.
- **Guidelines:** always state benign explanations; cite event IDs; separate observation from hypothesis.
- **Tools:** Read.
- **Quality:** every claim cites data; confidence stated.
- **References:** SYSTEM_DESIGN §7.7 envelope.
- **Deliverables:** fixture analyses for `FixtureProvider`, evaluation rubrics for AI outputs.

### 2.3 `siem-engineering`
- **Purpose:** parsers, normalisation and event-store conventions.
- **Knowledge:** ECS field semantics, syslog/combined log formats, Windows event structure, partitioned tables.
- **Guidelines:** parsers are pure; never trust payload for `aegis.*`; golden files + hypothesis tests for each parser; keep hot columns in sync with `doc`.
- **Tools:** Read, Edit, Bash (pytest).
- **Quality:** AC-SIEM-03/04 thresholds; no unhandled exceptions.
- **References:** ADR-0006, SYSTEM_DESIGN §3.
- **Deliverables:** parser modules, fixtures, field mapping docs.

### 2.4 `detection-engineering`
- **Purpose:** the AegisSOC detection lifecycle end to end.
- **Knowledge:** lifecycle states, four-eyes approval, regression gate, FP metrics.
- **Guidelines:** rule + positive + negative scenario in one change; document FP sources; never activate; use the scenario format verbatim.
- **Tools:** Read, Write under `detections/`, Bash (`aegissoc detections validate|test`).
- **Quality:** Detection rule DoD.
- **References:** SYSTEM_DESIGN §4, §8; diagrams/detection-lifecycle.md.
- **Deliverables:** rules, scenarios, tuning notes.

### 2.5 `sigma-rules`
- **Purpose:** write Sigma that the AegisSOC evaluator supports.
- **Knowledge:** Sigma spec v2 (rules + correlation), modifiers, conditions, logsource taxonomy, pySigma processing pipelines.
- **Guidelines:** only supported modifiers (SYSTEM_DESIGN §4.2); map fields through the AegisSOC pipeline; RE2-compatible regex; prefer `contains|all` over regex.
- **Tools:** Read, Write.
- **Quality:** static validation 0 errors; `level`, `falsepositives`, `tags` present.
- **References:** sigmahq.io specification; SigmaHQ rule conventions; DRL 1.1 attribution rules.
- **Deliverables:** `.yml` rules.

### 2.6 `mitre-attack`
- **Purpose:** correct ATT&CK usage.
- **Knowledge:** tactics vs techniques vs sub-techniques, tag format `attack.tXXXX.YYY`, deprecated/revoked handling, versioning.
- **Guidelines:** only IDs present in the imported version; prefer the most specific sub-technique supported by evidence.
- **Tools:** Read.
- **Quality:** zero invalid tags (validated).
- **References:** attack.mitre.org; ATT&CK Terms of Use (attribution).
- **Deliverables:** technique mappings, coverage reviews.

### 2.7 `incident-response`
- **Purpose:** incident model, lifecycle and reporting.
- **Knowledge:** state machine (SYSTEM_DESIGN §5.3), evidence handling, report structure.
- **Guidelines:** transitions only via service; every change → timeline + audit; evidence immutable once hashed.
- **Tools:** Read, Edit.
- **Quality:** AC-INC-* pass.
- **References:** NIST SP 800-61r3.
- **Deliverables:** incident features, report templates.

### 2.8 `threat-hunting`
- **Purpose:** hypothesis-driven hunts and synthetic storylines.
- **Knowledge:** hunting loop (hypothesis → data → analysis → conclusion), DSL limits, retro-hunt.
- **Guidelines:** synthetic indicators only; each storyline produces ground truth; hunts record hypothesis and conclusion.
- **Tools:** Read, Write under `data/hunts`, `services/synthetic-generator/storylines`.
- **Quality:** deterministic with seed; manifests complete.
- **References:** SYSTEM_DESIGN §6, §9.
- **Deliverables:** hunts, storylines, IOC CSVs.

### 2.9 `python-backend`
- **Purpose:** AegisSOC backend conventions.
- **Knowledge:** FastAPI dependencies, Pydantic v2 strict models, SQLAlchemy 2.0 async, Alembic, redis-py asyncio streams, structlog.
- **Guidelines:** module layout (api/service/models/schemas/repository/workers); permission dependency on every route; problem+json errors; no cross-module model imports; `Clock` injection; no `print`; type-complete.
- **Tools:** Read, Edit, Bash (uv, pytest, ruff, mypy).
- **Quality:** mypy --strict, coverage thresholds, import-linter green.
- **References:** ARCHITECTURE §3.2; component diagram; official FastAPI/SQLAlchemy docs (via Context7 if authorised).
- **Deliverables:** backend modules with tests.

### 2.10 `react-frontend`
- **Purpose:** AegisSOC SPA conventions.
- **Knowledge:** React, TanStack Query/Table, React Router, shadcn/ui, Tailwind tokens, openapi-fetch.
- **Guidelines:** features folder per module; generated API types only; CSRF via shared middleware; render data as text; all states (loading/empty/error); a11y first.
- **Tools:** Read, Edit, Bash (pnpm).
- **Quality:** tsc strict, eslint, axe 0 serious, Vitest coverage.
- **References:** UI_UX_SPECIFICATION.md.
- **Deliverables:** screens and components with tests.

### 2.11 `api-testing`
- **Purpose:** API tests that verify contracts and abuse cases.
- **Knowledge:** HTTPX AsyncClient, pytest fixtures, problem+json, RBAC matrix testing.
- **Guidelines:** each test tagged with `req(...)`; test 2xx and the full error table; role matrix parametrised from SECURITY.md table (single source).
- **Tools:** Read, Write under `qa/api`, Bash (pytest).
- **Quality:** deterministic, isolated (transaction rollback), < 50 ms median per test.
- **References:** API_SPECIFICATION.md, TEST_PLAN.md.
- **Deliverables:** API test modules, Postman collection check.

### 2.12 `playwright-automation`
- **Purpose:** E2E journeys and accessibility checks.
- **Knowledge:** Playwright Test (TS), fixtures, storage state per role, axe-core, trace viewer.
- **Guidelines:** role-based login fixtures; `getByRole` locators; no sleeps; `@smoke` tag for PR runs; capture trace on failure.
- **Tools:** Read, Write under `qa/e2e`, Bash (pnpm playwright).
- **Quality:** < 1 % flaky; each journey maps to a TC.
- **References:** TEST_PLAN TC-E2E-*.
- **Deliverables:** specs, fixtures, reports.

### 2.13 `security-testing`
- **Purpose:** verify SRs and threat mitigations.
- **Knowledge:** OWASP ASVS L2 controls, OWASP Top 10, LLM Top 10 (prompt injection, excessive agency), STRIDE.
- **Guidelines:** only against the local stack; payload corpora versioned in `qa/security`; no external targets; every finding mapped to SR/T IDs.
- **Tools:** Read, Write under `qa/security`, Bash (pytest, bandit, semgrep, gitleaks, trivy; ZAP baseline against localhost only).
- **Quality:** each SR has ≥ 1 automated test where automatable.
- **References:** SECURITY.md, THREAT_MODEL.md.
- **Deliverables:** security tests, review notes.

### 2.14 `devsecops`
- **Purpose:** CI pipeline and gates as specified.
- **Knowledge:** GitHub Actions, SHA pinning, scanners' configuration and exit codes, SBOM.
- **Guidelines:** gates block on High/Critical; waivers only via waiver file; minimal permissions.
- **Tools:** Read, Edit under `.github/`, Bash (actionlint, scanners).
- **Quality:** DEVSECOPS.md §2 stage table fully implemented.
- **References:** DEVSECOPS.md.
- **Deliverables:** workflows, scanner configs.

### 2.15 `docker-architecture`
- **Purpose:** hardened Compose topology.
- **Knowledge:** multi-stage builds, non-root images, read-only FS, networks, healthchecks, profiles, secrets.
- **Guidelines:** follow DEPLOYMENT.md tables; pin digests; no published ports except edge.
- **Tools:** Read, Edit under `infrastructure/`, Bash (docker compose, hadolint).
- **Quality:** TC-INF-01/02 pass; core ≤ 2.5 GB.
- **References:** DEPLOYMENT.md, deployment diagram.
- **Deliverables:** Dockerfiles, compose files, Caddyfile.

### 2.16 `technical-documentation`
- **Purpose:** consistent, ID-linked documentation.
- **Knowledge:** repo doc map, ID conventions (AC/SR/T/TC/ADR), ADR template.
- **Guidelines:** one fact one home, link instead of copy; update traceability when IDs change.
- **Tools:** Read, Edit under `docs/`.
- **Quality:** `make docs-check` (links + IDs) green.
- **References:** README documentation map.
- **Deliverables:** docs, runbooks, CHANGELOG.

### 2.17 `aegis-architecture-governance` (supporting, for the Architect Agent)
- **Purpose:** apply ADR process and boundary rules.
- **Guidelines:** ADR template; status flow Proposed → Accepted (human) → Superseded; import-linter contract updates with each new module.
- **Deliverables:** ADRs, boundary reviews.

## 3. Creation schedule (after approval)

| Sprint | Skills created |
|---|---|
| S1 | `python-backend`, `react-frontend` (audit R1 — Sprint 1 agents read DEVSECOPS, DEPLOYMENT, QA_STRATEGY and TEST_PLAN directly) |
| S2 | `api-testing`, `playwright-automation`, `security-testing`, `docker-architecture`, `devsecops`, `technical-documentation`, `aegis-architecture-governance`, `siem-engineering`, `threat-hunting` (storylines) |
| S3 | `detection-engineering`, `sigma-rules`, `mitre-attack` |
| S4 | `incident-response`, `blue-team-operations` |
| S5 | `soc-analysis` |
