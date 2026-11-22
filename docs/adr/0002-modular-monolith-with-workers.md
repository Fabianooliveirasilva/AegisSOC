# ADR-0002: Modular monolith with asynchronous workers

- **Status:** Accepted (2026-11-21, decision D-06)
- **Date:** 2026-11-21
- **Related:** ARCHITECTURE.md §2–3

## Context
One part-time developer, 10 weeks, laptop deployment, demo-scale data (≤ 2,000 EPS bursts). Ingestion and detection must not block API requests. Portfolio reviewers value clear boundaries.

## Decision
One Python package `aegissoc` with modules (core, platform.auth, platform.audit, siem, detection, alerts, incidents, intel, hunting, ai, qa, observability). Two entrypoints from the same image: `api` (FastAPI) and `worker` (stream consumers + scheduler). Module boundaries enforced by import-linter: modules interact only through each other's `service` interfaces and never touch another module's tables.

## Alternatives considered
| Option | Pros | Cons |
|---|---|---|
| Microservices | Independent scaling and deploys | Distributed transactions, many images/pipelines, contract versioning, ops load; no scaling need |
| Synchronous monolith | Simplest | Ingest/detection on request path; no backpressure |
| **Modular monolith + workers** | Simple ops, async processing, enforceable boundaries, extractable later | Single DB; discipline needed (enforced by tooling) |

## Consequences
- One backend image, one CI build; worker scales horizontally per consumer group.
- Extraction of the ingestion pipeline later is possible because it already communicates via streams.
- QA: integration tests can run api + worker in-process.
