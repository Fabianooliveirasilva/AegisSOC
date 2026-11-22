# AegisSOC — Requirements and Acceptance Criteria

Single source of truth for **functional requirements** and their **measurable acceptance criteria**. Each `AC-*` is implemented in the sprint shown and verified by the test cases listed in [TEST_PLAN.md](TEST_PLAN.md). Security requirements (`SR-*`) live in [SECURITY.md](../SECURITY.md).

Format: **ID — requirement.** *Given/When/Then or measurable criteria.* `[Sprint]`

---

## PLAT — Platform foundation

- **AC-PLAT-01 — Login.** Given an active user with valid credentials, `POST /auth/login` returns 200, sets `__Host-aegis_session` with `Secure; HttpOnly; SameSite=Strict; Path=/`, and returns a CSRF token. Wrong password and unknown user return the same 401 body; a throttled attempt returns the same 429 body whether or not the user exists. `[S1]`
- **AC-PLAT-02 — Logout.** `POST /auth/logout` returns 204, the session key no longer exists in Redis, and the old cookie value yields 401 on `/auth/me`. `[S1]`
- **AC-PLAT-03 — Session expiry.** A session idle > 30 min or older than 8 h returns 401 (verified with an injected clock). Session ID changes on login. `[S1]`
- **AC-PLAT-04 — CSRF.** Any POST/PUT/PATCH/DELETE with a valid cookie but missing or wrong `X-CSRF-Token` returns 403 `csrf-failed`; with the correct token it succeeds. `[S1]`
- **AC-PLAT-05 — Brute-force protection (decision D-09).** After 5 consecutive failures for a username, the next attempt within 30 s returns 429 with `Retry-After`; each further failure doubles the delay up to 900 s (verified with an injected clock: 30, 60, 120, 240, 480, 900, 900 s). Attempts during the delay are rejected without password verification and do not lengthen it. The 21st attempt within 60 s from one IP returns 429. Behaviour is identical for unknown usernames. There is no hard lockout. An `auth.login.repeated_failures` audit event is written at 10 consecutive failures and is visible to admins; an admin reset clears the delay and is audited. `[S1]`
- **AC-PLAT-06 — RBAC.** For every (role, route) pair the response matches the permission matrix in SECURITY.md §3.2 (403 where not permitted); a route without a declared permission makes the test suite fail. `[S1, extended every sprint]`
- **AC-PLAT-07 — User administration.** An admin can create, list, update role and deactivate users, and reset a user's login throttle; role change or deactivation revokes the target's sessions within 1 s; an admin cannot demote or deactivate themselves (409). `[S1]`
- **AC-PLAT-08 — Audit trail.** Every action listed in SR-17 that exists in the current sprint produces exactly one `audit_log` row with actor, action, target, outcome, IP and request ID; `UPDATE`/`DELETE`/`TRUNCATE` on `audit_log` as `aegis_app` fail, and purging is possible only through `aegis_purge_audit_before` with its 90-day floor. `GET /audit-log` is filterable and admin-only. `[S1, extended]`
- **AC-PLAT-09 — Health.** `/health/live` returns 200 while the process runs; `/health/ready` returns 503 within 2 s of Postgres or Redis becoming unavailable and 200 within 5 s of recovery; output contains no hostnames or versions. `[S1]`
- **AC-PLAT-10 — Error model.** All 4xx/5xx responses are `application/problem+json` with `request_id`; 500 responses contain no stack trace; `X-Request-ID` is echoed. `[S1]`
- **AC-PLAT-11 — Security headers.** Responses through the edge carry all headers in SR-20; HTTP requests redirect to HTTPS. `[S1]`
- **AC-PLAT-12 — Bootstrap admin.** `aegissoc admin create` creates the first admin from stdin or a secrets file, refuses a weak password, and refuses to run a second time without `--force-additional`. `[S1]`
- **AC-PLAT-13 — Web login and shell.** A user can log in through the SPA, sees the app shell with navigation filtered by role, can log out, and is redirected to login on 401. Keyboard-only login works. `[S1]`
- **AC-PLAT-14 — OpenAPI contract.** `docs/api/openapi.json` is generated from code; CI fails if it is stale `[S1]`. From Sprint 2, CI also fails on a breaking change against the `v0.1.0` snapshot unless the PR has the `api-breaking` label `[S2]`.
- **AC-PLAT-15 — One-command local stack.** `make up` on a clean machine with Docker brings the `core` profile to healthy in ≤ 3 min (excluding image download); total memory of core containers ≤ 2.5 GB at idle. `[S1]`
- **AC-PLAT-16 — CI pipeline.** On every PR the pipeline runs lint, type-check, unit, integration, API, E2E smoke, SAST, dependency, secret and container scans; a High/Critical finding or test failure blocks merge. `[S1]`

