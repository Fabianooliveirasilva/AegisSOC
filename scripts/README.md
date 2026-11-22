# scripts/

Operational and developer scripts (stdlib-only Python or POSIX shell), invoked via the root `Makefile`. Created from Sprint 1.

| Script | Purpose | Sprint |
|---|---|---|
| `setup-secrets` | generate random secrets into `infrastructure/compose/secrets/` | S1 |
| `check-compose` | assert container hardening rules (TC-INF-01) | S1 |
| `traceability` | build AC/SR → TC → result matrix from test markers | S2 |
| `docs-check` | verify doc links and that referenced IDs (AC/SR/T/TC/ADR) exist | S1 |
| `backup` / `restore` | pg_dump + evidence archive, optional age encryption | S5 |
