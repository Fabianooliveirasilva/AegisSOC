# AegisSOC — Planning Package Audit Report

| | |
|---|---|
| Date | 2026-11-21 (revision 1: audit · **revision 2: corrections applied**, same day) |
| Auditor | Claude Opus (planning model), self-audit against the Master Prompt and the user's audit checklist |
| Scope | Every file in the repository at audit time; consistency between architecture, database, API, security, QA and roadmap |
| Method | (1) file inventory via `find`; (2) automated ID/link check (every `AC/SR/TC/T/ADR` reference defined, every AC and SR mapped to a test, all relative links resolve); (3) targeted `grep` for suspected contradictions; (4) manual review of each document |
| **Verdict (rev. 2)** | **All 8 Sprint 1 blockers (B-1…B-8) are resolved** in the documentation (§12). Pre-Sprint-2 items remain open (§12.5). |
| **Approval state (verified against DECISIONS.md)** | **D-06 Approved** (ADRs accepted) and **D-08 Approved** (Sprint 1 scope) on 2026-11-21 by the maintainer's explicit instruction. **D-10 Open** — implementation not authorised, Sprint 1 not started, Sonnet not authorised. **D-05 Open** — needed before S1-T13. Source of truth: [DECISIONS.md](DECISIONS.md); summary: [FINAL_PLANNING_READINESS.md](FINAL_PLANNING_READINESS.md). |
| Verdict (rev. 1, historical) | Planning complete but not ready: 8 Sprint 1 blockers, 4 pre-Sprint-2/5 issues. |

> Sections 1–11 are the revision-1 audit, kept as the record of what was found. **Current status is in §12.**

> Note: the user referred to `DEVELOPMENT_ROADMAP.md`. No file with that name exists. The roadmap is **`docs/ROADMAP.md`** (the name the Master Prompt §16 specifies).

---

## 1. Complete file inventory

95 files at revision 1 (96 at revision 2, with `docs/DECISIONS.md`), 0 empty directories (empty folders hold `.gitkeep`). **0 source-code files** (`*.py`, `*.ts`, Dockerfiles, compose files, workflows: none). Line counts in parentheses.

### Root
| File | Purpose |
|---|---|
| `README.md` (82) | Vision, module overview, documentation map |
| `SECURITY.md` (153) | Disclosure policy, RBAC matrix, SR-01…SR-41, release checklist |
| `CLAUDE.md` (25) | Project rules for implementation sessions |
| `CONTRIBUTING.md` (25) | Workflow, coding standards |
| `.gitignore` (38) | Secrets, build artefacts, raw QA evidence |

### docs/ — planning documents
| File | Lines | | File | Lines |
|---|---|---|---|---|
| `ARCHITECTURE.md` | 196 | | `DEVSECOPS.md` | 88 |
| `SYSTEM_DESIGN.md` | 393 | | `DEPLOYMENT.md` | 97 |
| `THREAT_MODEL.md` | 110 | | `ROADMAP.md` | 174 |
| `QA_STRATEGY.md` | 134 | | `ACCEPTANCE_CRITERIA.md` | 123 |
| `TEST_PLAN.md` | 277 | | `DEFINITION_OF_DONE.md` | 55 |
| `API_SPECIFICATION.md` | 269 | | `UI_UX_SPECIFICATION.md` | 132 |
| `DATABASE_DESIGN.md` | 329 | | `OBSERVABILITY.md` | 72 |
| `AGENT_SPECIFICATION.md` | 182 | | `HANDOFF_SONNET.md` | 103 |
| `SKILLS_SPECIFICATION.md` | 176 | | `PLANNING_REPORT.md` | 149 |
| `MCP_SPECIFICATION.md` | 82 | | `PLANNING_AUDIT_REPORT.md` | this file |
| `sprints/SPRINT_01.md` | 213 | | `security/waivers.md` | 7 |

### docs/adr/ (18 files)
`README.md` (index), `0000-template.md`, `0001`…`0016` (see §3).

### docs/diagrams/ (8 files)
`README.md`, `system-architecture.md`, `component-diagram.md`, `data-flow.md`, `ingestion-sequence.md`, `detection-lifecycle.md`, `incident-response-sequence.md`, `deployment-diagram.md`.

### Governance and templates
`.github/PULL_REQUEST_TEMPLATE.md`, `.github/ISSUE_TEMPLATE/{bug_report.md, detection_defect.md, config.yml}`, `qa/templates/{QA_REPORT_TEMPLATE.md, BUG_REPORT_TEMPLATE.md, EVIDENCE_RECORD_TEMPLATE.md}`.

### Directory READMEs
`apps/README.md`, `apps/api/README.md`, `apps/web/README.md`, `services/README.md`, `services/synthetic-generator/README.md`, `qa/README.md`, `detections/README.md`, `data/README.md`, `infrastructure/README.md`, `agents/README.md`, `mcp/README.md`, `scripts/README.md`.

### Placeholders (`.gitkeep`, 0 lines)
`data/{hunts,iocs,mitre,playbooks,synthetic}`, `detections/{rules,correlation,scenarios}`, `infrastructure/{caddy,compose,docker,fluent-bit,observability}`, `qa/{api,integration,e2e,detection,security,performance,reports}`, `docs/api`, `docs/security/reviews`, `.github/workflows`.

