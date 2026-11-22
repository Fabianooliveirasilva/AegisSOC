# Data flow

```mermaid
flowchart LR
  SRC[Log source] -->|raw records batch| ING[Ingest endpoint<br/>auth key → source binding<br/>size/rate limits]
  ING -->|XADD| RAW[[aegis:ingest:raw]]
  RAW --> NORM[Normaliser<br/>parser by source_type<br/>ECS mapping · enrichment]
  NORM -->|bulk insert| EVT[(events<br/>partitioned by day)]
  NORM -->|failures| ERR[(ingest_errors)]
  NORM -->|XADD ids| NS[[aegis:events:normalized]]
  NS --> DETC[Detector<br/>active rule versions]
  NS --> IOCM[IOC matcher]
  DETC -->|match| ALS[Alert service<br/>dedup · severity]
  IOCM -->|match| ALS
  ALS --> AL[(alerts / alert_events)]
  ALS -->|XADD| AN[[aegis:alerts:new]]
  AN --> COR[Correlator<br/>count / temporal windows in Redis]
  COR -->|correlated alert| ALS
  AL -->|analyst promotes| INC[(incidents)]
  EVT --> SEARCH[Search / timelines / hunts]
  AL --> AIJ[AI analysis job]
  INC --> AIJ
  EVT --> AIJ
  AIJ -->|minimised, redacted context| LLM[Anthropic API]
  LLM -->|structured result| VAL[Output validator<br/>schema · citations]
  VAL --> AIA[(ai_analyses)]
  RULES[detections/ in git] -->|sync| RV[(detection_rule_versions)]
  SCN[scenarios] --> QAR[QA runner] --> VR[(validation_runs)]
  RV --> DETC
  RV --> QAR
```

Data classification used for minimisation (see [SECURITY.md §6](../../SECURITY.md#6-data-protection)):

| Class | Examples | Leaves host? |
|---|---|---|
| C1 Secrets | passwords, session IDs, API keys, Anthropic key | Never |
| C2 Identifiers | usernames, emails, internal IPs, hostnames | Only to Anthropic, only when AI enabled, optionally pseudonymised |
| C3 Event content | command lines, URLs, messages | Only to Anthropic, minimised, wrapped as untrusted data |
| C4 Metadata | rule IDs, ATT&CK IDs, counts | Yes (to Anthropic when AI enabled) |
