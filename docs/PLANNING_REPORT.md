# AegisSOC — Planning Completion Report

| | |
|---|---|
| Date | 2026-11-21 |
| Phase | Planning and architecture (Claude Opus) |
| Status | **Complete — Sprint 1 blockers corrected** (see [PLANNING_AUDIT_REPORT.md](PLANNING_AUDIT_REPORT.md), revision 2). **Approved:** ADRs (D-06) and Sprint 1 scope (D-08) on 2026-11-21. Sprint 1 implementation authorised (D-10, Sonnet). No application code has been written. |
| Assumed capacity | 10 weeks × 10–15 h/week, part-time, Sonnet implements, independent QA |

## 1. Executive summary

AegisSOC is planned as a **modular monolith** (FastAPI, one Python package with import-linter–enforced module boundaries) with an **asynchronous worker** on **Redis Streams**, **PostgreSQL 16** as the system of record *and* partitioned event store, a **Caddy** edge (TLS, headers, single origin) and a **React/TypeScript** SPA. Detection uses **Sigma** parsed by pySigma and evaluated by an in-house streaming evaluator (RE2 regex), with a detection-as-code lifecycle: static validation → positive/negative scenarios → regression → four-eyes approval → activation. The **AI analyst** runs on the Claude Messages API as an async job with read-only, requester-scoped tools, schema-constrained output, mechanically verified citations and human-applied proposals; it is off by default and has a deterministic fixture provider for offline demos and tests. Heavy or external pieces (OpenSearch, MISP, Fluent Bit, Grafana) are optional profiles or post-MVP.

Five two-week sprints: Foundation → SIEM pipeline → Detection engine → Incidents/hunting/intel → AI/QA/observability/release (`v0.5.0`).

## 2. Deliverables produced

| # | Required document | Location |
|---|---|---|
| 1 | README.md | [README.md](../README.md) |
| 2 | ARCHITECTURE.md | [ARCHITECTURE.md](ARCHITECTURE.md) |
| 3 | SYSTEM_DESIGN.md | [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md) |
| 4 | THREAT_MODEL.md | [THREAT_MODEL.md](THREAT_MODEL.md) |
| 5 | SECURITY.md | [SECURITY.md](../SECURITY.md) |
| 6 | QA_STRATEGY.md | [QA_STRATEGY.md](QA_STRATEGY.md) |
| 7 | TEST_PLAN.md | [TEST_PLAN.md](TEST_PLAN.md) |
| 8 | API_SPECIFICATION.md | [API_SPECIFICATION.md](API_SPECIFICATION.md) |
| 9 | DATABASE_DESIGN.md | [DATABASE_DESIGN.md](DATABASE_DESIGN.md) |
| 10 | AGENT_SPECIFICATION.md | [AGENT_SPECIFICATION.md](AGENT_SPECIFICATION.md) |
| 11 | SKILLS_SPECIFICATION.md | [SKILLS_SPECIFICATION.md](SKILLS_SPECIFICATION.md) |
| 12 | MCP_SPECIFICATION.md | [MCP_SPECIFICATION.md](MCP_SPECIFICATION.md) |
| 13 | DEVSECOPS.md | [DEVSECOPS.md](DEVSECOPS.md) |
| 14 | DEPLOYMENT.md | [DEPLOYMENT.md](DEPLOYMENT.md) |
| 15 | ROADMAP.md | [ROADMAP.md](ROADMAP.md) |
| 16 | ACCEPTANCE_CRITERIA.md | [ACCEPTANCE_CRITERIA.md](ACCEPTANCE_CRITERIA.md) |
| 17 | DEFINITION_OF_DONE.md | [DEFINITION_OF_DONE.md](DEFINITION_OF_DONE.md) |
| 18 | ADRs (16) | [adr/](adr/) |
| + | UI/UX specification | [UI_UX_SPECIFICATION.md](UI_UX_SPECIFICATION.md) |
| + | Observability and metrics | [OBSERVABILITY.md](OBSERVABILITY.md) |
| + | Diagrams (7 + ERD + CI + orchestration) | [diagrams/](diagrams/) |
| + | Sprint 1 implementation spec | [sprints/SPRINT_01.md](sprints/SPRINT_01.md) |
| + | Sonnet handoff | [HANDOFF_SONNET.md](HANDOFF_SONNET.md) |
| + | Human decision log | [DECISIONS.md](DECISIONS.md) |
| + | Planning audit (rev. 2) | [PLANNING_AUDIT_REPORT.md](PLANNING_AUDIT_REPORT.md) |
| + | Governance | `CLAUDE.md`, `CONTRIBUTING.md`, `.github/` PR & issue templates, `qa/templates/` (QA report, bug, evidence), `docs/security/waivers.md`, directory READMEs |