### Intentionally absent (created after approval, per the specs)
`.claude/agents/*`, `.claude/skills/*`, `.claude/settings.json`, `.mcp.json`, `Makefile`, Dockerfiles, compose files, CI workflows, `docs/api/openapi.json`, `LICENSE`, `CHANGELOG.md`, `docs/sprints/SPRINT_02…05.md`.

## 2. Mandatory documents (Master Prompt §16)

| # | Document | Exists | Completeness |
|---|---|:-:|---|
| 1 | README.md | ✔ | Complete |
| 2 | ARCHITECTURE.md | ✔ | Complete; corrections M-1, M-2 |
| 3 | SYSTEM_DESIGN.md | ✔ | Complete; corrections M-1, M-3, m-9 |
| 4 | THREAT_MODEL.md | ✔ | Complete; add T-31, T-32 (§5) |
| 5 | SECURITY.md | ✔ | Complete; corrections B-5, B-6, m-1 |
| 6 | QA_STRATEGY.md | ✔ | Complete; QA gaps §6 |
| 7 | TEST_PLAN.md | ✔ | Complete; corrections B-3, m-6 |
| 8 | API_SPECIFICATION.md | ✔ | Complete |
| 9 | DATABASE_DESIGN.md | ✔ | Complete; corrections B-5, M-2, M-3 |
| 10 | AGENT_SPECIFICATION.md | ✔ | Complete; correction B-3 |
| 11 | SKILLS_SPECIFICATION.md | ✔ | Complete; scope reduction in §7 |
| 12 | MCP_SPECIFICATION.md | ✔ | Complete; package/flag names flagged "verify at creation" |
| 13 | DEVSECOPS.md | ✔ | Complete; correction m-3 |
| 14 | DEPLOYMENT.md | ✔ | Complete; corrections B-1, B-7, M-1 |
| 15 | ROADMAP.md | ✔ | Complete; correction B-4 |
| 16 | ACCEPTANCE_CRITERIA.md | ✔ | Complete; measurability issue M-4 |
| 17 | DEFINITION_OF_DONE.md | ✔ | Complete |
| 18 | ADR documents | ✔ | 16 ADRs, all *Proposed* |

**Missing mandatory documents: none.**

## 3. ADRs

| ADR | Topic | Exists | Status |
|---|---|:-:|---|
| 0001 | Record architecture decisions | ✔ | Proposed |
| 0002 | Modular monolith + workers | ✔ | Proposed |
| 0003 | PostgreSQL event store; OpenSearch optional | ✔ | Proposed — needs addendum for M-2 (partition privileges) |
| 0004 | Redis Streams instead of Celery | ✔ | Proposed — needs addendum for M-1 (memory-based backpressure) |
| 0005 | pySigma + own evaluator | ✔ | Proposed |
| 0006 | ECS subset | ✔ | Proposed |
| 0007 | Sessions, CSRF, API keys | ✔ | Proposed — affected by B-6 (lockout policy) |
| 0008 | Caddy edge | ✔ | Proposed |
| 0009 | Frontend stack | ✔ | Proposed |
| 0010 | AI analyst | ✔ | Proposed — verification item M-4b |
| 0011 | HTTP ingestion; Fluent Bit optional | ✔ | Proposed |
| 0012 | REST + code-first OpenAPI | ✔ | Proposed |
| 0013 | Monorepo tooling | ✔ | Proposed |
| 0014 | Agents are dev-time only | ✔ | Proposed |
| 0015 | Detection-as-code, four-eyes | ✔ | Proposed |
| 0016 | Observability | ✔ | Proposed |

Every decision that the Master Prompt asked to evaluate (architecture style, each proposed technology, Celery alternative, OpenSearch, MISP, AI approach) is covered. **Missing ADRs: none.**

## 4. Specific verifications requested

| Item | Result | Evidence |
|---|---|---|
| `sprints/SPRINT_01.md` exists with detailed instructions | ✔ | Fixed tech decisions, dependency graph, recommended order, PR grouping, 16 tasks with files/behaviour/tests, acceptance checklist, DoD, assumptions |
| Architecture diagrams (7 required) | ✔ all 7 | system, component, data-flow, ingestion sequence, detection lifecycle, incident-response sequence, deployment |
| Database ERD | ✔ | `DATABASE_DESIGN.md §1` Mermaid ERD covering all 35 tables in §2 |
| API contracts | ✔ | Conventions + endpoints for auth, ingestion, events, detections, alerts, incidents, hunting, AI, QA, admin |
| Threat modelling | ✔ | Assets, 6 trust boundaries, STRIDE per element, T-01…T-30, abuse cases, residual risks |
| Security requirements | ✔ | SR-01…SR-41 with RBAC matrix and release checklist |
| QA strategy | ✔ | Pyramid, environments, data, bug lifecycle, coverage, gates, indicators, independence protocol |
| Agent definitions | ✔ | 8 agents × 10 fields + orchestrator + human-approval list |
| Skills | ✔ | 17 skills × 7 fields; none claimed installed |
| MCP specifications | ✔ | Available vs proposed; scopes, auth, risks, failure handling |
| Every sprint has measurable ACs | ✔ with caveat | S1: 18 ACs; S2: 17; S3: 17; S4: 22; S5: 22 (AC-OBS/QA shared). Caveat M-4: several AI and UI ACs are not measurable as written |
| Automated ID/link check | ✔ | 92 AC, 41 SR, 135 TC, 30 T, 16 ADR — all references defined; every AC and SR mapped to ≥ 1 TC; 0 broken links |

