# AegisSOC

> A defensive Security Operations Center platform: SIEM ingestion, detection engineering with Sigma, alert and incident management, threat hunting, an AI analyst that keeps the human in charge, and continuous QA of detection quality.

**Status:** Planning complete; ADRs and Sprint 1 scope approved (see [docs/DECISIONS.md](docs/DECISIONS.md)). Sprint 1 implementation authorised (D-10). No application code exists yet.
**Scope:** Local, single-host demo via Docker Compose, using **synthetic security data only**.

---

## Why AegisSOC exists

Most portfolio "SIEMs" are dashboards over static JSON. AegisSOC is built to show the engineering discipline behind a real SOC:

1. **Detections are code.** Sigma rules are versioned, statically validated, tested against positive *and* negative scenarios, reviewed by a second person and only then activated.
2. **Quality is measured, not claimed.** Every rule has scenario coverage, a pass rate, and false‑positive tracking from analyst dispositions. Metrics derived from synthetic data are labelled as simulated.
3. **AI assists, never decides.** The AI analyst explains, summarises and suggests — with cited sources, confidence levels and human approval for anything consequential.
4. **Security by design.** STRIDE threat model, RBAC, audit trail, hardened containers and CI security gates from Sprint 1.

## What it does (MVP, 10 weeks)

| Module | Capability |
|---|---|
| A — SIEM | HTTP ingestion with per-source API keys, parsing & normalisation to an ECS subset, partitioned event store, search, timelines, ingestion health, retention |
| B — Detection Engineering | Sigma rule management & versioning, streaming rule evaluation, correlation (count/temporal), MITRE ATT&CK mapping, scenario tests, detection metrics |
| C — Incident Management | Alerts → incidents, lifecycle, assignment, notes, evidence with hashes, timeline, checklist playbooks, audit trail |
| D — Threat Hunting | Structured event queries, saved hunts, retro-hunts with Sigma rules, IOC lists and matching, hunt reports |
| E — AI Analyst | Explain / summarise / next steps / report / ATT&CK suggestions / evidence gaps, structured & cited, human-approved actions |
| F — QA & Validation | Detection validation lifecycle, regression suite, QA reports, CI quality gates |

## Architecture at a glance

Modular monolith (FastAPI) + asynchronous worker (same codebase) + PostgreSQL + Redis Streams, behind a Caddy edge proxy, with a React/TypeScript SPA. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

```
Browser ──HTTPS──► Caddy ──► API (FastAPI) ──► PostgreSQL
                              │  ▲               ▲
Log sources ──HTTPS──► /ingest│  │               │
                              ▼  │               │
                         Redis Streams ──► Worker (normalise · detect · correlate · AI · QA)
                                                  └──► Anthropic API (optional)
```

## Documentation map

| Document | Purpose |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Components, boundaries, data ownership, diagrams |
| [docs/SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md) | Module-level design: pipeline, detection engine, incidents, hunting, AI, QA |
| [docs/DATABASE_DESIGN.md](docs/DATABASE_DESIGN.md) | ERD, tables, indexes, retention, migrations |
| [docs/API_SPECIFICATION.md](docs/API_SPECIFICATION.md) | REST contracts, auth, errors, pagination, rate limits |
| [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md) | STRIDE analysis and threat catalogue |
| [SECURITY.md](SECURITY.md) | Vulnerability disclosure, security requirements, checklist |
| [docs/QA_STRATEGY.md](docs/QA_STRATEGY.md) | Test pyramid, QA independence, gates, bug lifecycle |
| [docs/TEST_PLAN.md](docs/TEST_PLAN.md) | Test cases, detection scenarios, traceability |
| [docs/ACCEPTANCE_CRITERIA.md](docs/ACCEPTANCE_CRITERIA.md) | Requirements with measurable acceptance criteria |
| [docs/DEFINITION_OF_DONE.md](docs/DEFINITION_OF_DONE.md) | DoD for tasks, features, sprints, detection rules |
| [docs/UI_UX_SPECIFICATION.md](docs/UI_UX_SPECIFICATION.md) | Screens, flows, design tokens, accessibility |
| [docs/OBSERVABILITY.md](docs/OBSERVABILITY.md) | Metrics, dashboards, alerting |
| [docs/DEVSECOPS.md](docs/DEVSECOPS.md) | CI/CD pipeline, gates, branching, releases |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Compose profiles, configuration, backup/restore |
| [docs/AGENT_SPECIFICATION.md](docs/AGENT_SPECIFICATION.md) | Development agents and orchestration |
| [docs/SKILLS_SPECIFICATION.md](docs/SKILLS_SPECIFICATION.md) | Reusable skill definitions |
| [docs/MCP_SPECIFICATION.md](docs/MCP_SPECIFICATION.md) | MCP integrations and permission scopes |
| [docs/ROADMAP.md](docs/ROADMAP.md) | 10-week, 5-sprint plan |
| [docs/sprints/SPRINT_01.md](docs/sprints/SPRINT_01.md) | Implementation-ready Sprint 1 specification |
| [docs/HANDOFF_SONNET.md](docs/HANDOFF_SONNET.md) | Exact instructions for the implementation model |
| [docs/adr/](docs/adr/) | Architecture Decision Records |
| [docs/PLANNING_REPORT.md](docs/PLANNING_REPORT.md) | Planning quality-gate report, risks |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Human decision log (approved / open) |
| [docs/PLANNING_AUDIT_REPORT.md](docs/PLANNING_AUDIT_REPORT.md) | Planning audit, corrections and readiness |
| [docs/FINAL_PLANNING_READINESS.md](docs/FINAL_PLANNING_READINESS.md) | Current approval state and readiness summary |

## Ground rules

- **Defensive only.** No offensive tooling, exploitation, malware, uncontrolled scanning or automated destructive response.
- **Synthetic data only** in this repository and its demo environment. Never load real production logs or credentials.
- **External integrations are optional.** The platform runs fully offline; the AI analyst and MISP are opt-in.

## Quick start

Not available yet — added in Sprint 1 (see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)).

## Licence

To be decided before the first public release (see [docs/PLANNING_REPORT.md](docs/PLANNING_REPORT.md), decision D-01).
