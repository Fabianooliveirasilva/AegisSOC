# ADR-0006: Normalised event schema is a subset of Elastic Common Schema (ECS)

- **Status:** Accepted (2026-11-21, decision D-06)
- **Date:** 2026-11-21
- **Related:** SYSTEM_DESIGN.md §3.3–3.4

## Context
Detections, search, hunting and AI context all need consistent field names across six source types.

## Decision
Normalise to an ECS subset (`@timestamp`, `event.*`, `host.*`, `user.*`, `source.*`, `destination.*`, `process.*`, `file.*`, `registry.*`, `url.*`, `http.*`, `user_agent.*`, `cloud.*`, `dns.*`, `winlog.*`) plus an `aegis.*` namespace that only the server writes (`aegis.source_id`, `aegis.data_origin`, `aegis.batch_id`). Hot fields are columns; the full document is JSONB.

## Alternatives considered
| Option | Pros | Cons |
|---|---|---|
| OCSF | Vendor-neutral, rich | Heavier, fewer Sigma mapping examples |
| Custom schema | Free-form | Reinventing; harder for reviewers |
| **ECS subset (chosen)** | Well documented (Apache-2.0), common Sigma mappings | Some Windows fields need `winlog.event_data.*` passthrough |

## Consequences
- Sigma field mapping pipeline maps Sigma's Windows/Linux names to ECS.
- `aegis.*` from payloads are dropped (SR-34).