## 5. Findings

Severity: **B** = blocks Sprint 1 approval · **M** = must be fixed before the sprint it affects (S2+) · **m** = minor, fix opportunistically.

### 5.1 Architectural inconsistencies

| ID | Sev | Finding | Where | Correction |
|---|---|---|---|---|
| **B-1** | B | **`make setup` ordering is contradictory.** DEPLOYMENT says `make setup` asks for the bootstrap admin password; SPRINT_01 S1-T01 says it only generates secrets; the admin CLI (S1-T10) needs a running DB, which does not exist until `make up`. | DEPLOYMENT §2/§3; SPRINT_01 S1-T01, §6 | `make setup` = secrets + hooks only. Add `make bootstrap-admin` (after `make up`), which runs `docker compose exec -it api aegissoc admin create`. CI uses `make setup-ci`, which generates the admin password into the secrets folder. Update DEPLOYMENT §3, SPRINT_01 T01/T10/§6, and the DEVSECOPS §5 target list. |
| **B-2** | B | **Cursor HMAC secret is undefined.** S1-T03 signs cursors with HMAC, but no secret exists in the configuration table or in secret generation. | SPRINT_01 S1-T03; DEPLOYMENT §2 | **Simplify:** drop the HMAC. Cursor values are only ever bound SQL parameters under the caller's own permissions, so tampering gains nothing. Validate the decoded structure strictly (malformed → 400). This removes a secret and a mechanism. |
| **M-1** | M (S2) | **Backpressure thresholds cannot fit in Redis memory.** Raw-stream entries are whole batches (up to 1 MiB). `MAXLEN ~1,000,000` and a lag threshold of 100,000 entries could require GBs, but Redis is limited to 256 MB with `noeviction` → writes fail with OOM before backpressure triggers. The Prometheus alert (lag > 50,000) is inconsistent with both. | SYSTEM_DESIGN §3.2; ARCHITECTURE §5; DEPLOYMENT §2; OBSERVABILITY §4; deployment diagram | Backpressure on **two signals**: lag > 2,000 entries **or** Redis `used_memory` > 60 % of `maxmemory`. `MAXLEN ~5,000`. Alert at lag > 1,000. Update all five places + ADR-0004 addendum. Add a TC for the memory-based trigger. |
| **M-2** | M (S2) | **Partition management needs privileges the app role lacks.** The scheduler (running as `aegis_app`) creates and drops partitions, but only the table owner (`aegis_owner`) can. | DATABASE_DESIGN §5–6; SYSTEM_DESIGN §3.7, §10 | Add `SECURITY DEFINER` functions owned by `aegis_owner` (`aegis_ensure_event_partitions(days_ahead)`, `aegis_drop_event_partitions_before(date)`), with fixed `search_path` and `EXECUTE` granted to `aegis_app`. Created by migration. ADR-0003 addendum. |
| **M-3** | M (S2) | **Events referenced by ID alone cannot be found efficiently.** The events PK is `(event_time, id)`. `evidence.ref_id`, AI citations, the `get_event` tool and the normalised-stream payload carry only `id` → every lookup scans every partition. | DATABASE_DESIGN §2.2, §2.5; SYSTEM_DESIGN §7.5 | (a) Add a partitioned B-tree index on `events(id)`; (b) wherever practical, carry `event_time` alongside `id` (stream payload, evidence snapshot, AI context). Document the "event reference = (event_time, id)" convention in SYSTEM_DESIGN §1. |
| m-9 | m | SYSTEM_DESIGN §4.2 lists `base64offset` inside the supported-modifier list while saying it is excluded. | SYSTEM_DESIGN §4.2 | Move it to an explicit "not supported in MVP" list. |
| m-10 | m | DEPLOYMENT's `core` profile includes `worker`, but Sprint 1 has no worker (S2). | DEPLOYMENT §1; SPRINT_01 T12 | Note "worker joins `core` in Sprint 2". |
| m-11 | m | `docs/runbooks/` is listed as a Blue Team write path but no such directory or plan exists. | AGENT_SPECIFICATION §3.2 | Either add `docs/runbooks/` (S4) or remove the path. |

### 5.2 Security gaps

