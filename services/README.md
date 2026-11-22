# services/

Independently deployable auxiliary services that are **not** part of the core platform.

| Path | What | Talks to | Created in |
|---|---|---|---|
| `synthetic-generator/` | Synthetic log producer: benign baseline, attack storylines (D01–D12), replay; writes ground-truth manifests | ingestion API only (own API key per source) — no DB access | Sprint 2 |
