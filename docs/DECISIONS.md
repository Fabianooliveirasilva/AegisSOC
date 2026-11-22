# AegisSOC — Human Decision Log

Single source of truth for decisions that only the human maintainer can make. A decision is binding only when its status is **Approved**. Implementers must check this file before starting a sprint ([HANDOFF_SONNET.md §0](HANDOFF_SONNET.md)).

Status values: **Approved** · **Open** · **Rejected** · **Superseded**.

## Approved

| ID | Decision | Approved on | Recorded from | Effect |
|---|---|---|---|---|
| D-09 | **Login throttling policy:** no hard lockout. Per-username progressive delay after 5 consecutive failures (30 s, doubling, capped at 15 min), an additional per-IP limit (20 attempts/min), and an admin notice for repeated failures (audit event `auth.login.repeated_failures` at 10 consecutive failures, shown on the Users page) with admin reset. | 2026-11-21 | Maintainer's instruction authorising the documentation-correction phase | SR-05, AC-PLAT-05, T-31, ADR-0007 amendment, SYSTEM_DESIGN §2, SPRINT_01 S1-T06/T07/T11, TC-SEC-01, API `POST /users/{id}/reset-login-throttle` |
| D-06 | **ADRs accepted:** ADR-0001…0016 move from *Proposed* to *Accepted*, including the ADR-0003 addendum (partition owner functions) and the ADR-0007 amendment (D-09). | 2026-11-21 | Maintainer: "Aprovo D-06 e D-08" | Status line of every ADR and `docs/adr/README.md`; future changes follow ADR-0001 (new or superseding ADR) |
| D-08 | **Sprint 1 scope approved** as specified in [SPRINT_01.md](sprints/SPRINT_01.md) (after audit revision 2). This approves the *scope*; it does not by itself start implementation. | 2026-11-21 | Maintainer: "Aprovo D-06 e D-08" | ROADMAP "Current sprint" |
| D-10 | **Sprint 1 implementation authorised.** Conditions: (1) Claude **Sonnet** implements; Claude Opus keeps architecture, technical supervision, planning review and escalation (resolves protocol review U-1). (2) Scope S1-T01…S1-T16 **including the T12a sequencing adjustment** (resolves U-3), following the approved dependencies and ACs. (3) Agents may commit on **local feature branches**; push, merge into `main`, tags and releases are maintainer-only. (4) **D-05 must be completed before S1-T13 can be considered complete.** (5) HC-1…HC-6 mandatory. (6) No mandatory security control, scanner, AC or blocking test may be removed for schedule. (7) QA Engineer and Security Reviewer validate independently; implementers cannot approve their own work. (8) Any architectural change, new dependency, security-control modification or scope deviation needs review and explicit maintainer approval. **Applies to Sprint 1 only; Sprints 2–5 not approved.** | 2026-11-21 | Maintainer's written authorisation "D-10 — Sprint 1 Implementation Authorization" | ROADMAP "Current sprint"; SPRINT_01 status; SPRINT_01_EXECUTION_PROTOCOL status; HANDOFF §0 precondition satisfied for Sprint 1 |
| A-01 | **Documentation-correction phase authorised:** apply audit corrections B-1…B-8 and Sprint 1 reductions R1–R6. Code, Dockerfiles, workflows and executable infrastructure are **not** authorised; Sprint 1 is **not** started; Sonnet is **not** authorised. | 2026-11-21 | Same instruction | Corrections recorded in [PLANNING_AUDIT_REPORT.md §12](PLANNING_AUDIT_REPORT.md#12-revision-2--corrections-applied) |

## Open

| ID | Decision | Options (recommendation first) | Blocking for |
|---|---|---|---|
| D-05 | GitHub repository: create it, choose visibility, enable Actions, branch protection on `main`, Dependabot and private vulnerability reporting. Needed because S1-T13's pipeline runs on GitHub Actions and TC-PLAT-13 / AC-PLAT-16 must show a PR being blocked; SECURITY.md §1 also relies on GitHub private advisories | Private repo now, public at `v0.5.0` / public from day one. **Progress 2026-11-21:** repository `github.com/Fabianooliveirasilva/AegisSOC` created by the maintainer — **public**, empty (verified read-only); `origin` configured locally. **Remaining (maintainer):** confirm public visibility is intended; push the planning-baseline commit; enable Actions, Dependabot alerts/updates, private vulnerability reporting; protect `main` after the first CI run | S1-T13 (CI); not T01–T12 |
| D-07 | MCP servers to enable | GitHub (read-only by default) + Playwright now; Postgres MCP later if useful; authorise Context7 / none | S1-T15 (non-blocking; can defer) |
| D-02 | Redis or Valkey | Redis 7.4 (fine for local use) / Valkey 8 (BSD, drop-in) | S1-T12 (non-blocking) |
| D-03 | Language of UI and docs | English (assumed) / Portuguese / bilingual README | non-blocking |
| D-04 | AI model per task | Keep `claude-opus-5-5` (effort medium) for all tasks / `claude-haiku-5-5` for routine `explain` | Sprint 5 |
| D-01 | Licence | Apache-2.0 / MIT | Before going public |

## How to record a decision

Move the row to **Approved** (or **Rejected**) with the date and where the instruction came from, list the documents it affects, and update those documents in the same change.
