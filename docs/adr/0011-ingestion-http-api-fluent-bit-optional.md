# ADR-0011: HTTP ingestion API as the single entry point; Fluent Bit optional

- **Status:** Accepted (2026-11-21, decision D-06)
- **Date:** 2026-11-21
- **Related:** SYSTEM_DESIGN.md §3.2; SR-08, SR-22, SR-34

## Context
Sources: our synthetic generator (primary) and, for realism, a real shipper. Supporting syslog/UDP/Beats protocols adds attack surface and work.

## Decision
All telemetry enters through `POST /api/v1/ingest/events` (HTTPS via edge, per-source API key). Fluent Bit is offered as an optional Compose profile using its `http` output to the same endpoint (tailing sample files). No syslog/UDP listeners in MVP.

## Alternatives considered
| Option | Pros | Cons |
|---|---|---|
| Syslog listener | Classic SIEM input | Unauthenticated by default, UDP spoofing, parsing at the edge |
| Fluent Bit mandatory | Realistic pipeline | Extra container in core; config work |
| **HTTP API + optional Fluent Bit (chosen)** | One authenticated, rate-limited path | Real devices need a shipper |

## Consequences
- Source identity always comes from the key (log-poisoning control).
- Same limits and backpressure apply to all senders.
