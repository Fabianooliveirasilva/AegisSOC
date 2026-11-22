# AegisSOC — Definition of Done

A level is done only when **every** box is ticked, with evidence linked. "Done" is decided by QA + human, not by the implementer.

## 1. Task (roadmap item, e.g. `S2-T04`)

- [ ] Implements exactly the task scope; no future-sprint functionality
- [ ] Follows the approved architecture and module boundaries (import-linter green)
- [ ] Unit tests added/updated; mapped integration/API tests added for its ACs, with `req(...)` markers
- [ ] Lint, format, type-check clean (ruff, mypy --strict, eslint, tsc)
- [ ] No new High/Critical scanner findings; no secrets
- [ ] New dependency (if any) justified with licence noted in PR
- [ ] Docs touched where behaviour, config or API changed (OpenAPI snapshot regenerated)
- [ ] Implementation report in PR (HANDOFF §6 format)

## 2. Feature (one or more ACs)

- [ ] All mapped acceptance criteria demonstrably met (test output linked)
- [ ] Negative, boundary and permission cases tested (RBAC matrix updated for new routes)
- [ ] Security requirements touched are verified by their TCs
- [ ] Audit events emitted for SR-17 actions in scope
- [ ] UI (if any): loading, empty, error states; keyboard accessible; axe 0 serious/critical
- [ ] Observability: metrics/logs for the new path exist where OBSERVABILITY.md requires
- [ ] QA Engineer Agent validation note: **Accepted** (or Accepted with only S3/S4 defects logged)
- [ ] Security Reviewer note for changes touching auth, ingestion, files, AI, infra, CI

## 3. Detection rule

- [ ] Sigma rule with `id`, `title`, `description`, `author`, `references`, `level`, `tags` (ATT&CK), `falsepositives`
- [ ] Static validation: 0 errors
- [ ] ≥ 1 positive and ≥ 1 negative scenario, passing in unit and pipeline mode
- [ ] Generator storyline exists (for ground-truth evaluation)
- [ ] Regression suite green with the rule active
- [ ] Approved by someone other than the author
- [ ] Evaluation p95 within budget on perf sample

## 4. Sprint

- [ ] All committed tasks meet the Task DoD; any dropped stretch items recorded in ROADMAP
- [ ] Sprint ACs covered 100 % by passing tests in the traceability matrix
- [ ] Full regression (unit, integration, API, E2E, detection, security) green on `main`
- [ ] No open S1/S2 bugs in sprint scope
- [ ] QA report `qa/reports/sprint-NN/QA_REPORT.md` filed with evidence
- [ ] Threat model reviewed for new surfaces; new threats added with mitigations
- [ ] Docs and ADRs updated; CHANGELOG entry
- [ ] Demo of the sprint goal recorded (short script in the QA report)
- [ ] Human acceptance recorded

## 5. Release (`v0.x.0`)

- [ ] Sprint DoD for all included sprints
- [ ] Security checklist in [SECURITY.md §5](../SECURITY.md#5-security-checklist-per-release) complete
- [ ] Images built, scanned, SBOM attached; tag signed
- [ ] Backup/restore verified on this version
- [ ] README quick start verified on a clean machine
