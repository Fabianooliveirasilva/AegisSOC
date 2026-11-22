# apps/

Deployable applications.

| Path | What | Deployable | Created in |
|---|---|---|---|
| `api/` | Python package `aegissoc`: FastAPI API **and** worker (same image, different entrypoint: `uvicorn aegissoc.main:app` / `python -m aegissoc.worker`) | yes (backend image) | Sprint 1 (worker entrypoint Sprint 2) |
| `web/` | React + TypeScript SPA, built into the edge (Caddy) image | yes (via edge image) | Sprint 1 |

Layout of `api/`: see [docs/sprints/SPRINT_01.md S1-T02](../docs/sprints/SPRINT_01.md#s1-t02--backend-skeleton) and [component diagram](../docs/diagrams/component-diagram.md).
