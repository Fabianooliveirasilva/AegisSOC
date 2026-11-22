# AegisSOC — QA Strategy

| | |
|---|---|
| Owner | QA Engineer Agent (execution), human maintainer (acceptance) |
| Related | [TEST_PLAN.md](TEST_PLAN.md) · [ACCEPTANCE_CRITERIA.md](ACCEPTANCE_CRITERIA.md) · [DEFINITION_OF_DONE.md](DEFINITION_OF_DONE.md) · [DEVSECOPS.md](DEVSECOPS.md) |

## 1. Principles

1. **Independence.** The agent that implements a change never signs off its own QA. The QA Engineer Agent works from the acceptance criteria and the running system, not from the developer's description, and is expected to try to break assumptions (boundary values, concurrency, malformed input, role abuse).
2. **Evidence or it didn't happen.** Every claim of "passing" links to a CI run, a JUnit/HTML report, or captured command output stored under `qa/reports/<sprint>/`.
3. **Requirements-driven.** Every `AC-*` and `SR-*` maps to ≥ 1 test case. Tests carry markers with the IDs they verify (`@pytest.mark.req("AC-SIEM-02")`, Playwright `test.info().annotations`), so traceability is generated, not hand-maintained.
4. **Detections are software.** Rules get unit tests (scenarios), regression tests and production-like feedback (dispositions) like any code.
5. **Shift left, but test the whole system.** Fast unit tests on every save; the full Compose stack is exercised by E2E and pipeline scenarios on every PR.

## 2. Test pyramid

```
                 ▲  Manual exploratory + live-AI evaluation (per sprint, time-boxed 1 h)
                ▲▲  E2E (Playwright, full Compose stack)               ~ 30 tests   ≤ 8 min
              ▲▲▲▲  API tests (HTTPX against running api + real DB)   ~ 200 tests  ≤ 4 min
            ▲▲▲▲▲▲  Integration (pytest, real Postgres/Redis, worker in-process) ~ 150 ≤ 4 min
        ▲▲▲▲▲▲▲▲▲▲  Unit (pytest / Vitest) + detection scenarios (unit mode)   ~ 1000+ ≤ 2 min
```

Cross-cutting suites: security tests (`qa/security`), performance (`qa/performance`, k6), contract (OpenAPI diff), accessibility (axe in Playwright).

| Level | Scope | Tooling | Location |
|---|---|---|---|
| Unit — backend | pure functions: parsers, evaluator, DSL compiler, state machines, redaction, validators | pytest, hypothesis | `apps/api/tests/unit` |
| Unit — frontend | hooks, formatters, components with logic | Vitest, Testing Library | `apps/web/src/**/*.test.ts(x)` |
| Detection (unit mode) | rule × scenario without DB | `aegissoc detections test` (pytest plugin) | `detections/scenarios` |
| Integration | module services with real Postgres/Redis; worker consumers | pytest + Compose services | `qa/integration` |
| API | HTTP contract, auth, RBAC, errors, pagination | pytest + HTTPX `AsyncClient` | `qa/api` |
| E2E | user journeys through the edge | Playwright + TypeScript | `qa/e2e` |
| Detection (pipeline mode) | raw events → ingest → alerts | runner + generator | `qa/detection` |
| Security | abuse cases, RBAC matrix, injection, headers, uploads, AI red-team | pytest, Playwright, ZAP baseline (local only, Sprint 5, non-blocking) | `qa/security` |
| Performance | ingest throughput, API latency, search latency, detection latency | k6 (container) + pytest timing | `qa/performance` |
| SQL validation | migrations up/down, constraints, triggers, index usage (`EXPLAIN`) on key queries | pytest + SQL fixtures | `qa/integration/sql` |

## 3. Test environments

| Env | How | Used for |
|---|---|---|
| `local-unit` | `make test-unit` (no containers) | inner loop |
| `local-stack` | `make up` + `make test-integration test-api test-e2e` | before PR |
| `ci` | GitHub Actions: service containers for integration/API; full Compose for E2E | every PR and `main` |
| `perf` | local-stack with `--profile generator`, k6 container; documented hardware | Sprints 2, 3, 5 |

The test DB is created per test session; each test runs in a transaction rolled back at the end (integration/API), except worker tests, which truncate touched tables. Redis uses DB index 15 flushed per test.

## 4. Test data management

- **Synthetic only.** No real logs. IPs from RFC 5737 (`192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`) and private ranges; domains `example.com` / `*.test`; fictitious users.
- **Fixtures:** factory functions (`factory_boy`-style, plain Python) for users, sources, events, rules, alerts, incidents; golden files for parsers in `apps/api/tests/fixtures/parsers/<source_type>/*.{in,out.json}`.
- **Synthetic log generator** (`services/synthetic-generator`): seeded and deterministic; storylines map 1:1 to detection scenarios D01–D12; produces a ground-truth manifest.
- **Scenario fixtures:** YAML scenarios per rule (format in SYSTEM_DESIGN §8).
- **Prompt-injection and redaction corpora:** `qa/security/prompt_injection/*.yml`, `qa/security/redaction/*.yml`.
- **Demo seed:** `make seed` creates demo sources, ATT&CK, playbooks, sample IOCs and (from Sprint 3) one demo user per role with a **random password** written only to the git-ignored secrets folder (SR-16) — idempotent, refuses outside `local`/`ci`. Test and E2E role users are created by fixtures through the admin API, never with fixed passwords.