## SIEM — Module A

- **AC-SIEM-01 — Sources and keys.** An admin can create a log source and generate an API key shown exactly once; only the hash is stored; revoking a key makes the next ingest request with it return 401 within 1 s. `[S2]`
- **AC-SIEM-02 — Ingestion endpoint.** A valid batch of ≤ 500 records ≤ 1 MiB returns 202 with a batch ID in p95 ≤ 100 ms at 50 req/s; > 500 records → 422; > 1 MiB → 413; invalid key → 401; session cookie on ingest → 401. `[S2]`
- **AC-SIEM-03 — Parsers.** Parsers exist for `json_generic`, `windows_security`, `sysmon`, `linux_auth`, `nginx_access`, `cloud_audit`; each passes its golden-file tests (≥ 10 samples per type) and a property-based test of 1,000 random inputs with zero unhandled exceptions. `[S2]`
- **AC-SIEM-04 — Normalisation.** Normalised events contain `@timestamp`, `event.ingested`, `event.kind`, `event.category`, `aegis.source_id`, `aegis.data_origin` and the type-specific ECS fields in SYSTEM_DESIGN §3.3; hot columns equal the corresponding `doc` values. `[S2]`
- **AC-SIEM-05 — Source binding and server-set fields.** Payload values for `aegis.*`, `event.ingested` and source identity are ignored/overwritten; verified by abuse case §5.2 in the threat model. `[S2]`
- **AC-SIEM-06 — Idempotency.** Redelivering the same stream message (simulated worker crash before ACK) produces no duplicate events or alerts. `[S2]`
- **AC-SIEM-07 — Ingest errors and DLQ.** A record that fails parsing is stored in `ingest_errors` with stage and redacted excerpt while the rest of the batch is stored; a message failing 5 times lands in the DLQ; both are visible in the UI. `[S2]`
- **AC-SIEM-08 — Event search.** `POST /events/search` supports all DSL operators in SYSTEM_DESIGN §6.1, cursor pagination and full-text; on 1 M events a 24 h query filtered by `host.name` returns the first page in p95 ≤ 1 s. Disallowed fields → 422. `[S2]`
- **AC-SIEM-09 — Event detail and timeline.** Event detail shows the full normalised document; entity timeline returns events (and alerts, from S3) for host/user/IP ordered by time. `[S2]`
- **AC-SIEM-10 — Ingestion health.** Each source shows status `healthy|degraded|silent|disabled`, last event time and EPS; a source with no events for > 3× its expected interval becomes `silent` within 2 min. `[S2]`
- **AC-SIEM-11 — Retention.** The retention job creates partitions 7 days ahead and drops partitions older than the configured maximum; run is audited with counts; verified with an injected clock. `[S2]`
- **AC-SIEM-12 — Backpressure.** When stream lag exceeds the threshold, ingest returns 429 with `Retry-After`; no accepted batch is lost (accepted count = stored + failed). `[S2]`
- **AC-SIEM-13 — Synthetic generator.** `make demo-data` produces baseline traffic for all six source types at a configurable EPS and can inject named storylines deterministically (`--seed`) with a ground-truth manifest. Only documentation IP ranges and `.test`/`example.com` domains appear. `[S2]`
- **AC-SIEM-14 — Events explorer UI.** Users can build filters, run full-text search, paginate, open event detail and pivot to an entity timeline; loading, empty and error states are present. `[S2]`
- **AC-SIEM-15 — Fluent Bit (optional profile).** With `--profile fluentbit`, lines appended to sample `auth.log`/`access.log` appear as events within 10 s. `[S2 stretch]`

