# ADR-0004: Redis Streams (not Celery) for asynchronous processing

- **Status:** Accepted (2026-11-21, decision D-06)
- **Date:** 2026-11-21
- **Related:** ARCHITECTURE.md §4–5; SR-13

## Context
We need durable hand-off from the ingest endpoint to normalisation and detection, with backpressure, replay after crashes, ordered processing per stream and a few background jobs (AI, QA runs, retention).

## Decision
Use Redis Streams with consumer groups (`XADD` with `MAXLEN ~`, `XREADGROUP`, `XACK`, `XAUTOCLAIM`, delivery-count based DLQ) and a small in-house worker framework in `aegissoc.core` running asyncio consumers. Scheduled jobs run in the worker under a Redis leader lock. Payloads are JSON only. Redis runs with AOF and `noeviction`.

## Alternatives considered
| Option | Pros | Cons |
|---|---|---|
| Celery | Mature, many features | Heavy; historical pickle risks; sync-first; broker abstraction we don't need; harder to reason about stream semantics |
| Dramatiq / arq | Lighter | Job-queue model, not stream processing; still no replay/consumer-lag view |
| Kafka/Redpanda | Proper log | Too heavy for laptop demo |
| **Redis Streams (chosen)** | Replay, consumer groups, lag metrics, backpressure, already needed for sessions | We own retry/DLQ code (small, testable) |

## Consequences
- At-least-once delivery → consumers must be idempotent (dedup keys).
- Licence: Redis ≥ 7.4 is RSALv2/SSPLv1 (8.x adds AGPLv3); fine for local use; Valkey is a BSD drop-in (decision D-02).
- QA: crash/redelivery tests (TC-SIEM-06), DLQ tests (TC-SIEM-07).
