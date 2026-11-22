# Deployment diagram (Docker Compose, single host)

```mermaid
flowchart TB
  subgraph Host["Developer laptop — Docker Engine"]
    direction TB
    subgraph edge_net["edge_net (internal: true)"]
      EDGE["edge (Caddy)<br/>ports 127.0.0.1:8443→443, 127.0.0.1:8080→80 (redirect)<br/>profile: core"]
      GEN["generator<br/>profile: generator"]
      FB["fluent-bit<br/>profile: fluentbit"]
    end
    subgraph app_net["app_net (internal: true)"]
      API["api ×1<br/>uvicorn · non-root · read-only fs<br/>profile: core<br/>(also on edge_net)"]
      WRK["worker ×1..n<br/>python -m aegissoc.worker<br/>profile: core"]
      PG[("postgres:16<br/>volume pg_data<br/>profile: core")]
      RD[("redis:7<br/>AOF · volume redis_data<br/>profile: core")]
      OS[("opensearch<br/>profile: search (post-MVP)")]
    end
    subgraph obs_net["obs_net"]
      PROM["prometheus<br/>profile: observability"]
      GRAF["grafana 127.0.0.1:3000<br/>profile: observability"]
    end
    VOL[(volume evidence_data)]
  end
  EDGE --- API
  API --- PG & RD & VOL
  WRK --- PG & RD
  GEN -->|via edge| EDGE
  FB -->|via edge| EDGE
  PROM --- API & WRK
  GRAF --- PROM
  WRK -. egress HTTPS only if AI enabled .-> Internet((api.anthropic.com))
```

| Container | Memory limit | Notes |
|---|---|---|
| edge | 64 MB | |
| api | 512 MB | |
| worker | 512 MB | |
| postgres | 1 GB | `shared_buffers=256MB` |
| redis | 256 MB | `maxmemory-policy noeviction` (streams must not be evicted) |
| **core total** | **≈ 2.3 GB** | fits the ≤ 2.5 GB budget |
| generator | 128 MB | |
| fluent-bit | 64 MB | |
| prometheus + grafana | 512 MB | |
| opensearch | 2–4 GB | post-MVP only |

The edge additionally joins `public_net` (plain bridge) so its ports can be published; no other service joins it.

Egress: `edge_net` and `app_net` are `internal: true`. The worker joins an additional `egress_net` **only** when `AEGIS_AI_ENABLED=true`, so no other container can reach the internet.