## DET — Module B

- **AC-DET-01 — Rule management and versioning.** Creating or editing a rule creates an immutable version with incrementing number and content hash; identical content does not create a new version; version history and diff are viewable. `[S3]`
- **AC-DET-02 — Static validation.** Validation reports structured findings for each check in SYSTEM_DESIGN §4.2; a rule with an unmapped field, unsupported modifier, invalid ATT&CK tag or RE2-incompatible regex cannot leave `draft`. `[S3]`
- **AC-DET-03 — Evaluator correctness.** The evaluator passes the conformance suite (≥ 60 cases covering each supported modifier, condition operator, case sensitivity, lists, null handling); branch coverage of the evaluator ≥ 90 %. `[S3]`
- **AC-DET-04 — Streaming detection.** An event matching an active rule produces an alert within p95 ≤ 5 s of ingest at 500 EPS with 12 active rules; events are only evaluated against rules whose logsource matches. `[S3]`
- **AC-DET-05 — ATT&CK catalogue.** `aegissoc mitre import` loads a pinned ATT&CK Enterprise bundle (tactics, techniques, sub-techniques, version recorded); rules display mapped techniques; coverage endpoint returns the matrix. `[S3]`
- **AC-DET-06 — Severity.** Alert severity derives from Sigma `level` per mapping in SYSTEM_DESIGN §4.4. `[S3]`
- **AC-DET-07 — Lifecycle and four-eyes.** State transitions follow the lifecycle diagram; approval by the author returns 403; activation without a passing regression run < 24 h old returns 409; disable requires a reason; all transitions audited. `[S3]`
- **AC-DET-08 — Detection-as-code.** `aegissoc detections sync` imports changed files as draft versions (never activates); `aegissoc detections validate|test` exit non-zero on any failure and are used in CI. `[S3]`
- **AC-DET-09 — Correlation.** `event_count`, `value_count` and `temporal` correlation rules produce correlated alerts linked to contributing alerts; D01, D02, D04 and D09 scenarios pass. `[S4]`
- **AC-DET-10 — Detection metrics.** Per rule: alert volume, disposition counts, FP rate, precision, evaluation p95 over 30 days; values labelled simulated when computed from synthetic sources. `[S3 basic, S4 dispositions]`
- **AC-DET-11 — Rules UI.** List, filter, view versions, edit with YAML editor, see validation findings inline, run ad-hoc test against sample events, approve/activate/disable per role. `[S3]`
- **AC-DET-12 — Initial content.** The 12 MVP rules (D01–D12) are active with ≥ 1 positive and ≥ 1 negative scenario each. `[S3: D03, D05–D08, D10–D12; S4: D01, D02, D04, D09]`
- **AC-DET-13 — Alert deduplication.** Matches with the same dedup key within the window update one open alert (`event_count` increments) instead of creating new alerts. `[S3]`

## INC — Module C (alerts and incidents)