| ID | Sev | Finding | Correction |
|---|---|---|---|
| **B-5** | B | **Audit-log immutability bypass is poorly designed.** The trigger allows UPDATE/DELETE when the custom setting `aegis.retention_job = 'on'`. Any session can `SET` a custom setting, so this does not identify a retention job. Today `aegis_app` lacks DELETE/UPDATE grants anyway, so the switch is both unnecessary and misleading. | Remove the setting check. Immutability = no UPDATE/DELETE grants for `aegis_app` **plus** a trigger that raises unless `current_user = 'aegis_owner'`. Retention runs via a `SECURITY DEFINER` function `aegis_purge_audit_before(ts)` owned by `aegis_owner`, which only deletes rows older than the policy and writes a summary audit row. Update DATABASE_DESIGN §2.1, SPRINT_01 S1-T04, SR-17 text. |
| **B-6** | B | **Hard account lockout lets anyone lock out any user.** With 10 failures → 15-minute lock, an unauthenticated attacker can keep the admin locked out indefinitely. This is a missing threat. | Decision for the human (see D-09). **Recommended:** replace the hard lockout with **progressive per-username delay** (after 5 failures, each attempt must wait 2^n s, capped at 15 min) plus the existing per-IP limit, with an admin notice on repeated lockouts. This keeps brute-force resistance (ASVS V2.2.1) without permanent denial. Add **T-31 Account lockout DoS** to THREAT_MODEL; update SR-05, AC-PLAT-05, ADR-0007 and TC-SEC-01. |
| **B-7** | B | **Demo account credentials are unspecified.** "Demo users per role are seeded", but nothing says how their passwords are created. If they are fixed, anyone on the LAN can log in. | `make seed` generates random passwords per demo user, writes them to `infrastructure/compose/secrets/demo_users.txt` (mode 600, git-ignored), and never prints them to logs. Add to SR-16 and DEPLOYMENT §3. Add **T-32 Default/demo credentials** to THREAT_MODEL. |
| m-1 | m | CSP allows `style-src 'unsafe-inline'`. It's needed only for inline `style` attributes from Radix. | Use `style-src 'self'; style-src-attr 'unsafe-inline'` (style elements stay restricted). Verify with the built SPA in S1-T12. |
| m-2 | m | Edge access logging is unspecified. If enabled, it could record `Authorization` (ingest keys) or `Cookie` headers. | In the Caddyfile, either disable access logs or explicitly filter/redact `Authorization`, `Cookie` and `Set-Cookie`. Add to SR-18 and TC-SEC-23. |
| m-12 | m | How the generator and Fluent Bit get their ingest keys is unspecified (S2). | `make seed` creates demo sources + keys → writes `secrets/ingest_<source>.key` → mounted as a Docker secret into generator/Fluent Bit only. Add to SPRINT_02 when written. |

### 5.3 QA gaps

| ID | Sev | Finding | Correction |
|---|---|---|---|
| **B-3** | B | **Guardrails contradict test procedures and agent duties.** (a) `.claude/settings.json` denies `Bash(curl:*)`, but TC-PLAT-09 is specified as "curl through edge". (b) Denying `Edit(./.github/workflows/**)` applies to **all** agents, so it also blocks the DevOps agent, whose job is the workflows. The spec's "except DevOps" cannot be expressed in shared settings. | (a) Restate TC-PLAT-09 as a pytest/HTTPX test against `https://localhost:8443` with the Caddy CA. Keep curl denied. (b) Change workflow edits from **deny** to **ask** (human confirms every CI change), and remove "except DevOps". |
| M-4 | M (S5) | **Several ACs are not objectively measurable.** AC-AI-02…08 describe content ("ordered, rationale-bearing steps"). AC-INC-12, AC-SIEM-14 and AC-DET-11 say "with all states". | For AI tasks: fixture-based assertions (schema valid; each required array non-empty; every finding has ≥ 1 valid citation; `next_steps.order` contiguous from 1; `attack_techniques` ⊆ local ATT&CK DB), plus a 5-point rubric scored on a fixed evaluation set for the live provider (target mean ≥ 4). For UI ACs: list the exact states per screen (loading/empty/error/403) and have E2E assert each. |
| M-4b | M (S5) | **Untested API assumption:** combining structured output (`output_config.format`) with tool use in the same request, and server-side fallback behaviour, are stated as design but not verified. | Before S5 coding: a spike task S5-T00 checks both against current Claude API docs. Fallback: run the tool loop without a format constraint, then a final call with the schema. ADR-0010 note. |
| m-3 | m | DEVSECOPS §5 target list lacks `docs-check`, `setup-ci`, `bootstrap-admin`, `trust-ca`, `psql`, `psql-ro`, all of which are referenced elsewhere. There is also no CI check that the frontend's generated API types are fresh. | Add the targets; add "frontend API types fresh" to the OpenAPI-check stage. |
| m-4 | m | The QA independence protocol says validation happens **per PR**, but the roadmap shows QA as one final task per sprint. | Clarify: S*-T14-style tasks build the suite and the sprint report; per-PR validation notes are continuous and mandatory. |
| m-5 | m | The flaky-test-rate indicator has no measurement method. | CI re-runs failed tests once (`pytest --last-failed` job step / Playwright `retries: 1` on CI only); a test that passes only on retry is counted as flaky and reported, never hidden. |
| m-6 | m | TC-PLAT-02's wall-clock timing assertion (< 50 ms) will be flaky on CI runners. | Replace with a unit test asserting the unknown-user path performs a dummy argon2 verify; keep the timing measurement as a non-blocking report. |
| m-7 | m | Performance tests need 1 M events (TC-PERF-03), but there's no bulk-load tool (the generator at 500 EPS would take about 33 minutes). | Add `aegissoc dev load-events --count N` (direct COPY of generated normalised events, dev/CI only) in S2. |
| m-8 | m | E2E role fixtures need one user per role, but how they're provisioned in CI isn't stated. | QA fixtures create users through the admin API using the CI admin from `make setup-ci`. Document in SPRINT_01 S1-T14. |

