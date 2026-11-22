# AegisSOC — Test Plan

| | |
|---|---|
| Scope | MVP (Sprints 1–5) |
| Strategy | [QA_STRATEGY.md](QA_STRATEGY.md) |
| Requirements | `AC-*` in [ACCEPTANCE_CRITERIA.md](ACCEPTANCE_CRITERIA.md), `SR-*` in [SECURITY.md](../SECURITY.md) |

Level codes: **U** unit · **I** integration · **A** API · **E** E2E · **S** security · **P** performance · **M** manual/review.

---

## 1. Platform (Sprint 1)

| TC | Title | Level | Verifies | Procedure / expected |
|---|---|---|---|---|
| TC-PLAT-01 | Login success sets hardened cookie | A | AC-PLAT-01, SR-03 | POST valid creds → 200, cookie attributes exact, CSRF token in body |
| TC-PLAT-02 | Login failures indistinguishable | A/U | AC-PLAT-01, SR-05 | unknown user / wrong password → identical 401 status + body; throttled unknown vs throttled existing user → identical 429; unit test asserts the unknown-user path performs a dummy argon2 verify. Timing is measured and reported, not asserted (flaky on CI) |
| TC-PLAT-03 | Logout revokes session | A | AC-PLAT-02 | logout → old cookie on /auth/me → 401; Redis key absent |
| TC-PLAT-04 | Idle/absolute expiry and rotation | I | AC-PLAT-03, SR-02 | frozen clock +31 min → 401; +8 h → 401; session ID differs across logins |
| TC-PLAT-05 | User administration | A | AC-PLAT-07 | CRUD; role change revokes target sessions; self-demotion → 409 |
| TC-PLAT-06 | Audit entries for S1 actions | I | AC-PLAT-08, SR-17 | each action → exactly one row with required fields |
| TC-PLAT-07 | Health and readiness | I | AC-PLAT-09 | stop Postgres → /ready 503 ≤ 2 s; restart → 200 ≤ 5 s; no hostnames in body |
| TC-PLAT-08 | Problem details everywhere | A | AC-PLAT-10 | sample of 4xx/5xx → problem+json with request_id; forced 500 has no traceback |
| TC-PLAT-09 | Edge headers and TLS redirect | E | AC-PLAT-11, SR-19, SR-20 | pytest + HTTPX through the edge (`https://localhost:8443`, Caddy root CA passed as `verify=`): all SR-20 headers and HSTS present; `http://localhost:8080` → 308 to https. No curl (denied by agent guardrails) |
| TC-PLAT-10 | Bootstrap admin CLI | I | AC-PLAT-12 | stdin/file input, weak password rejected, second run refused |
| TC-PLAT-11 | OpenAPI snapshot fresh | U | AC-PLAT-14 | regenerate → no diff |
| TC-PLAT-12 | Stack up and memory budget | M/P | AC-PLAT-15 | `make up` timed; `docker stats` sum ≤ 2.5 GB idle |
| TC-PLAT-13 | CI blocks on planted findings | M | AC-PLAT-16, SR-26 | canary PR with a Bandit-flagged call and a fake secret → pipeline red; reverted |
| TC-E2E-01 | Login/logout journey | E | AC-PLAT-13 | UI login, shell visible, logout, back to login; keyboard-only path |
| TC-E2E-02 | Role-filtered navigation | E | AC-PLAT-13, AC-PLAT-06 | viewer sees no admin items; direct URL → 403 page |

## 2. Security (cross-cutting; introduced in the sprint where the surface appears)

