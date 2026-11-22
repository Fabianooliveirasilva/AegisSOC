# Open security findings carried across tasks

Tracking only. It changes no scope, requirement or decision. The owner column is a proposal until the maintainer confirms it.

| ID | Severity | Origin | Summary | Proposed owner / where | Must close before | Test |
|---|---|---|---|---|---|---|
| S1-T03-SEC-01 | Medium | S1-T03 (reviewed at `61bbdd6`, re-verified at `e9d1473`) | Starlette re-raises unhandled exceptions after sending the 500, so uvicorn writes the full traceback (message and Pydantic `input_value`) to stderr as plain text. The app logger is already fixed (`render_exception` keeps frames and type only) | (a) `core/logging.py`: route stdlib/uvicorn logs through the JSON and redaction chain, or add an outermost guard that swallows the re-raised exception. (b) `main.py` wiring in S1-T09. (c) uvicorn command in the backend Dockerfile / compose `api` in S1-T12: `log_config=None` or a JSON config. Also fix the false docstring in `core/errors.py` | Merge of S1-T06 (authentication) | Proposed TC-SEC-20 addition: a 500 whose exception message or Pydantic input contains a marker leaves no trace on stdout or stderr, under real uvicorn |
| S1-T03-SEC-02 | Low | S1-T03 | uvicorn access log records the full query string | S1-T12: `--no-access-log`, plus a JSON access line without the query from S1-T09 middleware | S1-T12 done | Same TC as above (query token) |
| S1-T03-SEC-03 / 07 / 17 | Low | S1-T03 | Key denylist gaps (`ingest_key`, `anthropic_key`, `signing_key`, bare `key`, `bearer`, `jwt`, `otp`); password in URL query string accepted; node budget shared with log record fields | Maintainer to decide: fix in a later core touch-up or accept | Before Sprint 1 closes | Unit tests in `test_core_logging.py` / `test_core_config.py` |
| QA-S1T03-008 | S4 | S1-T03 QA re-validation | No test fails if `X-Request-ID` is dropped from a bodyless HTTPException response | Implementer, next core touch | Sprint 1 closes | New unit test |

Details and evidence: `docs/security/reviews/sprint-01.md` (sections S1-T03 and "Re-verification at `e9d1473`"), `qa/reports/sprint-01/validation/S1-T03.md`.