### 5.4 Implementation dependencies

| ID | Sev | Finding | Correction |
|---|---|---|---|
| **B-4** | B | **Sprint 1 is over capacity** (see §7). | Apply the reductions in §7 and update ROADMAP + SPRINT_01. |
| **B-8** | B | **Host prerequisites are undocumented.** DEPLOYMENT lists only Docker; a developer also needs `make`, `git`, `uv`, Python 3.12, Node 22 + `pnpm` (corepack), `pre-commit`, and (for local scans) `gitleaks`. Browsers for Playwright install via `pnpm exec playwright install`. | Add a "Developer prerequisites" table to DEPLOYMENT and SPRINT_01 §1 with minimum versions; `make setup` checks them and prints what is missing. |
| m-13 | m | External artefacts need pinned sources and licences: the common-password list (S1), the ATT&CK STIX bundle (S3), Caddy's local CA trust flow. | Record source URL, version, licence and SHA-256 in `data/README.md` / SPRINT files when added. |
| — | ✔ | Task-level dependencies for S1 (graph + order + PR grouping) and S2–S5 (per-task "depends on"). External decisions D-05 (GitHub repo) and D-02 (Redis/Valkey). | Documented |

## 6. QA gap summary

The QA architecture is sound: pyramid, independence protocol, traceability by markers, detection scenario lifecycle, coverage gates and quality indicators are all specified, and every AC/SR maps to a test. The gaps are B-3 (a test contradicts the guardrails), M-4/M-4b (measurability of AI ACs; unverified API assumption), and minor tooling items m-3…m-8.

## 7. Sprint 1 workload review

Estimated human hours using the roadmap's effort scale at midpoints (S = 1 h, M = 2 h, L = 4.5 h):

| | Hours |
|---|---|
| As planned (16 tasks: 6 S, 7 M, 3 L) | **≈ 33.5 h** — above the 20–30 h sprint capacity |

Reductions **that do not weaken security**:

| # | Change | Saves | Security impact |
|---|---|---|---|
| R1 | S1-T15: create only the agents used in S1 (QA Engineer, Security Reviewer, DevOps, Documentation) and only 2 skills (`python-backend`, `react-frontend`); the rest are created just in time in the sprint that needs them | ~1 h | none — guardrails (`settings.json`) still created in S1 |
| R2 | Drop cursor HMAC (B-2) | ~0.5 h | none (bound parameters, same permissions) |
| R3 | Move the **generic** read/write rate limiter to S2 (where ingestion needs the same framework); keep **login throttling** in S1 | ~1 h | negligible — the S1 attack surface is login, which stays protected |
| R4 | S1-T11: ship the audit log as API + test in S1; its UI page moves to S2 with the other admin pages. Users page stays | ~1.5 h | none — audit records still written and tested |
| R5 | Remove `hypothesis` from S1 deps (parsers are S2); start `oasdiff` breaking-change checks in S2 (no baseline contract exists before S1 ends). Snapshot-freshness check stays | ~0.5 h | none |
| R6 | TC-PLAT-02 timing → deterministic unit test (m-6) | ~0.5 h, and avoids flaky CI | none |
| | **Total after reductions** | **≈ 28.5 h** | within capacity, with a thin buffer |

**Do not cut:** argon2id, sessions + CSRF, RBAC matrix test, route-permission enforcement test, audit immutability, container hardening, all CI security scanners, the E2E smoke in CI.
**Cut line if S1 still exceeds 25 h by day 10:** move the Users admin **UI** to S2 (the API and its tests stay in S1).

## 8. Required corrections

### 8.1 Before Sprint 1 can be approved (blocking)

| # | Correction | Files to change |
|---|---|---|
| B-1 | Setup/bootstrap ordering: `make setup` → `make up` → `make bootstrap-admin`; `make setup-ci` for CI | DEPLOYMENT, SPRINT_01, DEVSECOPS §5 |
| B-2 | Remove cursor HMAC; strict cursor validation | SPRINT_01 S1-T03 |
| B-3 | TC-PLAT-09 via HTTPX; workflow edits = *ask* not *deny* | TEST_PLAN, AGENT_SPECIFICATION §2 |
| B-4 | Apply workload reductions R1–R6 | ROADMAP (S1, S2), SPRINT_01, SKILLS_SPECIFICATION §3 |
| B-5 | Audit immutability by grants + owner-only trigger + `SECURITY DEFINER` purge function | DATABASE_DESIGN §2.1, SPRINT_01 S1-T04, SECURITY SR-17 |
| B-6 | Lockout policy (needs decision D-09); add T-31 | SECURITY SR-05, ACCEPTANCE AC-PLAT-05, THREAT_MODEL, ADR-0007, SYSTEM_DESIGN §2, SPRINT_01 S1-T06, TEST_PLAN TC-SEC-01 |
| B-7 | Random demo credentials; add T-32 | SECURITY SR-16, DEPLOYMENT §3, THREAT_MODEL, QA_STRATEGY §4 |
| B-8 | Developer prerequisites table + `make setup` checks | DEPLOYMENT, SPRINT_01 §1 |