| TC | Title | Level | Verifies | Sprint |
|---|---|---|---|---|
| TC-SEC-01 | Login throttling (D-09): per-IP limit; progressive per-username delay 30 s → 900 s cap with injected clock; no password check and no extension during delay; identical for unknown users; no hard lockout; repeated-failure notice; admin reset | A | SR-05, AC-PLAT-05 | S1 |
| TC-SEC-02 | Password policy and argon2id parameters | U | SR-01 | S1 |
| TC-SEC-03 | Session fixation: pre-login cookie not honoured, ID rotates | A | SR-02 | S1 |
| TC-SEC-04 | Cookie flags and HSTS through edge | E | SR-03, SR-19 | S1 |
| TC-SEC-05 | Exhaustive RBAC matrix (role × route) | A | SR-06, AC-PLAT-06 | S1+ |
| TC-SEC-06 | Object-level rules (notes author, AI analyses, self-demotion, reopen) | A | SR-07 | S1+ |
| TC-SEC-07 | Injection payload corpus against DSL, filters, sort keys | A | SR-09, SR-11 | S2 |
| TC-SEC-08 | CSRF missing/wrong/correct | A | SR-04, AC-PLAT-04 | S1 |
| TC-SEC-09 | XSS corpus stored via events, notes, rule titles, filenames → rendered inert | E | SR-10 | S2+ |
| TC-SEC-10 | API key misuse: revoked, expired, wrong source, used on non-ingest route, cookie on ingest | A | SR-08 | S2 |
| TC-SEC-11 | Log poisoning: spoofed `aegis.*`, `event.ingested`, source | I | SR-34 | S2 |
| TC-SEC-12 | Unsafe deserialisation: Semgrep/Bandit rules present and passing; no pickle/yaml.load | S | SR-13 | S1 |
| TC-SEC-13 | ReDoS patterns compile via RE2 or are rejected; evaluation stays < budget | U | SR-12 | S3 |
| TC-SEC-14 | Detection tampering: self-approval, activation without regression, disable without reason | A | SR-07, SR-17 | S3 |
| TC-SEC-15 | Export permission, row cap, audit | A | SR-06, SR-35 | S2 |
| TC-SEC-16 | Malicious uploads: HTML/SVG, polyglot, oversized, traversal filename | A | SR-14, SR-22 | S4 |
| TC-SEC-17 | AI tools cannot read beyond requester scope or write | I | SR-30 | S5 |
| TC-SEC-18 | Port exposure: only edge on 127.0.0.1; Postgres/Redis unreachable from host | M | SR-24 | S1 |
| TC-SEC-19 | Audit log immutability: UPDATE/DELETE/TRUNCATE as `aegis_app` fail; triggers block non-owners; `aegis_purge_audit_before` refuses cutoffs inside the 90-day floor and logs a summary row | I | SR-17 | S1 |
| TC-SEC-20 | Error and readiness information disclosure | A | SR-18 | S1 |
| TC-SEC-21 | `X-Forwarded-For` from non-edge peer ignored | I | SR-41 | S1 |
| TC-SEC-22 | Body size limits at edge and app | A/E | SR-22 | S1 (generic), S2 (ingest), S4 (uploads) |
| TC-SEC-23 | Log hygiene: run suite with log capture, grep for passwords/session IDs/keys | I | SR-18, SR-16 | S1+ |
| TC-SEC-24 | Every route declares a permission | U | SR-06 | S1 |
| TC-SEC-25 | Rate-limit headers and 429 per route group | A | SR-21 | S2 (generic limiter moved from S1; login throttling is TC-SEC-01) |
| TC-SEC-26 | Outbound connections only to allowlist; no response-action code paths | I/M | SR-15, SR-38 | S5 |
| TC-SEC-27 | Demo seeding: random per-user passwords, secrets file mode 600, nothing printed or logged, refuses when `AEGIS_ENV` ∉ {local, ci}; no default credentials anywhere (grep of repo and images) | I | SR-16 | S3 |

## 3. Infrastructure

| TC | Title | Level | Verifies | Sprint |
|---|---|---|---|---|
| TC-INF-01 | Compose hardening lint (user, read_only, cap_drop, no-new-privileges, limits, healthchecks) via `scripts/check-compose` | U | SR-23 | S1 |
| TC-INF-02 | Data stores require auth and are on internal network | M | SR-24, SR-27 | S1 |
| TC-INF-03 | Supply chain: actions pinned by SHA, lockfiles present, Trivy image scan, SBOM produced | S | SR-25, SR-26, SR-40 | S1 |
| TC-INF-04 | Gitleaks on full history and images | S | SR-16 | S1 |
| TC-INF-05 | Agent/MCP permission configuration review against spec | M | SR-39 | S1, S5 |
| TC-INF-06 | Backup and restore drill | M | SR-37, SR-27 | S5 |
| TC-INF-07 | Retention job deletes only expired data | I | SR-36 | S2 |

