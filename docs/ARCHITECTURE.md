# AegisSOC — Architecture

| | |
|---|---|
| Status | Planning baseline — architecture accepted via ADRs (D-06), Sprint 1 scope approved (D-08). Changes follow ADR-0001 |
| Owner | Architect Agent (governance), human maintainer (approval) |
| Related | [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md) · [DATABASE_DESIGN.md](DATABASE_DESIGN.md) · [API_SPECIFICATION.md](API_SPECIFICATION.md) · [THREAT_MODEL.md](THREAT_MODEL.md) · [ADRs](adr/) · [Diagrams](diagrams/) |

This document is the single source of truth for **components, boundaries, communication, failure handling and data ownership**. Module internals live in SYSTEM_DESIGN.md; schemas in DATABASE_DESIGN.md; contracts in API_SPECIFICATION.md.

---

## 1. Context and constraints

| Constraint | Consequence |
|---|---|
| One part-time developer, 10 weeks, ~10–15 h/week, implementation by Claude Sonnet | Minimise moving parts; one backend language; one deployable backend image |
| Must run on a laptop via Docker Compose | Core stack must fit in **≤ 2.5 GB RAM**; heavy components (OpenSearch, Grafana) are optional profiles |
| Synthetic data, demo volumes | Design target: **sustained 500 events/s, burst 2,000 events/s**, 30-day hot retention ≈ 50–100 M rows worst case, typically far less |
| Portfolio quality | Clean module boundaries, tests, threat model and CI gates matter more than scale |
| External integrations optional | Platform must be fully functional offline; Anthropic API and MISP are opt-in |
| Defensive only | No response automation that changes external systems; playbooks are human-executed checklists |

## 2. Architectural style — decision

**Modular monolith with asynchronous workers** ([ADR-0002](adr/0002-modular-monolith-with-workers.md)).

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| Microservices (ingest, detection, incidents, AI… as separate services) | Independent scaling, fault isolation | Distributed transactions, service discovery, N× CI/containers, contract versioning between services, much higher cognitive load for a solo dev; no real scaling need | Rejected for MVP |
| **Modular monolith + workers** | One codebase, one image, in-process calls with enforced module boundaries, async work off the request path, easy local dev | Must enforce boundaries by tooling; single DB | **Chosen** |
| Plain monolith (all synchronous) | Simplest | Ingestion and detection would block API requests; no backpressure | Rejected |

Module boundaries are enforced with **import-linter** contracts in CI: modules talk only through each other's `service` interfaces, never through another module's tables or ORM models. This keeps a later extraction (e.g. the ingestion pipeline) feasible without designing for it now.

## 3. Component overview

See [diagrams/system-architecture.md](diagrams/system-architecture.md) and [diagrams/component-diagram.md](diagrams/component-diagram.md).

### 3.1 Runtime processes

