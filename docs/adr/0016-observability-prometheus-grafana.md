# ADR-0016: Prometheus metrics and optional Grafana; structured logs; no tracing in MVP

- **Status:** Accepted (2026-11-21, decision D-06)
- **Date:** 2026-11-21
- **Related:** OBSERVABILITY.md; AC-OBS-*

## Context
We must show operational metrics and distinguish simulated from real measurements without heavy infrastructure.

## Decision
`prometheus-client` metrics on internal `/metrics` for api and worker; Prometheus + Grafana in an optional `observability` profile with provisioned dashboards and alert rules (tested with promtool). Structured JSON logs with request IDs propagated through stream payloads. OpenTelemetry deferred. The in-app Overview covers SOC-facing metrics without Grafana.

## Alternatives considered
| Option | Pros | Cons |
|---|---|---|
| OpenTelemetry + collector + Tempo/Loki | Full observability | Several more containers; time |
| In-app only | Lightest | No real ops dashboards/alerting |
| **Prometheus/Grafana optional (chosen)** | Industry standard, small | Second place to look for metrics |

## Consequences
- `data_origin` label on synthetic-influenced metrics; SIMULATED badges.