## 4. Module tests

### SIEM (Sprint 2)
| TC | Title | Level | Verifies |
|---|---|---|---|
| TC-SIEM-01 | Source and key lifecycle | A | AC-SIEM-01, SR-08 |
| TC-SIEM-02 | Ingest limits and statuses (202/401/413/422/429) | A | AC-SIEM-02, SR-09 |
| TC-SIEM-03 | Parser golden files + hypothesis property tests | U | AC-SIEM-03, SR-13 |
| TC-SIEM-04 | Normalised field contract | U/I | AC-SIEM-04 |
| TC-SIEM-05 | Source binding and server-set fields | I | AC-SIEM-05, SR-34 |
| TC-SIEM-06 | Redelivery idempotency (kill worker before ACK) | I | AC-SIEM-06 |
| TC-SIEM-07 | Ingest errors, redacted excerpts, DLQ after 5 failures | I | AC-SIEM-07 |
| TC-SIEM-08 | Search DSL operators, pagination, full-text, disallowed fields | A | AC-SIEM-08 |
| TC-SIEM-09 | Backpressure 429 and no-loss accounting | I | AC-SIEM-12, SR-35 |
| TC-SIEM-10 | Entity timeline ordering and overlay | A | AC-SIEM-09 |
| TC-SIEM-11 | Health status transitions incl. `silent` | I | AC-SIEM-10 |
| TC-SIEM-12 | Partition creation and drop | I | AC-SIEM-11, SR-36 |
| TC-SIEM-13 | Generator determinism and safe address ranges | U | AC-SIEM-13 |
| TC-SIEM-14 | Fluent Bit profile end-to-end | E | AC-SIEM-15 |
| TC-E2E-03 | Events explorer journey | E | AC-SIEM-14 |

### Detection (Sprints 3–4)
| TC | Title | Level | Verifies |
|---|---|---|---|
| TC-DET-01 | Version creation, hash dedup, history | A | AC-DET-01 |
| TC-DET-02 | Static validation findings per check | U | AC-DET-02 |
| TC-DET-03 | Evaluator conformance suite (≥ 60 cases) | U | AC-DET-03, SR-12 |
| TC-DET-04 | Streaming detection latency at 500 EPS | P | AC-DET-04 |
| TC-DET-05 | ATT&CK import and coverage | I | AC-DET-05 |
| TC-DET-06 | Level → severity mapping | U | AC-DET-06 |
| TC-DET-07 | Lifecycle transitions, four-eyes, regression precondition | A | AC-DET-07 |
| TC-DET-08 | `detections sync/validate/test` CLI exit codes | I | AC-DET-08 |
| TC-DET-09 | Correlation types | I | AC-DET-09 |
| TC-DET-10 | Rule metrics computation | I | AC-DET-10 |
| TC-DET-11 | Alert dedup window | I | AC-DET-13 |
| TC-DET-12 | D01–D12 positive/negative scenarios (unit + pipeline) | U/E | AC-DET-12 |
| TC-E2E-04 | Rule author → validate → test → approve (2nd user) → activate | E | AC-DET-11, AC-DET-07 |
| TC-E2E-05 | Generator storyline → alert visible → triage | E | AC-DET-04, AC-INC-01 |

