# AegisSOC — Final Planning Readiness

| | |
|---|---|
| Date | 2026-11-21 |
| Basis | Verified against [DECISIONS.md](DECISIONS.md) (source of truth for human decisions), not against earlier report statements |
| Verdict | **Planning baseline approved.** *(Update 2026-11-21: D-10 approved — Sprint 1 implementation authorised for Sonnet; see DECISIONS.md. The rest of this report reflects the state before D-10.)* |

## 1. Actual approval state

| Item | State | Evidence |
|---|---|---|
| Architecture (ADR-0001…0016) | **Approved** — all 16 ADRs *Accepted* | D-06; status line of every ADR; `docs/adr/README.md` |
| Sprint 1 scope | **Approved** | D-08; `SPRINT_01.md` status line; ROADMAP "Current sprint" |
| Start of Sprint 1 implementation | **Not authorised** | D-10 *Open* |
| Sprints 2–5 | Task-level plan only; **not approved** | ROADMAP; Sprint 2 needs re-planning (M-5) |

The contradiction you found (header said D-06/D-08 approved, §12.7 said "awaiting") came from audit revision 2 having been written *before* your approval message. It has been corrected in PLANNING_AUDIT_REPORT (verdict, §9, §12.7), SPRINT_01, HANDOFF_SONNET, ROADMAP, DECISIONS, PLANNING_REPORT, README and the status lines of ARCHITECTURE, SYSTEM_DESIGN, DATABASE_DESIGN and API_SPECIFICATION.

## 2. Decisions

| ID | State | Meaning |
|---|---|---|
| D-05 | **Open — not approved** | Create the GitHub repository and choose its visibility (recommended: private now, public at `v0.5.0`); enable Actions, branch protection on `main`, Dependabot and private vulnerability reporting. **Why before S1-T13:** the CI pipeline runs on GitHub Actions, and AC-PLAT-16 / TC-PLAT-13 require showing a PR being blocked by the gates; SECURITY.md §1 relies on GitHub private advisories. **Human action needed:** create the repo, add it as `origin` and push the first commit (agents are denied `git push`), then enable the settings above. Does not block S1-T01…T12. |
| D-06 | **Approved** 2026-11-21 | ADRs accepted |
| D-08 | **Approved** 2026-11-21 | Sprint 1 scope approved (scope only, not the start) |
| D-09 | **Approved** 2026-11-21 | Progressive per-username login delay (5 failures → 30 s doubling, cap 15 min), per-IP limit, admin notice and reset; no hard lockout |
| D-10 | **Open** | Go-ahead to start Sprint 1 implementation. Added by the planning model so the start is an explicit decision; nobody has taken it |

## 3. Sprint 1 blockers

| ID | State |
|---|---|
| B-1 setup/bootstrap order | ✅ Resolved |
| B-2 cursor HMAC secret | ✅ Resolved (HMAC removed, strict validation) |
| B-3 guardrails vs tests | ✅ Resolved |
| B-4 capacity | ✅ Resolved (≈ 29.5 h) |
| B-5 audit immutability design | ✅ Resolved |
| B-6 lockout DoS | ✅ Resolved (D-09) |
| B-7 demo credentials | ✅ Resolved |
| B-8 host prerequisites | ✅ Resolved |

Details: [PLANNING_AUDIT_REPORT.md §12.1](PLANNING_AUDIT_REPORT.md#121-sprint-1-blockers).

## 4. Sprint 1 capacity and scope

- **Estimate ≈ 29.5 h** against 20–30 h; thin buffer. Cut line: if over 25 h by day 10, the Users admin UI moves to S2 (API and tests stay).
- **Scope:** 16 tasks (S1-T01…T16), 18 ACs (AC-PLAT-01…16, AC-QA-05, AC-QA-07). The generic rate limiter, audit-log UI, `hypothesis` and `oasdiff` are deferred to S2.
- **Agents/skills created in S1:** QA Engineer, Security Reviewer, DevOps, Documentation; skills `python-backend`, `react-frontend`. Every S1 task is assigned to one of these or to the orchestrator (checked).
- **Dependencies:** roadmap table and SPRINT_01 graph agree (a missing T04 → T08 edge was added); the recommended order covers all 16 tasks with no dependency violations (checked).
- **Non-negotiable controls present in SPRINT_01:** argon2id, `__Host-` session cookie + CSRF, RBAC matrix test (TC-SEC-05), route-permission test (TC-SEC-24), login throttling, audit immutability (triggers + owner purge function), container hardening, blocking scanners (Bandit, Semgrep, Gitleaks, pip-audit, pnpm audit, Trivy fs/image/config — Trivy made explicit in S1-T13 during this check), E2E `@smoke` in CI.

## 5. Before Sprint 2

| ID | Item |
|---|---|
| **M-5** | **Sprint 2 must be re-planned before it starts.** As listed it is ≈ 38 h against 20–30 h, partly because of tasks moved from Sprint 1 (generic rate limiter, audit-log UI). Not fitted into capacity now; to be resolved in `SPRINT_02.md` and approved by the maintainer |
| M-1 | Memory-based backpressure (Redis 256 MB vs batch-sized stream entries) |
| M-3 | Event reference convention `(event_time, id)` + index on `events(id)` |
| m-7, m-12 | Bulk event loader for perf tests; ingest-key distribution to generator / Fluent Bit |

## 6. Before Sprint 5

| ID | Item |
|---|---|
| M-4 | Make AI and UI acceptance criteria objectively measurable |
| M-4b | Spike: structured output combined with tool use, and server-side fallback, against current Claude API docs |
| D-04 | Model per AI task |

## 7. Integrity checks (re-run)

| Check | Result |
|---|---|
| AC / SR / TC / T / ADR references | ✅ 92 / 41 / 136 / 32 / 16 — all defined; every AC and SR mapped to ≥ 1 TC |
| Internal links | ✅ 0 broken |
| Approval-state contradictions | ✅ none remaining ("awaiting approval", "Awaiting D-06/D-08", stale status lines) |
| Agent and skill permissions | ✅ consistent across SPRINT_01, ROADMAP, AGENT_SPECIFICATION, SKILLS_SPECIFICATION; workflow edits = *ask*, `curl`/`git push` denied |

## 8. Confirmations

- **No application code exists.** There are no `.py`, `.ts`, `.js`, shell scripts, Dockerfiles, compose files, Makefile or workflow files. `.github/workflows/` holds only `.gitkeep`; `.claude/` and `.mcp.json` do not exist.
- **Sonnet is not authorised.** D-10 is open, and HANDOFF_SONNET §0 now requires both D-08 and D-10 to be *Approved* before any implementation.
- The git repository has no commits yet.

**Waiting for the maintainer.** Next human actions: approve D-10 when ready; D-05 before S1-T13.