### 8.2 Before Sprint 2 starts
M-1 (memory-based backpressure), M-2 (partition functions), M-3 (event reference convention + `id` index), m-12 (ingest key distribution), m-7 (bulk loader), and writing `docs/sprints/SPRINT_02.md`.

### 8.3 Before Sprint 5 starts
M-4 (measurable AI/UI ACs), M-4b (structured output + tools + fallback spike).

### 8.4 Minor (fold into the sprint that touches the file)
m-1 … m-13.

## 9. Sprint readiness assessment

| Sprint | Readiness | Conditions |
|---|---|---|
| **S1** | 🟢 **Scope approved, not started** | B-1…B-8 resolved; D-06, D-08, D-09 approved; start requires D-10; D-05 before S1-T13 |
| S2 | 🟠 Task-level plan only | M-1, M-2, M-3, m-7, m-12 applied; `SPRINT_02.md` written from S1 outcomes |
| S3 | 🟠 Task-level plan only | `SPRINT_03.md`; pySigma and `google-re2` version and wheel availability checked for Python 3.12 |
| S4 | 🟠 Task-level plan only | `SPRINT_04.md` |
| S5 | 🟠 Task-level plan only | M-4, M-4b; decision D-04 (model per task) |

Detailed specs for S2–S5 are deliberately written at each sprint's start so they reflect what was actually built. This is planned, not a gap.

## 10. New decision raised by this audit

| ID | Decision | Options (recommendation first) | Blocking |
|---|---|---|---|
| D-09 | Login lockout policy | **Progressive per-username delay (cap 15 min) + per-IP limit** / keep hard lockout (simpler, but lets attackers lock users out) | Sprint 1 |

## 11. Conclusion

The package is **structurally complete**: all 17 mandatory documents, 16 ADRs, 7 diagrams + ERD, a detailed Sprint 1 spec and full ID traceability exist, with no code written. The audit found **8 Sprint 1 blockers** (B-1…B-8) — two setup/config contradictions, one guardrail/test contradiction, workload over capacity, three security-design flaws (audit bypass design, lockout DoS, demo credentials), and missing host prerequisites — plus **4 pre-Sprint-2/5 issues**. **Planning remains unapproved** until the Sprint 1 blockers are corrected and D-09 is decided.

---

## 12. Revision 2 — corrections applied

Authorisation: the maintainer's instruction of 2026-11-21, recorded as **A-01** and **D-09** in [DECISIONS.md](DECISIONS.md). Scope: documentation only. No application code, Dockerfiles, workflows or executable infrastructure were created. **Sprint 1 has not started; Sonnet is not authorised.**

Interpretation note: "create only the agents and the two skills for Sprint 1" (R1) was applied to the **plan**. The agent and skill files themselves are created by task S1-T15 after approval, as the specs always stated. Creating them now would be implementation work you did not authorise.

### 12.1 Sprint 1 blockers

| ID | Status | Resolution | Files changed |
|---|---|---|---|
| B-1 | ✅ Resolved | `make setup` = prerequisite check + hooks + random secrets, **no users**; `make up`; `make bootstrap-admin` (interactive, after `make up`); `make setup-ci` adds a random CI admin password. Added `postgres_superuser_password`, which the Postgres image needs and was missing (N-1). | SPRINT_01 (§1, T01, T10, T13, §6), DEPLOYMENT §2–3, DEVSECOPS §5 |
| B-2 | ✅ Resolved | Cursor HMAC removed; strict validation specified (≤ 512 chars, base64url, exact JSON keys, version, UUID, sort-key type → otherwise 400) | SPRINT_01 T03 |
| B-3 | ✅ Resolved | TC-PLAT-09 is now pytest + HTTPX through the edge; `curl` stays denied; workflow edits moved from *deny* to *ask* for all agents (no per-agent exception needed) | TEST_PLAN, AGENT_SPECIFICATION §2 |
| B-4 | ✅ Resolved | R1–R6 applied (see §12.3); estimate ≈ 29.5 h, within 20–30 h | ROADMAP, SPRINT_01, SKILLS_SPECIFICATION §3, AGENT_SPECIFICATION, UI_UX, ACCEPTANCE (AC-PLAT-14), TEST_PLAN (TC-PLAT-02, TC-SEC-25), DEVSECOPS |
| B-5 | ✅ Resolved | Session-variable bypass removed. Immutability = `aegis_app` has only SELECT/INSERT + owner-only UPDATE/DELETE trigger + owner-only TRUNCATE trigger. Purge only through `SECURITY DEFINER aegis_purge_audit_before(cutoff)` with a **hard 90-day floor** that writes a summary row | DATABASE_DESIGN §2.1/§6, SPRINT_01 T04, SECURITY SR-17, ACCEPTANCE AC-PLAT-08, TEST_PLAN TC-SEC-19, SYSTEM_DESIGN §2/§3.7, ARCHITECTURE §6 |
| B-6 | ✅ Resolved (D-09 approved) | No hard lockout. Progressive per-username delay after 5 failures (30 s doubling, cap 900 s), per-IP 20/min, same for unknown usernames, admin notice at 10 failures (audit event shown on the Users page), admin reset endpoint. T-31 added with residual risk | SECURITY SR-05/SR-17, ACCEPTANCE AC-PLAT-01/05/07, THREAT_MODEL (T-31, STRIDE, abuse case 8, residual risk), ADR-0007 amendment, SYSTEM_DESIGN §2, DATABASE_DESIGN users table, API_SPECIFICATION (endpoint, schema, rate table), SPRINT_01 T06/T07/T11/§4, TEST_PLAN TC-PLAT-02/TC-SEC-01, UI_UX, OBSERVABILITY (metric labels, alert rule), ARCHITECTURE §3.2, DECISIONS |
| B-7 | ✅ Resolved | No default credentials anywhere. Demo users (from S3) get random per-user passwords stored only in the git-ignored `demo_users.txt` (mode 600). Seeding refuses outside `local`/`ci`. T-32 and TC-SEC-27 added | SECURITY SR-16 + checklist, THREAT_MODEL T-32, DEPLOYMENT §2–3, QA_STRATEGY §4, ROADMAP S3-T07/S3-T11, TEST_PLAN, PLANNING_REPORT §7 |
| B-8 | ✅ Resolved | DEPLOYMENT §0 prerequisites table (Docker/Compose, make, git, uv — which supplies Python 3.12 — Node 22, pnpm via corepack, pre-commit, gitleaks via Docker hook, Playwright browsers, hardware). `scripts/check-prereqs` is run by `make setup` | DEPLOYMENT §0, SPRINT_01 §1/T01 |