### Incidents (Sprints 3–4)
| TC | Title | Level | Verifies |
|---|---|---|---|
| TC-INC-01 | Alert queue filters and `If-Match` | A | AC-INC-01 |
| TC-INC-02 | Disposition → rule metrics | I | AC-INC-02 |
| TC-INC-03 | Bulk triage limits and audit | A | AC-INC-03 |
| TC-INC-04 | Create incident from alerts | A | AC-INC-04 |
| TC-INC-05 | State machine table-driven (all from×to pairs) | U/A | AC-INC-05 |
| TC-INC-06 | Assignment and "my incidents" | A | AC-INC-06 |
| TC-INC-07 | Notes revisions and author rule | A | AC-INC-07 |
| TC-INC-08 | Evidence upload/download/hash | A | AC-INC-08, SR-14 |
| TC-INC-09 | Timeline merge and AI marking | I | AC-INC-09 |
| TC-INC-10 | Playbook load and checklist | I | AC-INC-10 |
| TC-INC-11 | TTT/TTC and MTTR | I | AC-INC-11 |
| TC-INC-12 | Incident Markdown report | A | AC-INC-13 |
| TC-E2E-06 | Alert → incident → playbook → evidence → close | E | AC-INC-12 |
| TC-E2E-07 | XSS payloads in event/notes displayed as text | E | SR-10 |

### Hunting and intel (Sprint 4)
| TC | Title | Level | Verifies |
|---|---|---|---|
| TC-HUNT-01 | Hunt DSL execution, aggregation and limits | A | AC-HUNT-01, SR-35 |
| TC-HUNT-02 | DSL allowlist and injection corpus | A | SR-11 |
| TC-HUNT-03 | Saved hunts and runs persistence | A | AC-HUNT-02 |
| TC-HUNT-04 | Retro-hunt async, no alerts | I | AC-HUNT-03 |
| TC-HUNT-05 | IOC import validation (CSV/STIX, over-broad, limits) | A | AC-HUNT-04 |
| TC-HUNT-06 | Live IOC matching and expiry | I | AC-HUNT-05 |
| TC-HUNT-07 | Related activity ranking | A | AC-HUNT-06 |
| TC-HUNT-08 | MISP connector (post-MVP) | I | AC-HUNT-08 |
| TC-HUNT-09 | Hunt report and attach as evidence | A | AC-HUNT-07 |
| TC-E2E-08 | Hunting journey | E | AC-HUNT-01, AC-HUNT-02 |

### AI analyst (Sprint 5) — fixture provider unless stated
| TC | Title | Level | Verifies |
|---|---|---|---|
| TC-AI-01 | Disabled mode, no egress | I | AC-AI-01 |
| TC-AI-02 | Explain event/alert | I | AC-AI-02 |
| TC-AI-03 | Summarise incident | I | AC-AI-03 |
| TC-AI-04 | Next steps | I | AC-AI-04 |
| TC-AI-05 | Explain rule | I | AC-AI-05 |
| TC-AI-06 | Report draft | I | AC-AI-06 |
| TC-AI-07 | ATT&CK suggestions exist locally | I | AC-AI-07 |
| TC-AI-08 | Evidence gaps vs playbook | I | AC-AI-08 |
| TC-AI-09 | Schema validation → rejected | U | AC-AI-09 |
| TC-AI-10 | Citation enforcement and >50 % rejection | U | AC-AI-10, SR-32 |
| TC-AI-11 | Prompt-injection corpus (fixture: always; live: manual evaluation run) | S | AC-AI-11, SR-29 |
| TC-AI-12 | Redaction corpus and context manifest | U | AC-AI-12, SR-28 |
| TC-AI-13 | Apply/dismiss with RBAC and audit | A | AC-AI-13, SR-31 |
| TC-AI-14 | Quota, budget, refusal, timeout handling | I | AC-AI-14, SR-33 |
| TC-AI-15 | Live provider smoke (optional, needs key, not in CI) | M | AC-AI-02 |
| TC-E2E-09 | AI panel: request, view citations, apply proposed action | E | AC-AI-15, AC-AI-13 |

