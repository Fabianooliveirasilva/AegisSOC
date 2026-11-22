# Security Policy and Security Architecture

## 1. Reporting a vulnerability

AegisSOC is a portfolio / demonstration project that runs locally with synthetic data. If you find a vulnerability:

1. **Do not open a public issue.** Use GitHub's *Report a vulnerability* (private security advisory) on this repository.
2. Include affected version/commit, reproduction steps against a local deployment, and impact.
3. Expect acknowledgement within 7 days. Fixes are released as patch versions and credited in the changelog unless you prefer otherwise.

Supported versions: the latest `0.x` minor release only.

**Out of scope:** findings that require real production data, attacks against third-party services (Anthropic, GitHub, MISP), social engineering, volumetric DoS.

---

## 2. Security principles

1. **Defensive only** — AegisSOC observes, detects and helps humans respond. It never takes actions against external systems (SR-38).
2. **Deny by default** — every endpoint declares a permission; anything undeclared fails a test (SR-06).
3. **Untrusted input everywhere** — log content is attacker-controlled by definition: it is validated, size-limited, never executed, never rendered as HTML, never interpreted as instructions by the AI (SR-09, SR-10, SR-29, SR-34).
4. **Least privilege** — for users (RBAC), services (DB roles, network segments), the AI (read-only, requester-scoped tools) and development agents/MCP servers (SR-30, SR-39).
5. **Evidence over claims** — every control below has a verifying test case in [docs/TEST_PLAN.md](docs/TEST_PLAN.md).

The threats that motivate these requirements are catalogued in [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md).

---

## 3. Identity and access

### 3.1 Roles

| Role | Intended user |
|---|---|
| `admin` | Platform administrator: users, sources, keys, settings, audit |
| `detection_engineer` | Writes, tests, approves and activates detection content |
| `analyst` | Triages alerts, works incidents, hunts, uses the AI analyst |
| `viewer` | Read-only stakeholder (e.g. demo audience) |

### 3.2 RBAC permission matrix

| Permission | admin | detection_engineer | analyst | viewer |
|---|:-:|:-:|:-:|:-:|
| `users:manage` | ✔ | | | |
| `audit:read` | ✔ | | | |
| `admin:settings` | ✔ | | | |
| `sources:manage` | ✔ | | | |
| `sources:read` | ✔ | ✔ | ✔ | ✔ |
| `events:read` | ✔ | ✔ | ✔ | ✔ |
| `events:export` | ✔ | ✔ | ✔ | |
| `rules:read` | ✔ | ✔ | ✔ | ✔ |
| `rules:write` | ✔ | ✔ | | |
| `rules:approve` | ✔ | ✔ | | |
| `alerts:read` | ✔ | ✔ | ✔ | ✔ |
| `alerts:triage` | ✔ | ✔ | ✔ | |
| `incidents:read` | ✔ | ✔ | ✔ | ✔ |
| `incidents:write` | ✔ | | ✔ | |
| `hunts:read` | ✔ | ✔ | ✔ | ✔ |
| `hunts:write` | ✔ | ✔ | ✔ | |
| `intel:read` | ✔ | ✔ | ✔ | ✔ |
| `intel:write` | ✔ | ✔ | ✔ | |
| `ai:use` | ✔ | ✔ | ✔ | |
| `ai:read_all` | ✔ | | | |
| `qa:read` | ✔ | ✔ | ✔ | ✔ |
| `qa:run` | ✔ | ✔ | | |

Additional object-level rules (SR-07): rule approval requires approver ≠ author; notes editable only by their author; AI analyses visible only to the requester unless `ai:read_all`; an admin cannot demote or disable their own account; incident reopen requires `admin` or the assignee.

---

## 4. Security requirements (SR)

