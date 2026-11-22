# System architecture

Trust boundaries (TB-n) match [THREAT_MODEL.md §2](../THREAT_MODEL.md#2-trust-boundaries).

```mermaid
flowchart LR
  subgraph TB1["TB1 — User browser"]
    U[Analyst / Engineer / Admin<br/>React SPA]
  end
  subgraph TB2["TB2 — Log sources (untrusted)"]
    GEN[Synthetic generator]
    FB[Fluent Bit (optional)]
    EXT[Other HTTP senders]
  end
  subgraph HOST["Docker host — 127.0.0.1 only"]
    EDGE[Caddy edge<br/>TLS · headers · static SPA · size limits]
    subgraph APP["TB3 — Application zone"]
      API[API — FastAPI<br/>auth · RBAC · rate limit · all module routers]
      WRK[Worker<br/>normaliser · detector · correlator · IOC matcher · AI runner · QA runner · scheduler]
    end
    subgraph DATA["Data zone"]
      PG[(PostgreSQL 16)]
      RD[(Redis 7<br/>streams · sessions · counters)]
      EV[(Evidence volume)]
    end
    subgraph OBS["Observability (optional)"]
      PROM[Prometheus]
      GRAF[Grafana]
    end
  end
  subgraph TB4["TB4 — External (optional)"]
    ANT[Anthropic API]
    MISP[MISP (post-MVP)]
  end

  U -- HTTPS --> EDGE
  GEN -- HTTPS + ingest key --> EDGE
  FB -- HTTPS + ingest key --> EDGE
  EXT -- HTTPS + ingest key --> EDGE
  EDGE -- HTTP /api/* --> API
  API --> PG
  API --> RD
  API --> EV
  RD <--> WRK
  WRK --> PG
  WRK -- HTTPS, minimised context --> ANT
  WRK -. pull IOCs .-> MISP
  PROM -- scrape /metrics --> API
  PROM -- scrape /metrics --> WRK
  GRAF --> PROM
```