### 12.2 Items from revision 1 also resolved

| ID | Resolution |
|---|---|
| M-2 | Partition DDL through owner functions `aegis_ensure_event_partitions` / `aegis_drop_event_partitions_before` with input guards (DATABASE_DESIGN §5–6, ADR-0003 addendum, SYSTEM_DESIGN §3.7). Done now because it uses the same privilege model as B-5. |
| m-3 | Makefile target list complete; frontend API-type freshness added to the OpenAPI stage |
| m-6 | TC-PLAT-02 deterministic (part of R6) |
| m-8 | E2E role users created via the admin API by the CI admin |
| m-10 | `worker` joins `core` from Sprint 2 (DEPLOYMENT §1, SPRINT_01 T12) |
| m-11 | `docs/runbooks/` removed from Blue Team write paths |

### 12.3 Sprint 1 scope reductions (R1–R6)

| # | Applied as |
|---|---|
| R1 | S1-T15 creates only QA Engineer, Security Reviewer, DevOps, Documentation and the skills `python-backend` and `react-frontend`. Other agents and skills are created just in time (S2: Architect, Threat Hunter; S3: Detection Engineer; S4: Blue Team; skill schedule in SKILLS_SPECIFICATION §3) |
| R2 | Cursor HMAC removed (B-2) |
| R3 | Generic rate limiter moved to S2-T02 (effort M → L); login throttling stays in S1; TC-SEC-25 moved to S2 |
| R4 | Audit-log API and tests stay in S1; the viewer UI moves to S2-T10 |
| R5 | `hypothesis` deferred to S2; `oasdiff` breaking-change check starts in S2 against the `v0.1.0` snapshot (AC-PLAT-14 split S1/S2) |
| R6 | TC-PLAT-02 timing assertion replaced by a deterministic dummy-hash check |
| + | S1-T16 narrowed: documentation is updated inside each task (DoD); T16 only verifies the quick start, records the threat-model delta and files the sprint security review |

**Non-negotiable controls preserved:** argon2id, server-side sessions + CSRF, RBAC matrix and route-permission tests, login throttling, audit immutability, container hardening, every CI security scanner, E2E smoke in CI.

### 12.4 Additional technical review (problems found while correcting)

| ID | Area | Finding | Resolution |
|---|---|---|---|
| N-1 | Secrets / bootstrap | The Postgres image requires a superuser password, which no secret covered | `postgres_superuser_password` added, used only by the init script |
| N-2 | Audit retention | A purge limited only by `retention_policies` could be abused, because the app role can edit that table (e.g. set 0 days) | Hard 90-day floor inside the owner function, independent of app-editable settings |
| N-3 | Audit immutability | Row triggers don't fire on `TRUNCATE` | Statement-level `BEFORE TRUNCATE` trigger + no TRUNCATE grant |
| N-4 | Login throttling | Tracking throttle state only for existing users would reveal which usernames exist | State keyed by `sha256(lower(username))` for every attempted username; identical 429 |
| N-5 | PostgreSQL privileges | Objects created in `public` by other roles could hijack name resolution in `SECURITY DEFINER` functions | `REVOKE CREATE ON SCHEMA public FROM PUBLIC`, schema owned by `aegis_owner`, `SET search_path = public, pg_temp`, schema-qualified names, `format('%I')` for dynamic DDL, `EXECUTE` revoked from PUBLIC |
| N-6 | Observability | Metric label `lockout` and alert `AegisAuthLockoutSpike` no longer matched the design | Renamed to `throttled` / `repeated_failures`, alert `AegisAuthRepeatedFailures` |
| N-7 | Credentials | MCP spec said `make setup` generates the `aegis_mcp_ro` password, although that role exists only if D-07 approves it | Password created only when the role is enabled |
| N-8 | Residual risk | Progressive delay reduces but doesn't eliminate targeted denial: an attacker who retries exactly when each delay expires keeps one username at the 15-min cap | Accepted, documented (THREAT_MODEL §6). Visible to admins and resettable; MFA/per-device trust is post-MVP |
| N-9 | Agent guardrails | Deny `Read(./infrastructure/compose/secrets/**)` means agents can't read the CI admin password | Intended. Tests read it inside `make`/pytest processes, not through the agent Read tool. No change |

