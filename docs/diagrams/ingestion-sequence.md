# Event ingestion sequence

```mermaid
sequenceDiagram
  autonumber
  participant S as Log source
  participant E as Caddy edge
  participant A as API (siem.ingest)
  participant R as Redis
  participant N as Worker: normaliser
  participant P as PostgreSQL
  participant D as Worker: detector

  S->>E: POST /api/v1/ingest/events (Bearer aik_…, ≤1 MiB, ≤500 records)
  E->>A: forward (size limit enforced)
  A->>R: rate-limit check (per key)
  A->>P: lookup api_key by id, verify hash (constant time), load source
  alt invalid key / disabled source
    A-->>S: 401 problem+json
  else over rate or backlog too high
    A-->>S: 429 Retry-After
  else ok
    A->>A: validate envelope (schema, record count, record size ≤ 64 KiB)
    A->>P: INSERT ingest_batches(status=queued)
    A->>R: XADD aegis:ingest:raw {batch_id, source_id, records}
    A-->>S: 202 {batch_id, accepted}
  end
  N->>R: XREADGROUP normaliser
  N->>N: parse per source_type, map to ECS, set event.ingested, source binding
  N->>P: bulk INSERT events ON CONFLICT (source_id, dedup_key) DO NOTHING
  N->>P: INSERT ingest_errors for failed records
  N->>P: UPDATE ingest_batches(status=processed, counts)
  N->>R: XADD aegis:events:normalized {event_ids}
  N->>R: XACK
  D->>R: XREADGROUP detector
  D->>P: SELECT events by ids
  D->>D: evaluate active rule versions (RE2, time budget)
  D->>P: INSERT alerts / alert_events (dedup)
  D->>R: XADD aegis:alerts:new ; XACK
```