- **AC-INC-01 — Alert queue.** Analysts can filter alerts by status, severity, rule, technique, assignee and time; triage (assign, change status) with optimistic locking. `[S3]`
- **AC-INC-02 — Disposition and FP tracking.** Closing an alert requires a disposition; dispositions feed rule metrics within 5 min. `[S4]`
- **AC-INC-03 — Bulk triage.** Up to 100 alerts can be assigned or closed in one request; each change audited. `[S4]`
- **AC-INC-04 — Create incident from alerts.** An analyst creates an incident from 1..n alerts; alerts are linked, timeline entry created, matching playbooks suggested. `[S4]`
- **AC-INC-05 — Lifecycle.** Only transitions in SYSTEM_DESIGN §5.3 are allowed (409 otherwise); closing requires a resolution and propagates it as disposition to linked alerts without one; reopen requires reason. `[S4]`
- **AC-INC-06 — Assignment and ownership.** Incidents can be assigned to analysts; "My incidents" view; assignment changes appear in timeline and audit. `[S4]`
- **AC-INC-07 — Notes.** Notes are rendered as plain text; editing creates a revision; only the author can edit/delete. `[S4]`
- **AC-INC-08 — Evidence.** File evidence enforces SR-14 (size, type, hash, attachment download); reference evidence snapshots key fields; downloads audited; SHA-256 visible. `[S4]`
- **AC-INC-09 — Investigation timeline.** The timeline merges all entry types in SYSTEM_DESIGN §5.5 in chronological order and marks AI entries. `[S4]`
- **AC-INC-10 — Playbooks.** 5 MVP playbooks load from YAML; attaching one creates checklist steps; progress (% required done) shown; no step triggers external actions. `[S4]`
- **AC-INC-11 — Metrics.** Time-to-triage and time-to-close recorded per incident; overview shows MTTR (30 days). `[S4]`
- **AC-INC-12 — Incident UI.** Incident list and investigation workspace (summary, alerts, events, timeline, notes, evidence, playbook, AI panel) with all states. `[S4]`
- **AC-INC-13 — Incident report.** `GET /incidents/{id}/report` produces a Markdown report with summary, timeline, affected entities, ATT&CK techniques, evidence hashes and resolution. `[S4]`

## HUNT — Module D (threat hunting and intel)

- **AC-HUNT-01 — Hunt queries.** Analysts run DSL hunts with group-by aggregation from the hunting workspace; limits from SYSTEM_DESIGN §6.1 enforced (422 when exceeded). `[S4]`
- **AC-HUNT-02 — Saved hunts and runs.** Hunts store hypothesis, techniques and query; each run stores parameters, counts, duration, results snapshot and conclusion. `[S4]`
- **AC-HUNT-03 — Retro-hunt.** A rule version can be run over ≤ 7 days of history asynchronously; results stored as a hunt run, no alerts created. `[S4]`
- **AC-HUNT-04 — IOC lists.** CSV and STIX 2.1 (indicator pattern subset) imports with per-row error reporting; values normalised; invalid/over-broad IOCs (e.g. `0.0.0.0`, private ranges unless allowed) rejected. `[S4]`
- **AC-HUNT-05 — IOC matching.** An ingested event containing an IOC in a monitored field produces an IOC-match alert within p95 ≤ 5 s; expired IOCs do not match. `[S4]`
- **AC-HUNT-06 — Related activity.** For an entity and time, related events/alerts within the window are returned ranked by shared entities. `[S4]`
- **AC-HUNT-07 — Hunt report.** A hunt run exports a Markdown report and can be attached to an incident as evidence. `[S4]`
- **AC-HUNT-08 — MISP connector.** Pull-only connector imports attributes into an IOC list. `[Post-MVP]`

## AI — Module E