### QA module and observability
| TC | Title | Level | Verifies |
|---|---|---|---|
| TC-QA-01 | Runner unit and pipeline modes, diff output | U/I | AC-QA-01 |
| TC-QA-02 | Validation run API and persistence | A | AC-QA-02 |
| TC-QA-03 | Regression gate in CI and activation precondition | M/A | AC-QA-03 |
| TC-QA-04 | Quality indicators endpoint and simulated flags | A | AC-QA-04 |
| TC-QA-05 | QA report generation | I | AC-QA-05 |
| TC-QA-06 | Ground-truth evaluation recall ≥ 0.9 | P | AC-QA-06 |
| TC-QA-07 | Coverage thresholds enforced | M | AC-QA-07 |
| TC-QA-08 | Traceability script output | U | AC-QA-08 |
| TC-E2E-10 | Detection validation screen | E | AC-QA-02 |
| TC-E2E-11 | Accessibility (axe: 0 serious/critical) on all main screens | E | UI_UX §8 |
| TC-E2E-12 | Overview dashboard with synthetic badges | E | AC-OBS-04 |
| TC-OBS-01 | `/metrics` exposed internally, not via edge | I | AC-OBS-01 |
| TC-OBS-02 | Grafana dashboards provisioned | M | AC-OBS-02 |
| TC-OBS-03 | `promtool test rules` | U | AC-OBS-03 |

### Performance
| TC | Title | Verifies | Target |
|---|---|---|---|
| TC-PERF-01 | Ingest: 500 EPS for 10 min + 2,000 EPS burst for 60 s | AC-SIEM-02, AC-SIEM-12, SR-35 | 0 lost; p95 accept ≤ 100 ms; backlog drains ≤ 2 min after burst |
| TC-PERF-02 | API mixed read load, 20 VUs, 5 min | SR-21 | p95 ≤ 300 ms, error rate < 0.5 % |
| TC-PERF-03 | Search on 1 M events | AC-SIEM-08 | p95 first page ≤ 1 s |
| TC-PERF-04 | Detection latency at 500 EPS, 12 rules | AC-DET-04 | p95 ≤ 5 s |

Hardware for performance numbers is recorded with each result; numbers are indicative for a laptop, not capacity guarantees.

## 5. Detection scenario catalogue (MVP)

Each rule D01–D12 (SYSTEM_DESIGN §4.9) has at minimum:

| Rule | Positive scenarios | Negative scenarios |
|---|---|---|
| D01 SSH brute force | 12 failures from one IP in 2 min | 4 failures (below threshold); 12 failures spread over 1 h |
| D02 Success after brute force | D01 pattern then success same IP+user within 10 min | success without prior failures; success from different IP |
| D03 Encoded PowerShell | `-enc`, `-EncodedCommand`, `-e` variants | plain `powershell -File script.ps1`; `-ExecutionPolicy` only |
| D04 Local admin created | 4720 then 4732 (Administrators) same account ≤ 5 min | 4720 alone; 4732 to non-admin group |
| D05 Scheduled task | `schtasks /create` by non-SYSTEM | `schtasks /query` |
| D06 LSASS access | EID 10 TargetImage lsass with suspicious GrantedAccess from non-allowlisted image | access by allowlisted AV image |
| D07 Log cleared | 1102 | 1100 (service shutdown) |
| D08 Web shell request | POST to `/uploads/*.php` with 200 | GET static image in uploads |
| D09 Path traversal | ≥ 5 requests with `../` encodings from one IP in 1 min | single request; legitimate `..` in query value only once |
| D10 Console login without MFA | ConsoleLogin success, MFAUsed=No | MFAUsed=Yes |
| D11 Logging disabled | StopLogging / DeleteTrail | DescribeTrails |
| D12 Sudo to root by unusual user | sudo by user not in allowlist | sudo by allowlisted admin |

Every scenario also exists as a generator storyline for pipeline mode and ground-truth evaluation.

## 6. Traceability matrix

Generated by `make traceability` from test markers (AC-QA-08); this static version is the planned baseline.

### Requirements → tests

