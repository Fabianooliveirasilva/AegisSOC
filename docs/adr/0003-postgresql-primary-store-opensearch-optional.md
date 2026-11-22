# ADR-0003: PostgreSQL as primary and event store; OpenSearch optional post-MVP

- **Status:** Accepted (2026-11-21, decision D-06)
- **Date:** 2026-11-21
- **Related:** DATABASE_DESIGN.md; AC-SIEM-08

## Context
The SIEM needs time-range search, filters, full-text and aggregations. OpenSearch is the usual choice but needs 2–4 GB RAM, index templates and lifecycle management. Core stack must stay ≤ 2.5 GB. Demo volume: ≤ ~100 M rows worst case over 30 days, usually far less.

## Decision
Store normalised events in a PostgreSQL 16 table range-partitioned by day, with hot ECS fields as columns, the full document as JSONB, a generated `tsvector`, and B-tree/GIN/GiST indexes. Search goes through an `EventSearchBackend` interface with a Postgres implementation. OpenSearch is a post-MVP optional profile implementing the same interface.

## Alternatives considered
| Option | Pros | Cons |
|---|---|---|
| OpenSearch from day one | Purpose-built search, scale | RAM, ops, dual-write consistency, more to test |
| ClickHouse | Excellent analytics | Another engine to learn/operate; weaker for transactional data |
| TimescaleDB | Time-series helpers | Extension licensing nuance (TSL features); plain partitioning suffices |
| **PostgreSQL partitions (chosen)** | One store, transactional integrity with alerts/incidents, cheap retention via DROP PARTITION | Full-text and aggregation slower at large scale |

## Consequences
- Retention is O(1) partition drops.
- Performance targets (AC-SIEM-08) validated at 1 M events; beyond that OpenSearch is the documented path.
- Query DSL compiles to SQL; must be injection-safe (SR-11).

## Addendum — 2026-11-21 (planning audit M-2)

The worker connects as `aegis_app`, which has no DDL rights, yet must create and drop daily partitions. Partition management therefore goes through two owner-owned `SECURITY DEFINER` functions, `aegis_ensure_event_partitions(days_ahead)` and `aegis_drop_event_partitions_before(cutoff)`, with input guards, a fixed `search_path` and `EXECUTE` granted only to `aegis_app` (DATABASE_DESIGN §6). This keeps least privilege for the application role.
