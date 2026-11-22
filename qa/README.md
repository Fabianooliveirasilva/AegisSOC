# qa/

Tests above unit level, test assets and QA evidence. Unit tests live next to the code (`apps/api/tests/unit`, `apps/web/src/**/*.test.ts(x)`). Strategy: [docs/QA_STRATEGY.md](../docs/QA_STRATEGY.md). Cases: [docs/TEST_PLAN.md](../docs/TEST_PLAN.md).

| Path | Contents | Tooling |
|---|---|---|
| `api/` | HTTP contract, auth, RBAC, error tests | pytest + HTTPX |
| `integration/` | module services with real Postgres/Redis, worker consumers, SQL validation (`integration/sql`) | pytest |
| `e2e/` | user journeys + accessibility | Playwright + TypeScript |
| `detection/` | pipeline-mode detection scenarios, ground-truth evaluation | runner + generator |
| `security/` | abuse cases, injection/XSS corpora, prompt-injection and redaction corpora, ZAP baseline config | pytest, Playwright |
| `performance/` | k6 scripts and result summaries | k6 (container) |
| `templates/` | QA report, bug report, evidence record templates | — |
| `reports/sprint-NN/` | QA reports, generated traceability, curated evidence (`raw/` is git-ignored) | — |