| Requirement | Test cases |
|---|---|
| AC-PLAT-01 | TC-PLAT-01, TC-PLAT-02 |
| AC-PLAT-02 | TC-PLAT-03 |
| AC-PLAT-03 | TC-PLAT-04 |
| AC-PLAT-04 | TC-SEC-08 |
| AC-PLAT-05 | TC-SEC-01 |
| AC-PLAT-06 | TC-SEC-05, TC-SEC-24, TC-E2E-02 |
| AC-PLAT-07 | TC-PLAT-05 |
| AC-PLAT-08 | TC-PLAT-06, TC-SEC-19 |
| AC-PLAT-09 | TC-PLAT-07 |
| AC-PLAT-10 | TC-PLAT-08 |
| AC-PLAT-11 | TC-PLAT-09 |
| AC-PLAT-12 | TC-PLAT-10 |
| AC-PLAT-13 | TC-E2E-01, TC-E2E-02 |
| AC-PLAT-14 | TC-PLAT-11 |
| AC-PLAT-15 | TC-PLAT-12 |
| AC-PLAT-16 | TC-PLAT-13 |
| AC-SIEM-01 … 15 | TC-SIEM-01 … 14, TC-E2E-03 (see §4 SIEM table) |
| AC-DET-01 … 13 | TC-DET-01 … 12, TC-E2E-04, TC-E2E-05 |
| AC-INC-01 … 13 | TC-INC-01 … 12, TC-E2E-05, TC-E2E-06 |
| AC-HUNT-01 … 08 | TC-HUNT-01 … 09, TC-E2E-08 |
| AC-AI-01 … 15 | TC-AI-01 … 15, TC-E2E-09 |
| AC-QA-01 … 08 | TC-QA-01 … 08, TC-E2E-10 |
| AC-OBS-01 … 04 | TC-OBS-01 … 03, TC-E2E-12 |

### Security requirements → tests

| SR | Tests | SR | Tests |
|---|---|---|---|
| SR-01 | TC-SEC-02 | SR-22 | TC-SEC-22 |
| SR-02 | TC-SEC-03, TC-PLAT-04 | SR-23 | TC-INF-01 |
| SR-03 | TC-SEC-04, TC-PLAT-01 | SR-24 | TC-SEC-18, TC-INF-02 |
| SR-04 | TC-SEC-08 | SR-25 | TC-INF-03 |
| SR-05 | TC-SEC-01, TC-PLAT-02 | SR-26 | TC-PLAT-13 |
| SR-06 | TC-SEC-05, TC-SEC-24 | SR-27 | TC-INF-02, TC-INF-06 |
| SR-07 | TC-SEC-06, TC-SEC-14 | SR-28 | TC-AI-12 |
| SR-08 | TC-SEC-10, TC-SIEM-01 | SR-29 | TC-AI-11 |
| SR-09 | TC-SEC-07, TC-SIEM-02 | SR-30 | TC-SEC-17 |
| SR-10 | TC-SEC-09, TC-E2E-07 | SR-31 | TC-AI-13 |
| SR-11 | TC-SEC-07, TC-HUNT-02 | SR-32 | TC-AI-10 |
| SR-12 | TC-SEC-13, TC-DET-03 | SR-33 | TC-AI-14 |
| SR-13 | TC-SEC-12, TC-SIEM-03 | SR-34 | TC-SIEM-05, TC-SEC-11 |
| SR-14 | TC-SEC-16, TC-INC-08 | SR-35 | TC-PERF-01, TC-HUNT-01, TC-SEC-15, TC-SIEM-09 |
| SR-15 | TC-SEC-26 | SR-36 | TC-SIEM-12, TC-INF-07 |
| SR-16 | TC-INF-04, TC-SEC-23, TC-SEC-27 | SR-37 | TC-INF-06 |
| SR-17 | TC-PLAT-06, TC-SEC-19 | SR-38 | TC-SEC-26 |
| SR-18 | TC-SEC-20, TC-SEC-23 | SR-39 | TC-INF-05 |
| SR-19 | TC-PLAT-09, TC-SEC-04 | SR-40 | TC-INF-03 |
| SR-20 | TC-PLAT-09 | SR-41 | TC-SEC-21 |
| SR-21 | TC-SEC-25, TC-PERF-02 | | |

## 7. Entry and exit criteria per sprint

**Entry:** sprint scope approved; ACs for the sprint have mapped TCs; environments available.
**Exit:** all TCs mapped to the sprint's ACs executed and passing; no open S1/S2; coverage gates met; QA report filed; security review note filed.