## 5. Bug lifecycle

```
New → Triaged (severity, owner) → In progress → Fixed (PR linked) → Verified by QA → Closed
                     └→ Won't fix / Duplicate (reason required)      └→ Reopened
```

| Severity | Definition | Blocks |
|---|---|---|
| S1 Critical | security control bypass, data loss, platform unusable, wrong detection result for an active rule | sprint completion and release |
| S2 Major | feature does not meet an AC, no workaround | sprint completion |
| S3 Minor | AC met but defect with workaround / cosmetic in critical path | nothing (scheduled) |
| S4 Trivial | cosmetic | nothing |

Every fixed bug gets a regression test referencing the issue ID (`@pytest.mark.bug("GH-42")`). Bug reports use `qa/templates/BUG_REPORT_TEMPLATE.md` (also as a GitHub issue template).

## 6. Coverage requirements (CI-enforced)

| Area | Metric | Threshold |
|---|---|---|
| Backend overall (`aegissoc`) | line | ≥ 80 % |
| `siem.parsers`, `detection.evaluator`, `hunting.dsl`, `ai.validator`, `ai.redaction`, `platform.auth` | branch | ≥ 90 % |
| Frontend `src/lib`, `src/features/**/hooks` | line | ≥ 70 % |
| Active detection rules | ≥ 1 positive and ≥ 1 negative scenario | 100 % |
| Acceptance criteria of completed sprints | ≥ 1 passing mapped test | 100 % |
| Routes | permission declared + RBAC matrix test | 100 % |

Coverage is a floor, not a goal; mutation testing (`mutmut`) on the evaluator is a stretch in Sprint 5.

## 7. CI quality gates

Defined in [DEVSECOPS.md §3](DEVSECOPS.md#3-quality-gates). QA-relevant blocking gates: all test levels green, coverage thresholds, detection regression suite green, OpenAPI snapshot fresh, traceability matrix has no uncovered AC for completed sprints, no S1/S2 open bugs for the sprint scope.

## 8. Quality indicators (measured)

| Indicator | Definition | Target | Source |
|---|---|---|---|
| Scenario pass rate | passed / total scenarios in latest regression run | 100 % on `main` | validation_runs |
| Rule scenario coverage | active rules with ≥ 1 positive and ≥ 1 negative / active rules | 100 % | DB |
| Simulated recall | detected storylines / injected storylines (generator ground truth) | ≥ 0.9 | `qa evaluate-generator-run` (**simulated**) |
| Simulated false-alert rate | alerts outside any storyline window / total alerts in baseline-only run | ≤ 5 % | same (**simulated**) |
| FP rate per rule | FP / (TP + BTP + FP) dispositions, 30 d | ≤ 20 % (flag for tuning) | alerts (**simulated in demo**) |
| Detection latency p95 | ingest accept → alert created | ≤ 5 s at 500 EPS | metric `aegis_detection_latency_seconds` |
| Defect escape rate | bugs found after sprint acceptance / total bugs in sprint | ≤ 10 % | issues |
| Flaky test rate | tests that failed then passed on rerun / total, rolling 2 weeks | ≤ 1 % | CI |
| Mean time to fix S1/S2 | open → verified | ≤ 2 working sessions | issues |
| AC coverage | ACs of completed sprints with passing tests | 100 % | traceability |

## 9. Regression strategy

- Full unit + detection suite on every PR (fast).
- Integration + API + E2E smoke (tagged `@smoke`, ≤ 3 min) on every PR; full E2E on `main` and nightly.
- Detection regression on every PR touching `detections/`, `aegissoc/detection`, `aegissoc/siem/parsers`.
- Bug-fix regression tests are permanent and tagged `regression`.
- Before each sprint acceptance: full suite + perf smoke + security suite.

## 10. Evidence collection

Per sprint `qa/reports/sprint-NN/`:
- `QA_REPORT.md` (from template), `traceability.md` (generated), JUnit XML and HTML (pytest-html, Playwright report), screenshots of failures, k6 summaries, scanner outputs.
- **Original artefacts are retained:** small machine-readable artefacts are committed under `evidence/` with a SHA-256 `MANIFEST.md`; large ones stay as CI artefacts (90-day retention) plus a local copy outside git, listed in the manifest. `raw/` is only a git-ignored scratch area. Rules and independent reproduction: [SPRINT_01_EXECUTION_PROTOCOL.md §7](SPRINT_01_EXECUTION_PROTOCOL.md#7-evidence-requirements).
- Each evidence item records git SHA, date, environment, command.

## 11. QA independence protocol

1. Developer finishes a task and opens a PR with the implementation report (HANDOFF §6 format).
2. QA Engineer Agent receives: task ID, AC/SR IDs, PR diff summary — **not** the developer's test results.
3. QA runs the mapped test cases, adds missing negative/boundary tests, does ≤ 30 min exploratory testing on the running stack.
4. QA writes findings as bugs (template) and a validation note: `Accepted` / `Accepted with minor defects` / `Rejected`.
5. Rejected → back to developer. S1/S2 bugs block completion.
6. Human reads QA note + security note and approves merge.

## 12. QA report template

`qa/templates/QA_REPORT_TEMPLATE.md`.
