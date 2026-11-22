# Sprint 1 Execution Protocol — Consistency Review

| | |
|---|---|
| Date | 2026-11-21 |
| Reviewer | Claude Opus (architect / governance) |
| Subject | [SPRINT_01_EXECUTION_PROTOCOL.md](SPRINT_01_EXECUTION_PROTOCOL.md) revision 1 → revision 2 |
| Scope | Documentation only. No decision, ADR or acceptance criterion changed. D-10 not approved; Sonnet not authorised |

## 1. Summary

| Check | Rev. 1 | Rev. 2 |
|---|---|---|
| Dependencies vs SPRINT_01 | 2 gaps (missing T15 process dependency for 5 tasks; T14 → T08 not in graph) | ✅ resolved, machine-checked |
| PR groups vs dependencies | 2 violations (PR2 had T05 before T04's PR; PR1 mixed T15 with a DevOps task before HC-1) | ✅ re-cut into 12 PRs |
| Integration tests before infrastructure | T04–T10 needed a database that only T12 created | ✅ T12a pulled forward (C-4) |
| T15 validation | Required QA/Security notes from agents that T15 itself creates | ✅ Opus review + HC-1 + guardrail probe |
| Agent permissions | Scanner-suppression files editable without review; no test of guardrails | ✅ `ask` rules + probe + path check |
| Database rollback safety | Not defined | ✅ disposable DB, mandatory cycle, data-loss escalation |
| Evidence integrity | Raw artefacts git-ignored, i.e. not retained; no exit status or SHA-256; no reproduction rule | ✅ retained, hashed, reproducible |
| Capacity controls | Cut line only | ✅ tracking, triggers, non-removable list |

## 2. Dependency graph

**Method:** `check_protocol` script (kept outside the repo, in the session scratchpad) parses the CSV table in protocol §3.1, the Mermaid graph in SPRINT_01 §2 and the ROADMAP Sprint 1 table, then checks four rules:

- **R1** — every graph and roadmap edge is implied by `hard`;
- **R2** — the linear order is a topological order of `hard ∪ process`;
- **R3** — no task sits in an earlier PR than one of its dependencies;
- **R4** — every subagent task depends on T15.

It also checks that PR1 contains only T15 and that the sequence diagram matches the table.

| Finding (rev. 1) | Correction |
|---|---|
| F-1 PR2 = T03 + T05, but T05 depends on T04 (PR3) | T04 + T05 now share PR5; T03 is PR3 |
| F-2 PR1 = T15 + T01 + T02. T01 is run by DevOps, which exists only after HC-1 reviews T15 | PR1 = T15 alone; T01 + T02 in PR2 |
| F-3 T01, T12, T13, T14 and T16 are run by subagents but had no dependency on T15 | `process` dependency on T15 added (R4) |
| F-4 ROADMAP says T14 depends on T08; the SPRINT_01 graph doesn't imply it | `hard` for T14 lists T06–T13 explicitly |
| F-5 T04–T10 integration tests (TC-SEC-19, TC-PLAT-07, sessions in Redis) need Postgres/Redis, which only T12 provided | **C-4:** T12a (the Postgres/Redis part of T12 + disposable overlay) runs after T03, before T04. No scope change; ≤ 0.25 h overhead. SPRINT_01 and ROADMAP updated to say so |

**Result after correction:** `tasks=17 PRs=12 — PROTOCOL DEPENDENCIES CONSISTENT`.

## 3. Agent permissions

| Finding | Correction |
|---|---|
| P-1 T15 required QA and Security notes, but those agents are created by T15 | T15 is validated by Opus review + HC-1; the new Security Reviewer then runs the guardrail probe as its first action |
| P-2 DevOps could add allowlists or ignores to `.gitleaks.toml`, `.trivyignore` or `.semgrep/**` — an unreviewed waiver | These files, and `docs/security/waivers.md`, are now *ask* rules (AGENT_SPECIFICATION §2); any coverage reduction is a waiver (HC-5) |
| P-3 `git reset --hard` / `git clean` could silently discard work or evidence | Added as *ask* rules |
| P-4 No test that guardrails work | Guardrail probe (protocol §5.2), recorded as EV-S01-000 |
| P-5 QA could appear to validate its own T14 work | T14 is reviewed by Security Reviewer (security tests), orchestrator (correctness) and human |
| P-6 Guardrails could block legitimate operations | Checked: commits on branches, lockfile installs, compose up/down, disposable-DB cycles (tmpfs, so no `down -v`), `make clean`, HTTPX checks and containerised scanners all remain possible |
| P-7 T04 had Sonnet writing `01-roles.sh` (infrastructure); T10 edited the Makefile owned by T01 | `01-roles.sh` moved to DevOps (T12a); T10 may only fill the recipes of the existing `openapi` / `bootstrap-admin` targets |

QA and Security Reviewer cannot modify implementation code: their tools are constrained by the spec, their paths are checked per PR, and they cannot validate work they authored. DevOps cannot weaken hardening, gates or scanner coverage without ADR + HC-5, and cannot edit requirements, ACs, SRs or the threat model.

## 4. Database rollback safety

Added as protocol §6:
- **Disposable test DB:** project `aegissoc-test`, tmpfs, throwaway passwords.
- **Mandatory cycle:** upgrade → validate → downgrade → validate absence → upgrade → validate.
- **Prohibited without maintainer approval** on the persistent local stack: downgrade, `DROP`, `TRUNCATE`, `down -v`, `reset`, `restore`, volume removal.
- **Data-loss escalation:** each migration declares `data_loss: none | possible`; `possible` requires Opus review, an expand/contract plan, a backup and maintainer approval.

## 5. Evidence integrity

| Finding | Correction |
|---|---|
| E-1 `qa/reports/**/raw/` is git-ignored, so original artefacts weren't retained | Small artefacts are committed under `evidence/` with a SHA-256 manifest; large ones are CI artefacts (90-day retention) plus a local copy, also in the manifest. `raw/` is scratch only (QA_STRATEGY §10 updated) |
| E-2 The evidence record lacked exit status, artefact hashes, tool versions and reproduction | Template rewritten (`qa/templates/EVIDENCE_RECORD_TEMPLATE.md`) |
| E-3 No rule against textual claims or wrong-SHA results | Protocol §7 "Not accepted" row |
| E-4 No defined independent reproduction | QA re-runs the commands at the recorded SHA in a clean `git worktree` with a fresh disposable DB; a mismatch blocks |

## 6. Capacity controls

The 29.5 h estimate and the cut line (25 h by day 10) are preserved.

Added:
- a time log (`docs/sprints/SPRINT_01_TIME_LOG.md`, created at sprint start);
- an overrun trigger (> 50 % on a task);
- escalation when the projected total exceeds 30 h after the cut line: Opus proposes options, the maintainer chooses;
- an explicit list of controls, tests and scanners that cannot be removed to save time.

## 7. Files changed

| File | Change |
|---|---|
| `docs/SPRINT_01_EXECUTION_PROTOCOL.md` | Rewritten as revision 2 (all corrections above, §3.1 machine-checkable table) |
| `docs/SPRINT_01_PROTOCOL_REVIEW.md` | New (this file) |
| `docs/sprints/SPRINT_01.md` | Recommended order and PR grouping corrected; T12a described in T12; `01-roles.sh` ownership noted in T04 |
| `docs/ROADMAP.md` | S1-T12 row notes T12a |
| `docs/AGENT_SPECIFICATION.md` | *ask* rules: `git reset --hard`, `git clean`, scanner-suppression files |
| `docs/QA_STRATEGY.md` | §10 evidence retention |
| `qa/templates/EVIDENCE_RECORD_TEMPLATE.md` | Full metadata, hashes, reproduction |

Not changed: DECISIONS.md, every ADR, ACCEPTANCE_CRITERIA, SECURITY requirements, the threat model.

## 8. Unresolved issues (for the maintainer)

| ID | Issue | Proposed handling |
|---|---|---|
| **U-1** | The D-10 row in DECISIONS.md says "Sonnet or Opus", while this protocol assigns implementation to Sonnet only | Settle it in the D-10 approval wording. The row was not edited, because decisions are maintainer-only |
| **U-2** | Per-agent path bounds remain instruction-based (Claude Code tool lists can't express paths); enforcement is the PR path check | Accept for Sprint 1. Optionally add an automated per-agent path check script in Sprint 2 (needs agent identification in commits) |
| **U-3** | C-4 (T12a) reorders approved Sprint 1 work. Scope is unchanged, but it's a change to the approved sequence | Acknowledge in the D-10 approval |
| **U-4** | D-05 is still open | Recommended before D-10 |

## 9. Final checklist

| # | Item | Status |
|---|---|---|
| 1 | Every task dependency in the protocol matches SPRINT_01 and ROADMAP (R1) | ✅ |
| 2 | Linear sequence is a valid topological order (R2) | ✅ |
| 3 | No PR combines or orders tasks against their dependencies (R3); PR1 = T15 only | ✅ |
| 4 | Machine-checkable dependency table present (§3.1) | ✅ |
| 5 | Each agent has only the permissions its tasks need | ✅ |
| 6 | QA and Security Reviewer cannot modify implementation or approve their own work | ✅ (paths instruction-based, review-checked — U-2) |
| 7 | DevOps cannot bypass security controls or alter requirements | ✅ |
| 8 | Guardrails don't block legitimate operations | ✅ |
| 9 | Permission enforcement test defined (guardrail probe, path check, author ≠ validator) | ✅ |
| 10 | Disposable test DB procedure and up → validate → down → up cycle | ✅ |
| 11 | Destructive operations on persistent environments need maintainer approval; data-loss escalation | ✅ |
| 12 | Original artefacts retained with SHA, UTC time, environment, command, exit status, location, hash | ✅ |
| 13 | Textual claims rejected; independent reproduction defined | ✅ |
| 14 | 29.5 h estimate and 25 h day-10 cut line preserved; escalation defined; no security control removable | ✅ |
| 15 | No code, infrastructure or workflow created; no decision/ADR/AC changed; D-10 not approved; Sonnet not authorised | ✅ |
| 16 | ID and link check | ✅ (see final run below) |

**Verdict:** the protocol is internally consistent and **ready for maintainer approval**, subject to U-1 and U-3 being settled in the D-10 wording. Implementation remains unauthorised.