### 12.5 Still open (not Sprint 1 blockers)

| ID | Must be resolved before | Note |
|---|---|---|
| M-1 | Sprint 2 | Memory-based backpressure (Redis 256 MB vs batch-sized stream entries) |
| M-3 | Sprint 2 | Event reference convention `(event_time, id)` + index on `events(id)` |
| **M-5 (new)** | Sprint 2 | **Sprint 2 is now over capacity:** ≈ 36.5 h of tasks plus just-in-time agents/skills (≈ 1.5 h) against 20–30 h, because it received the generic rate limiter and audit-log UI from S1 and already carried six parsers, the DSL and the generator. Must be re-scoped when writing `SPRINT_02.md`. Candidates: trim the S2 skill list to what is actually used, move the events export endpoint and aggregate endpoint to S4 (hunting), and keep Fluent Bit as stretch |
| m-7, m-12 | Sprint 2 | Bulk event loader; ingest key distribution to generator/Fluent Bit |
| M-4, M-4b | Sprint 5 | Measurable AI/UI ACs; structured output + tools + fallback spike |
| m-1, m-2, m-5, m-9, m-13 | When the file is next touched | CSP `style-src-attr`; Caddy log header redaction; flaky-rate method; modifier list wording; artefact provenance |

### 12.6 Sprint 1 capacity (re-estimated per task)

| Task | h | Task | h | Task | h | Task | h |
|---|---|---|---|---|---|---|---|
| T01 | 1.5 | T05 | 1 | T09 | 1 | T13 | 1.5 |
| T02 | 2 | T06 | 4.5 | T10 | 1 | T14 | 1.5 |
| T03 | 1.5 | T07 | 2 | T11 | 3 | T15 | 0.5 |
| T04 | 2.5 | T08 | 1 | T12 | 4.5 | T16 | 0.5 |

**Total ≈ 29.5 h** against 20–30 h. Corrections added about 1.5 h (prerequisite check, owner purge function and triggers, throttle notice panel); the reductions removed about 5.5 h. The buffer is thin. The cut line stays: if over 25 h by day 10, move the Users admin UI to S2 (≈ 1.5 h saved; API and tests stay).

### 12.7 Final verification

| Check | Result |
|---|---|
| Automated ID/link check after corrections | ✅ 92 AC, 41 SR, **136** TC (+TC-SEC-27), **32** T (+T-31, T-32), 16 ADR — all references defined; every AC and SR mapped to ≥ 1 TC; 0 broken links |
| Leftover contradictions (grep for `lockout`/`locked_until`/`unlock`, `HMAC`, audit page in S1, `retention_job`/`current_setting`, `curl` in tests, `make setup` asking for a password, S1 skill set, generic limiter in S1, `hypothesis` in S1) | ✅ none. Remaining matches are the new text describing the change |
| Application code / Dockerfiles / workflows / executable infra | ✅ none created (`*.py`, Dockerfile, compose, `.github/workflows/*.yml`: 0) |
| Sprint 1 within capacity | ✅ ≈ 29.5 h ≤ 30 h (thin buffer) |
| Planning approved? | ADRs and Sprint 1 scope **approved** (D-06, D-08, recorded after this revision). Implementation **not authorised** (D-10 open). See [DECISIONS.md](DECISIONS.md) |

### 12.8 Modified and new files in revision 2

New: `docs/DECISIONS.md`.
Modified: `README.md`, `SECURITY.md`, `CLAUDE.md`, `docs/ACCEPTANCE_CRITERIA.md`, `docs/AGENT_SPECIFICATION.md`, `docs/API_SPECIFICATION.md`, `docs/ARCHITECTURE.md`, `docs/DATABASE_DESIGN.md`, `docs/DEPLOYMENT.md`, `docs/DEVSECOPS.md`, `docs/HANDOFF_SONNET.md`, `docs/MCP_SPECIFICATION.md`, `docs/OBSERVABILITY.md`, `docs/PLANNING_REPORT.md`, `docs/PLANNING_AUDIT_REPORT.md`, `docs/QA_STRATEGY.md`, `docs/ROADMAP.md`, `docs/SKILLS_SPECIFICATION.md`, `docs/SYSTEM_DESIGN.md`, `docs/TEST_PLAN.md`, `docs/THREAT_MODEL.md`, `docs/UI_UX_SPECIFICATION.md`, `docs/sprints/SPRINT_01.md`, `docs/adr/0003-postgresql-primary-store-opensearch-optional.md`, `docs/adr/0007-authentication-sessions.md`.