Not created on purpose (require approval first or belong to Sprint 1): `.claude/agents/*`, `.claude/skills/*`, `.claude/settings.json`, `.mcp.json`, Makefile, Dockerfiles, compose files, CI workflows, any source code, LICENSE.

## 3. Planning quality gates

| Gate | Status | Evidence |
|---|---|---|
| Architecture coherent and documented | ✔ | ARCHITECTURE §2–6, component/data-flow/deployment diagrams; ADR-0002 |
| Technology choices justified | ✔ | ARCHITECTURE §12 (adopt/replace/defer per proposed tech); ADR-0003…0013 |
| Data model defined | ✔ | DATABASE_DESIGN §1–2 (ERD + 35 tables), §3 indexes, §4 retention, §5 migrations, §6 DB roles |
| API contracts documented | ✔ | API_SPECIFICATION §1 conventions, §2 endpoints for auth, ingestion, events, detections, alerts, incidents, hunting, AI, QA, admin |
| Threat model complete | ✔ | THREAT_MODEL: 9 assets, 6 trust boundaries, STRIDE per element, 30 threats incl. all categories in the brief, abuse cases, residual risks |
| Security requirements specified | ✔ | SECURITY.md SR-01…SR-41, RBAC matrix, release checklist |
| QA architecture defined | ✔ | QA_STRATEGY: pyramid, environments, data, bug lifecycle, coverage, gates, indicators, independence protocol |
| Detection validation designed | ✔ | SYSTEM_DESIGN §4, §8; detection-lifecycle diagram; ADR-0015; TEST_PLAN §5 scenario catalogue |
| Agents have clear boundaries | ✔ | AGENT_SPECIFICATION §2–3 (mission … acceptance criteria per agent), orchestration model, human approval list. Limitation on path-level enforcement stated |
| Skills specified | ✔ | SKILLS_SPECIFICATION §2 (17 skills) + creation schedule; none claimed installed |
| MCP permissions documented | ✔ | MCP_SPECIFICATION §1 available vs proposed, §2 scopes, §4 checklist |
| Repository structure defined | ✔ | Directories created with READMEs stating purpose and sprint; see §5 below |
| UI/UX requirements documented | ✔ | UI_UX_SPECIFICATION: 12 screens, flows, components, tokens, states, accessibility |
| CI/CD designed | ✔ | DEVSECOPS §2 (12 stages + OpenAPI + traceability), §3 gates & waivers, §4 CI hardening |
| Roadmap dependency-aware | ✔ | ROADMAP: sprint dependency graph, per-task dependencies, stretch lists, capacity risks |
| Acceptance criteria measurable | ✔ | 92 ACs with thresholds/conditions; each mapped to ≥ 1 TC |
| Tasks detailed enough for Sonnet | ✔ Sprint 1 / ◐ Sprints 2–5 | Sprint 1 is fully specified (files, behaviour, tests, order, PR grouping). Sprints 2–5 are specified at task level with ACs and TCs; a detailed `SPRINT_NN.md` is to be produced (Opus/Architect) at each sprint start so it reflects what Sprint N−1 actually delivered. This is deliberate, not a gap. |

### Consistency verification performed

An automated check (script kept outside the repo) parsed all Markdown files and confirmed:
- every referenced `AC-*` (92), `SR-*` (41), `TC-*` (135), `T-*` (30) and `ADR-*` (16) ID is defined;
- every AC and every SR is mapped to at least one test case in TEST_PLAN;
- all relative Markdown links resolve.

Manual cross-checks fixed during planning: event dedup key definition aligned between ARCHITECTURE and DATABASE_DESIGN; alert dedup index aligned; network topology corrected so log shippers reach the API only via the edge and the edge can publish ports while other networks stay internal.

## 4. Risks