| Process | Image | Role | Independently deployable? |
|---|---|---|---|
| `edge` | Caddy (official) | TLS termination (`tls internal` locally), static SPA hosting, reverse proxy `/api/*`, security headers, request size limits | Yes (3rd‑party) |
| `api` | `aegissoc-backend` | FastAPI HTTP API (all modules' routers) | Same image as worker |
| `worker` | `aegissoc-backend` | Stream consumers: normaliser, detector, correlator, IOC matcher, AI jobs, QA jobs; scheduler (leader-elected) | Same image as api, different command; can scale horizontally per consumer group |
| `web` | build-only | Vite build → static assets copied into the `edge` image | Built separately, served by edge |
| `postgres` | PostgreSQL 16 | System of record for everything, including events | Yes (3rd‑party) |
| `redis` | Redis 7 | Streams (pipeline + jobs), sessions, rate-limit counters, correlation state, IOC lookup sets, leader lock | Yes (3rd‑party) |
| `generator` *(profile)* | `aegissoc-generator` | Synthetic log producer (benign baseline + attack storylines) posting to ingestion API | Yes |
| `fluent-bit` *(profile)* | Fluent Bit (official) | Optional shipper: tails sample log files and forwards to ingestion API | Yes (3rd‑party) |
| `prometheus`, `grafana` *(profile)* | official | Metrics scraping and dashboards | Yes (3rd‑party) |
| `opensearch` *(profile, post-MVP)* | official | Optional search backend for large event volumes | Yes (3rd‑party) |

### 3.2 Backend modules (inside `aegissoc`)

| Module | Responsibility | Owns data | Depends on |
|---|---|---|---|
| `core` | Settings, logging, DB/Redis clients, error model, pagination, IDs, clock, metrics | — | — |
| `platform.auth` | Users, password hashing, sessions, CSRF, RBAC, API keys | `users`, `api_keys`; Redis `sess:*`, `auth:fail:*` | core, audit |
| `platform.audit` | Append-only audit trail | `audit_log` | core |
| `siem` | Log sources, ingestion endpoint, parsers, normalisation, event store, search, timelines, ingestion health, retention | `log_sources`, `events`, `ingest_batches`, `ingest_errors`, `retention_policies` | core, auth, audit |
| `detection` | Sigma rules + versions, static validation, evaluator, correlation rules, ATT&CK catalogue, detection metrics | `detection_rules`, `detection_rule_versions`, `rule_techniques`, `mitre_*`, `correlation_state` (Redis) | core, siem (read API), alerts |
| `alerts` | Alert creation, dedup, triage, disposition (TP/FP/benign) | `alerts`, `alert_events` | core, auth, audit |
| `incidents` | Incidents, lifecycle, assignment, notes, evidence, timeline, playbooks | `incidents`, `incident_alerts`, `incident_notes`, `evidence`, `incident_timeline`, `playbooks`, `playbook_steps`, `incident_playbook_steps` | core, auth, audit, alerts |
| `intel` | IOC lists, IOC import, IOC matching, (post-MVP) MISP connector | `ioc_lists`, `iocs`, `ioc_matches`; Redis `ioc:*` | core, siem, alerts |
| `hunting` | Query DSL execution, saved hunts, retro-hunts, hunt reports | `hunts`, `hunt_runs` | core, siem (read), detection (evaluator) |
| `ai` | Context building, redaction, LLM client, tool loop, output validation, proposed actions | `ai_analyses`, `ai_proposed_actions` | core, auth, audit, read APIs of siem/alerts/incidents/detection |
| `qa` | Detection scenario runner, validation runs, QA metrics, reports | `rule_test_scenarios`, `validation_runs`, `validation_results` | core, detection (evaluator) |
| `observability` | Prometheus metrics exposition, health/readiness | — | core |

Rule: **a module writes only its own tables.** Cross-module reads go through the owning module's service functions. Enforced by import-linter (no `from aegissoc.siem.models import …` outside `siem`).

## 4. Communication

| From → To | Protocol | Sync/async | Notes |
|---|---|---|---|
| Browser → edge | HTTPS (HTTP/2) | sync | Single origin; no CORS needed |
| edge → api | HTTP/1.1 on internal network | sync | `X-Forwarded-*` trusted only from edge |
| Log source / generator / Fluent Bit → edge → api `/api/v1/ingest/*` | HTTPS + `Authorization: Bearer <ingest key>` | sync accept, async processing | Returns `202` with batch id once durably queued |
| api → Redis Streams | RESP (redis-py asyncio) | async hand-off | `XADD` with `MAXLEN ~` cap for backpressure |
| worker ↔ Redis Streams | consumer groups (`XREADGROUP`, `XACK`, `XAUTOCLAIM`) | async | At-least-once delivery; consumers idempotent |
| api/worker → PostgreSQL | asyncpg via SQLAlchemy 2.0 async | sync | Transaction per request / per batch |
| worker → Anthropic API | HTTPS via official `anthropic` SDK | async job | Optional; disabled without key |
| Prometheus → api/worker `/metrics` | HTTP on internal network | pull | `/metrics` is **not** routed through edge |

### Streams and consumer groups

| Stream | Producer | Consumer group(s) | Payload |
|---|---|---|---|
| `aegis:ingest:raw` | api (ingest endpoint) | `normaliser` | `{batch_id, source_id, source_type, received_at, records[]}` |
| `aegis:events:normalized` | worker/normaliser | `detector`, `ioc-matcher` | `{event_ids[], partition_day}` (events already committed to Postgres) |
| `aegis:alerts:new` | alerts service | `correlator` | `{alert_id, rule_id, group_key, ts}` |
| `aegis:jobs:ai` | api (AI endpoint) | `ai-runner` | `{analysis_id}` |
| `aegis:jobs:qa` | api (QA endpoint), CI | `qa-runner` | `{validation_run_id}` |

All payloads are **JSON**. No pickle or other executable serialisation ([ADR-0004](adr/0004-redis-streams-for-async-processing.md)).

## 5. Failure handling

| Failure | Detection | Behaviour |
|---|---|---|
| Postgres down | readiness probe, connection errors | api `/ready` → 503; ingest returns 503 `Retry-After`; workers pause consumption and retry with exponential backoff (max 30 s) without ACKing |
| Redis down | readiness probe | api returns 503 for ingest and for authenticated requests (sessions live in Redis); workers back off |
| Parser error on a record | exception in normaliser | Record written to `ingest_errors` (raw truncated to 8 KiB, reason, batch id); rest of batch continues; metric `aegis_ingest_records_failed_total` |
| Worker crash mid-batch | un-ACKed message stays pending | Another consumer reclaims after 60 s via `XAUTOCLAIM`; idempotency keys prevent duplicate events/alerts |
| Poison message (fails 5 times) | delivery count from `XPENDING` | Moved to `aegis:dlq` stream + `ingest_errors`; ACKed; alert on DLQ growth |
| Stream backlog grows | `XLEN`/lag metric | Ingest endpoint returns `429` with `Retry-After` when `aegis:ingest:raw` lag > 100k entries (backpressure) |
| Anthropic API error/timeout/refusal | SDK exceptions, `stop_reason` | Analysis marked `failed` or `refused` with reason; never retried more than 2 times; UI shows status; rest of platform unaffected |
| Rule evaluation timeout | per-event evaluation budget | Rule marked `degraded`, evaluation skipped and counted; RE2 regex engine prevents catastrophic backtracking |
| Scheduler leader lost | Redis lock TTL 30 s | Another worker acquires lock; jobs are idempotent (partition creation, retention) |

Idempotency: events carry `dedup_key = sha256(source_id ‖ raw_hash)` → unique constraint on `(event_time, source_id, dedup_key)`, so redelivered records collapse; alerts use a partial unique index on `(rule_id, dedup_key)` for open alerts (dedup window enforced in the alert service); `alert_events` has PK `(alert_id, event_id)`.

## 6. Data ownership and storage

| Data | Store | Owner module | Retention (default) |
|---|---|---|---|
| Normalised events | Postgres `events` (range-partitioned by day) | siem | 30 days (configurable per source class) |
| Raw records | Not stored after normalisation, except failures in `ingest_errors` (truncated) | siem | 7 days |
| Alerts, incidents, notes, evidence metadata | Postgres | alerts / incidents | 365 days |
| Evidence files | Local volume `evidence/` (content-addressed by SHA-256) | incidents | Same as incident |
| Rules, versions, scenarios, validation runs | Postgres + git (`detections/`) | detection / qa | Indefinite |
| Audit log | Postgres `audit_log` (append-only: app role lacks UPDATE/DELETE/TRUNCATE, owner-only triggers, purge only via owner function with 90-day floor — DATABASE_DESIGN §6) | audit | 365 days |
| AI analyses | Postgres | ai | 90 days |
| Sessions, rate counters, correlation windows, IOC sets | Redis (ephemeral, AOF enabled) | auth / detection / intel | TTL-based |

Search infrastructure: **PostgreSQL** (B-tree, GIN on JSONB, `tsvector` full-text) for the MVP. OpenSearch is an optional, post-MVP backend behind a `EventSearchBackend` interface ([ADR-0003](adr/0003-postgresql-primary-store-opensearch-optional.md)).

## 7. Frontend architecture

React + TypeScript SPA ([ADR-0009](adr/0009-frontend-stack.md)):

- **Routing:** React Router; route-level code splitting.
- **Server state:** TanStack Query; no global client store beyond small UI state (Zustand only if needed).
- **API client:** generated types from the committed OpenAPI snapshot (`openapi-typescript` + `openapi-fetch`); the CSRF header is attached by a single fetch middleware.
- **UI:** Tailwind CSS + shadcn/ui (Radix primitives, copied into repo, not a runtime dependency on a hosted library); TanStack Table for dense tables; Recharts for charts.
- **Security:** no `dangerouslySetInnerHTML`; all log content rendered as text; strict CSP from edge.
- Structure: `src/app` (routing, providers), `src/features/<module>` (pages, hooks, components per module), `src/components/ui` (shadcn), `src/lib` (api client, formatting).

## 8. API gateway and authentication

There is no separate API gateway service; **Caddy** acts as the edge (TLS, headers, size limits, static hosting) and FastAPI enforces authentication, authorisation and rate limiting in middleware/dependencies ([ADR-0007](adr/0007-authentication-sessions.md), [ADR-0008](adr/0008-edge-proxy-caddy.md)).

| Principal | Credential | Can call |
|---|---|---|
| Human user | Server-side session cookie `__Host-aegis_session` + `X-CSRF-Token` header on unsafe methods | All `/api/v1/*` except ingest, subject to RBAC |
| Ingestion source | API key `Authorization: Bearer aik_<id>_<secret>` (hash stored, bound to one `log_source`) | `/api/v1/ingest/*` only |
| Prometheus | network position (internal network only) | `/metrics` only |

Roles: `admin`, `detection_engineer`, `analyst`, `viewer`. Permission matrix in [SECURITY.md §3.2](../SECURITY.md#32-rbac-permission-matrix).

## 9. AI analyst architecture (summary)

Full design in [SYSTEM_DESIGN.md §7](SYSTEM_DESIGN.md#7-module-e--ai-security-analyst) and [ADR-0010](adr/0010-ai-analyst-claude-messages-api.md).

- Runs as an **asynchronous job** in the worker, using the Claude **Messages API** with a host-side tool loop over **read-only** tools (the data never leaves except the minimised context we send).
- Output constrained by JSON Schema (`output_config.format`) and re-validated with Pydantic; every finding must cite source IDs that exist in the supplied context — uncited or unknown citations are rejected.
- Consequential actions are only **proposed**; a human applies them through the normal API, which records the human as the actor.
- Provider is pluggable: `anthropic` (real) or `fixture` (deterministic, used in tests and offline demos).

## 10. Observability (summary)

Structured JSON logs (structlog) with `request_id`/`trace_id`, Prometheus metrics from api and worker, optional Grafana dashboards. Details and metric catalogue: [OBSERVABILITY.md](OBSERVABILITY.md).

## 11. Deployment (summary)

Docker Compose with profiles `core`, `generator`, `fluentbit`, `observability`, `search`. Networks: `public_net` (edge only, for published ports), `edge_net` (edge↔api and log shippers, internal), `app_net` (api/worker↔redis/postgres, internal), `obs_net`, and `egress_net` (worker only, when AI is enabled). Only the edge publishes ports, bound to `127.0.0.1`. Details: [DEPLOYMENT.md](DEPLOYMENT.md), [diagrams/deployment-diagram.md](diagrams/deployment-diagram.md).

## 12. Technology stack evaluation

| Area | Proposed | Decision | Justification / alternative considered |
|---|---|---|---|
| Frontend | React, TypeScript, Vite, Tailwind, shadcn/ui | **Adopt** | Mainstream, MIT-licensed, strong typing; shadcn components are copied source (no lock-in). Alternative: Mantine (faster to start, less control over density/theme) |
| Backend | Python, FastAPI, Pydantic v2, SQLAlchemy 2.0 | **Adopt** | Best ecosystem for security tooling (pySigma, STIX), native OpenAPI, async; all MIT/BSD |
| Migrations | Alembic | **Adopt** (added) | Standard with SQLAlchemy |
| Primary DB | PostgreSQL 16 | **Adopt** | Relational integrity for incidents/audit; partitioning + JSONB + FTS is sufficient for demo-scale events |
| Search | OpenSearch | **Defer (optional profile, post-MVP)** | 2–4 GB RAM, extra ops, index mapping work; not needed at demo scale. Kept behind an interface ([ADR-0003](adr/0003-postgresql-primary-store-opensearch-optional.md)) |
| Cache/queue | Redis 7 | **Adopt** | Streams give durable, replayable, consumer-group processing; also sessions and counters. Licence note: Redis 7.4+ moved to RSAL/SSPL then added AGPLv3 in 8.0 — for local use all are acceptable; **Valkey** (BSD) is a drop-in alternative if licence matters |
| Task processing | Celery | **Replace with Redis Streams consumers** | Celery's default pickle concerns, weaker async story with FastAPI, and it adds a broker abstraction we don't need. Streams give ordering, replay and backpressure natively ([ADR-0004](adr/0004-redis-streams-for-async-processing.md)). Alternatives considered: Dramatiq, arq |
| Log shipper | Fluent Bit | **Adopt as optional profile** | Demonstrates real shipping; core demo uses the generator posting directly ([ADR-0011](adr/0011-ingestion-http-api-fluent-bit-optional.md)) |
| Detection format | Sigma + pySigma | **Adopt** | Industry standard; pySigma (LGPL-2.1, used as a library — compatible) parses and validates; evaluation by our own engine ([ADR-0005](adr/0005-sigma-pysigma-custom-evaluator.md)) |
| Regex engine | `google-re2` | **Adopt** (added) | Linear-time regex for user-supplied Sigma `re` modifiers (ReDoS protection) |
| Event schema | ECS subset | **Adopt** (added) | Common, documented field names; easy Sigma field mapping ([ADR-0006](adr/0006-normalized-event-schema-ecs-subset.md)) |
| ATT&CK | MITRE ATT&CK Enterprise STIX bundle | **Adopt** | Pinned version imported to DB; attribution per ATT&CK Terms of Use |
| Threat intel | IOC lists; MISP | **IOC lists in MVP; MISP optional post-MVP** | MISP is heavy to run; a pull-only connector is enough |
| AI | Anthropic API, structured outputs, tool use, HITL | **Adopt** | Messages API + host-side read-only tools ([ADR-0010](adr/0010-ai-analyst-claude-messages-api.md)) |
| Backend tests | Pytest, HTTPX | **Adopt** | + `pytest-asyncio`, `hypothesis` for parser fuzzing |
| E2E | Playwright + TypeScript | **Adopt** | |
| API collections | Postman-compatible | **Adopt (generated)** | Generated from OpenAPI with `openapi-to-postmanv2` in CI artefacts, not hand-maintained |
| Perf tests | — | **k6 (container image)** (added) | Scriptable, no local install |
| DevSecOps | Docker, Compose, GitHub Actions, Bandit, Semgrep, Trivy, Gitleaks | **Adopt** | + `pip-audit`, `pnpm audit`, Trivy SBOM. Semgrep CE rules only (licence: Semgrep Rules License permits internal use) |
| Edge | — | **Caddy** (added) | Automatic local TLS, simple config, secure headers ([ADR-0008](adr/0008-edge-proxy-caddy.md)) |
| Python tooling | — | **uv, ruff, mypy, import-linter** (added) | Fast, reproducible lockfile; boundary enforcement |

Estimated running cost: **$0** offline. With AI enabled, cost is per-analysis and bounded by per-analysis token limits and a daily budget setting (see SYSTEM_DESIGN §7.8).