- **AC-AI-01 — Disabled by default.** With no API key or `AEGIS_AI_ENABLED=false`, AI endpoints return 503 `ai-disabled`, the UI shows an explanatory empty state, and no outbound connection is attempted (verified by network policy test). `[S5]`
- **AC-AI-02 — Explain event/alert.** Produces a validated envelope with summary, findings with citations and confidence, ATT&CK candidates and benign explanations. `[S5]`
- **AC-AI-03 — Summarise incident.** Produces summary, timeline and affected entities citing incident alerts/events. `[S5]`
- **AC-AI-04 — Next steps.** Ordered, rationale-bearing steps referencing data to check. `[S5]`
- **AC-AI-05 — Explain rule.** Plain-language explanation, FP sources and tuning ideas citing the rule version. `[S5]`
- **AC-AI-06 — Incident report draft.** Structured report sections; the human can copy into a note (it is never auto-saved as the official report). `[S5]`
- **AC-AI-07 — ATT&CK recommendations.** Suggested techniques exist in the local ATT&CK DB and carry citations. `[S5]`
- **AC-AI-08 — Evidence gaps.** Lists open questions vs the attached playbook's required steps. `[S5]`
- **AC-AI-09 — Structured output validation.** 100 % of stored `completed` analyses validate against the task schema; invalid provider output → status `rejected` with reasons. `[S5]`
- **AC-AI-10 — Citation enforcement.** In the fixture suite, findings citing unknown IDs are dropped; analyses with > 50 % dropped findings are `rejected`; no finding without citations is displayed. `[S5]`
- **AC-AI-11 — Prompt-injection resistance.** For the red-team fixture set (≥ 15 cases), no proposed action that the injection requested is auto-applied (always 0 auto-applied by design), and with the real provider (manual evaluation run) ≥ 90 % of cases produce a `prompt_injection_suspected` finding or ignore the instruction. `[S5]`
- **AC-AI-12 — Data minimisation.** The context manifest lists only allowlisted fields; redaction suite (≥ 20 secret patterns) shows 0 secrets in the outbound payload. `[S5]`
- **AC-AI-13 — Human-in-the-loop.** Proposed actions are applied only through the apply endpoint by a user with the underlying permission; audit shows the human actor and `ai_suggested=true`; dismissals recorded. `[S5]`
- **AC-AI-14 — Limits.** Per-user quota and daily token budget enforced (429); refusals stored as `refused` with category; provider timeouts → `failed` after ≤ 2 retries. `[S5]`
- **AC-AI-15 — AI UI.** AI panel shows status, confidence badges, citations as links, "AI-generated" labelling, proposed actions with Apply/Dismiss. `[S5]`

## QA — Module F

- **AC-QA-01 — Scenario format and runner.** Scenarios in the format of SYSTEM_DESIGN §8 run in `unit` mode (no DB) and `pipeline` mode; runner reports expected vs actual diff. `[S3]`
- **AC-QA-02 — Validation runs API.** Runs can be triggered for a rule version, a rule, all active rules or the regression suite; results persisted and visible in UI. `[S3 API, S5 UI]`
- **AC-QA-03 — Regression gate.** CI runs all scenarios on every PR touching `detections/` or `aegissoc/detection`; any failure blocks merge; activation requires a passing run < 24 h old. `[S3]`
- **AC-QA-04 — Quality indicators.** `/qa/metrics` exposes the indicators in QA_STRATEGY §8 with `simulated` flags. `[S5]`
- **AC-QA-05 — QA reports.** Each sprint produces a QA report from the template in `qa/templates/`; validation runs export as report. `[S1–S5]`
- **AC-QA-06 — Ground-truth evaluation.** For a seeded generator run with all storylines, recall per technique and false alerts outside storylines are computed and shown as simulated; target recall ≥ 0.9 for D01–D12 storylines. `[S5]`
- **AC-QA-07 — Coverage gates.** Coverage thresholds in QA_STRATEGY §6 enforced in CI. `[S1]`
- **AC-QA-08 — Traceability.** `make traceability` produces a matrix AC/SR → TC → latest result from test markers; no AC of a completed sprint lacks a passing test. `[S2 script, maintained]`

## OBS — Observability

- **AC-OBS-01 — Metrics endpoints.** api and worker expose the metrics in OBSERVABILITY.md §2 on `/metrics` reachable only on the internal network. `[S2 basic, S5 full]`
- **AC-OBS-02 — Dashboards.** With `--profile observability`, Grafana shows the provisioned dashboards in OBSERVABILITY.md §3 without manual setup. `[S5]`
- **AC-OBS-03 — Alerting rules.** Prometheus alert rules in OBSERVABILITY.md §4 are loaded and have unit tests (`promtool test rules`). `[S5]`
- **AC-OBS-04 — In-app overview.** The Security Overview screen shows EPS, alerts by severity, open incidents, MTTR, top rules and ingestion health, with "synthetic" badges. `[S3 basic, S5 full]`