| ID | Risk | L | I | Mitigation |
|---|---|---|---|---|
| R-01 | Capacity: 100–150 human hours is tight for six modules | H | H | Vertical slices, stretch lists, strict sprint scope, post-MVP backlog; Sprint 1 cut rules in ROADMAP §2 |
| R-02 | Evaluator correctness (Sigma semantics subtleties) | M | H | Conformance suite ≥ 60 cases, 90 % branch coverage, scenario-driven development |
| R-03 | AI safety classifiers refuse security content | M | M | `refused` status handled, server-side fallback, fixture provider keeps demo deterministic; report live behaviour honestly |
| R-04 | Implementer drifts from design or invents APIs | M | H | CLAUDE.md + HANDOFF rules, import-linter, OpenAPI diff, ADR change control, independent QA, "consult docs" rule for SDKs |
| R-05 | Laptop performance below targets | M | M | Targets are indicative and recorded with hardware; OpenSearch path documented |
| R-06 | pySigma API changes between versions | L | M | Pin version; wrap in a thin adapter; conformance suite catches regressions |
| R-07 | Local TLS friction for reviewers (Caddy CA) | M | L | `make trust-ca`, documented one-time warning acceptance |
| R-08 | Redis licence questions for a public portfolio | L | L | Valkey drop-in (D-02) |
| R-09 | Agent path restrictions are instruction-based | M | M | PR template "paths changed by agent", human review, TC-INF-05 |
| R-10 | Synthetic data makes metrics look better than reality | H | M | SIMULATED labelling everywhere; reports state data origin |

## 5. Repository structure (created)

```
AegisSOC/
├── README.md · SECURITY.md · CLAUDE.md · CONTRIBUTING.md · .gitignore
├── .github/            PR template, issue templates (workflows arrive in S1-T13)
├── apps/               api/ (backend + worker), web/ (SPA)              — deployable
├── services/           synthetic-generator/                             — deployable, auxiliary
├── qa/                 api/ integration/ e2e/ detection/ security/ performance/ templates/ reports/
├── detections/         rules/ correlation/ scenarios/
├── data/               mitre/ playbooks/ iocs/ hunts/ synthetic/
├── infrastructure/     compose/ docker/ caddy/ fluent-bit/ observability/
├── agents/             (spec pointer; real files go to .claude/agents/ after approval)
├── mcp/                (spec pointer; .mcp.json only after approval)
├── scripts/            (from Sprint 1)
└── docs/               17 docs + UI/UX + observability + handoff + report
    ├── adr/            0000 template + 0001–0016
    ├── diagrams/       7 diagrams
    ├── sprints/        SPRINT_01.md
    ├── api/            (openapi.json snapshot from Sprint 1)
    └── security/       waivers.md, reviews/
```

## 6. Decisions

The decision log — status, options and who approved what — lives in **[DECISIONS.md](DECISIONS.md)** (single source of truth). Summary: **D-06, D-08, D-09 approved**; D-10 (start implementation) open; D-05 needed before S1-T13; D-01, D-02, D-03, D-04, D-07 open and non-blocking.

## 7. Assumptions made (correct any that are wrong)

1. Single maintainer; demo users per role are seeded (from Sprint 3, with random passwords — SR-16) so four-eyes approval can be demonstrated.
2. Laptop with ≥ 8 GB RAM and Docker; reviewers run the stack locally.
3. English for code, UI and docs.
4. No real data ever; `data_origin=production` is impossible by schema.
5. The Anthropic API is used only when the maintainer enables it; CI never calls it.
6. GitHub Actions is the CI; GHCR publishing is optional.
7. Sprint lengths are calendar-fixed; scope flexes via stretch lists.

## 8. Handoff instructions for Claude Sonnet (summary)

Full text: [HANDOFF_SONNET.md](HANDOFF_SONNET.md). In short: check preconditions (approved sprint, accepted ADRs, blocking decisions resolved) → read in the given order → present sequence and gaps → wait for confirmation → per task: tests first, smallest change, run suites, independent QA and security agents, PR with the standard report → human merges. Never change architecture silently, never weaken gates, never claim unexecuted results.

## 9. Next step

**Planning stops here.** To proceed, the maintainer should:
1. Review this package (suggested reading: README → ARCHITECTURE → ROADMAP → SPRINT_01 → SECURITY).
2. ~~Resolve D-06 and D-08~~ — approved 2026-11-21. Remaining: D-10 (go-ahead), D-05 before S1-T13; optionally D-07, D-02.
3. Set "Current sprint" in ROADMAP.md to *Sprint 1 — approved on <date>*.
4. Start an implementation session with Sonnet pointing it at `docs/HANDOFF_SONNET.md`.