Each requirement is verified by at least one test case (`TC-SEC-*` or module TCs) — see the traceability matrix in [docs/TEST_PLAN.md §6](docs/TEST_PLAN.md#6-traceability-matrix).

### Authentication and sessions
- **SR-01** Passwords hashed with argon2id (m=64 MiB, t=3, p=4); minimum 12 characters; rejected if in the bundled 10k common-password list; never logged or returned.
- **SR-02** Server-side sessions: 256-bit random IDs, stored hashed in Redis; rotated on login and privilege change; idle timeout 30 min, absolute 8 h; all sessions revoked on password change, role change or deactivation.
- **SR-03** Session cookie `__Host-aegis_session` with `Secure`, `HttpOnly`, `SameSite=Strict`, `Path=/`, no `Domain`.
- **SR-04** CSRF synchroniser token required in `X-CSRF-Token` for all unsafe methods on cookie-authenticated requests; compared in constant time.
- **SR-05** Login throttling (decision D-09): per-IP limit of 20 attempts/min; per-username progressive delay after 5 consecutive failures (30 s, doubling, capped at 15 min), applied identically to unknown usernames; **no hard lockout**, so an attacker cannot lock users out (T-31); admin notice at 10 consecutive failures and admin reset; identical 401 for unknown user / bad password and identical 429 while throttled; the unknown-user path performs a dummy hash verification.

### Authorisation
- **SR-06** Deny by default: every route declares exactly one permission; an automated test enumerates routes and fails on undeclared ones; the RBAC matrix (§3.2) is tested exhaustively.
- **SR-07** Object-level authorisation rules (§3.2) enforced in services, not only in the UI.
- **SR-08** Ingestion API keys: ≥ 256-bit secret, stored as SHA-256 hash, shown once, bound to one log source, revocable, optional expiry, `last_used_at` tracked; keys only valid on `/ingest/*`.

### Input, output and injection
- **SR-09** All request bodies validated with strict Pydantic models (`extra="forbid"`), explicit max lengths and collection sizes.
- **SR-10** Output encoding: the SPA renders all data as text (no `dangerouslySetInnerHTML`, no Markdown-to-HTML in MVP); CSV exports neutralise cells starting with `= + - @ \t \r`.
- **SR-11** SQL only via SQLAlchemy with bound parameters; the hunting/search DSL maps to an allowlist of fields; no user-supplied SQL, column names or sort keys outside allowlists.
- **SR-12** User-supplied regular expressions (Sigma `re`, DSL `regex`) compiled with RE2 (linear time); compile failures rejected.
- **SR-13** Safe deserialisation: YAML via safe loaders only; queue payloads JSON only; no `pickle`, `marshal` or `yaml.load` with unsafe loaders anywhere (Bandit/Semgrep rule enforced).
- **SR-14** File uploads: ≤ 10 MiB, content-type allowlist verified by signature, stored outside any served path under SHA-256 names, served only as `attachment` with `nosniff`, never parsed or executed server-side.
- **SR-15** SSRF: no user-supplied URL is fetched in the MVP; outbound connections limited to `api.anthropic.com` (AI enabled) and the configured MISP host (post-MVP), enforced in code (allowlist) and network (egress only for worker).

### Secrets, logging, audit
- **SR-16** Secrets supplied via files (`*_FILE` env vars / Docker secrets) or `.env` (git-ignored); never committed (Gitleaks in pre-commit and CI); masked in settings views and logs. **No default or fixed credentials exist:** database/Redis secrets and the CI admin password are generated randomly by `make setup` / `make setup-ci`; the first admin's password is entered interactively (`make bootstrap-admin`); demo users get random per-user passwords written only to `infrastructure/compose/secrets/demo_users.txt` (mode 600, never printed or logged), and demo seeding refuses to run unless `AEGIS_ENV` is `local` or `ci` (T-32).
- **SR-17** Audit trail for: login success/failure/throttling, repeated-failure notices, login-throttle resets, logout, password change, user/role changes, key creation/revocation, source changes, rule create/approve/activate/disable, alert disposition, incident create/transition/assignment, evidence upload/download, AI analysis request and action apply/dismiss, retention runs, settings changes. Append-only: the application role has no UPDATE/DELETE/TRUNCATE privilege; owner-only triggers block UPDATE/DELETE/TRUNCATE by anyone else; retention purges run only through the `SECURITY DEFINER` function `aegis_purge_audit_before(cutoff)` with a hard 90-day floor that writes a summary row. Each row records actor, IP and request ID.
- **SR-18** Application logs are structured JSON; never contain passwords, session IDs, CSRF tokens, API key secrets or Anthropic keys; untrusted values are JSON-encoded (no log forging via newlines).

### Transport, headers, limits
- **SR-19** TLS at the edge (Caddy `tls internal` locally); HTTP redirects to HTTPS; HSTS `max-age=31536000`.
- **SR-20** Security headers: `Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `Permissions-Policy` (camera, mic, geolocation off), `Cross-Origin-Opener-Policy: same-origin`, `Cache-Control: no-store` on API responses.
- **SR-21** Rate limits per principal and route group as specified in API_SPECIFICATION §1.6.
- **SR-22** Request body limits: 1 MiB default and on `/ingest/*`, 10 MiB on evidence upload, 5 MiB on IOC import — enforced at edge and app.
- **SR-41** Proxy headers (`X-Forwarded-For`, `X-Forwarded-Proto`) trusted only from the edge container's network address.

### Platform hardening
- **SR-23** Containers: non-root UID, read-only root filesystem with explicit tmpfs, `cap_drop: [ALL]`, `no-new-privileges`, resource limits, healthchecks, minimal base images (`python:3.12-slim` / distroless where possible), base images pinned by digest.
- **SR-24** Network segmentation: only the edge publishes ports, bound to `127.0.0.1`; data stores on an `internal` network; only the worker gets egress, and only when AI is enabled.
- **SR-25** Dependencies pinned with lockfiles (`uv.lock`, `pnpm-lock.yaml`); new runtime dependencies require justification and licence check; Dependabot/Renovate enabled.
- **SR-26** CI security gates (Bandit, Semgrep, Gitleaks, pip-audit, pnpm audit, Trivy fs/image) block merge on High/Critical findings ([docs/DEVSECOPS.md](docs/DEVSECOPS.md)).
- **SR-27** Encryption at rest relies on host full-disk encryption (documented assumption); exported backups encrypted with `age` when leaving the host; Postgres/Redis passwords required even on internal networks.
- **SR-40** Supply chain for CI: third-party GitHub Actions pinned by commit SHA; workflow `permissions:` minimal (`contents: read` by default); no secrets exposed to `pull_request` workflows from forks.

### AI-specific
- **SR-28** Data minimisation: per-task context allowlist of fields; C1 secrets redacted by pattern (passwords in command lines, tokens, keys, `Authorization` headers) before any external call; optional pseudonymisation of usernames/hosts (`AEGIS_AI_PSEUDONYMIZE=true`); the `context_manifest` records what was sent.
- **SR-29** Prompt-injection resistance: untrusted data delimited and JSON-encoded; system prompt forbids following embedded instructions; suspected injection reported as a finding; red-team fixtures in CI.
- **SR-30** AI tools are read-only, executed with the requester's permissions, bounded in rows and calls; no URL fetching, code execution or write tools.
- **SR-31** Human approval for consequential actions: the AI can only create `proposed_actions`; applying requires a human request that passes normal RBAC and is audited with the human as actor.
- **SR-32** No fabricated findings: output schema-validated; every finding needs ≥ 1 citation to an ID present in the analysis context; invalid citations dropped; analyses with > 50 % dropped findings rejected; confidence level and rationale mandatory; UI labels all AI content.
- **SR-33** AI cost and abuse limits: per-user hourly quota, global daily token budget, `max_tokens` cap, timeouts.

### Data, operations, governance
- **SR-34** Log-poisoning controls: source identity comes from the API key, not the payload; `event.ingested` and `aegis.*` fields are server-set; payload fields named `aegis.*` are dropped; event content is treated as untrusted in UI, exports and AI.
- **SR-35** DoS controls: ingest quotas and backpressure (429), query time-range and complexity limits, `statement_timeout`, pagination caps, evaluation time budget per rule.
- **SR-36** Retention and deletion as specified in [docs/SYSTEM_DESIGN.md §3.7](docs/SYSTEM_DESIGN.md#37-retention); `data_origin=production` is not an accepted value.
- **SR-37** Backup and recovery: `scripts/backup` (pg_dump custom format + evidence volume tar), documented restore, restore drill in Sprint 5; demo RPO 24 h, RTO 1 h.
- **SR-38** Defensive-only: no feature performs actions on external systems (no host isolation, firewall changes, account disabling); playbooks are checklists; generator uses documentation IP ranges and `.test`/`example.com` domains.
- **SR-39** Development agents and MCP servers operate under least privilege as defined in [docs/AGENT_SPECIFICATION.md](docs/AGENT_SPECIFICATION.md) and [docs/MCP_SPECIFICATION.md](docs/MCP_SPECIFICATION.md); no agent can merge, release or change secrets.

---

## 5. Security checklist (per release)

- [ ] Threat model reviewed for new components/data flows; new threats have mitigations and tests
- [ ] All `SR-*` requirements touched by the release have passing tests (traceability matrix green)
- [ ] CI security gates green: Bandit, Semgrep, Gitleaks, pip-audit, pnpm audit, Trivy (fs + images) — no unwaived High/Critical
- [ ] Waivers (if any) documented in `docs/security/waivers.md` with expiry and owner
- [ ] RBAC matrix test and route-permission test passing
- [ ] No new endpoint without rate limit, size limit, validation and permission
- [ ] Containers run as non-root with read-only root FS; images pinned by digest; SBOM generated
- [ ] Only edge ports published, bound to 127.0.0.1
- [ ] No secrets in repo, images or logs (Gitleaks + log grep test)
- [ ] No default or fixed credentials anywhere (SR-16, TC-SEC-27); demo passwords only in the git-ignored secrets folder
- [ ] AI: prompt-injection suite, citation-validation suite and redaction suite passing; AI off by default
- [ ] Audit log contains entries for every SR-17 action exercised by E2E tests
- [ ] Backup and restore tested on this release
- [ ] Dependencies reviewed for licence compatibility
- [ ] Security Reviewer Agent report attached to the release PR

## 6. Data protection

Data classes C1–C4 are defined in [docs/diagrams/data-flow.md](docs/diagrams/data-flow.md). This repository and its demo environment must contain only synthetic data (`data_origin` ∈ {`synthetic`, `lab`}).
