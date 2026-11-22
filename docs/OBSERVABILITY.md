# AegisSOC — Observability and Metrics

## 1. Signals

| Signal | Implementation |
|---|---|
| Logs | structlog JSON to stdout; fields `ts, level, logger, msg, request_id, user_id?, route, status, duration_ms`; worker adds `stream, consumer, message_id` |
| Metrics | `prometheus-client` on `/metrics` (api :8000, worker :9100), internal networks only |
| Health | `/health/live`, `/health/ready`; worker heartbeat key in Redis every 10 s (`aegis:hb:<worker_id>`) |
| Traces | Not in MVP. `request_id` propagated into stream payloads gives end-to-end correlation. OpenTelemetry is a post-MVP candidate |

## 2. Metric catalogue

Every metric that can be influenced by synthetic traffic carries the label `data_origin` (`synthetic`|`lab`). UI and dashboards show a **SIMULATED** badge when all contributing sources are synthetic.

| Required metric | Prometheus name | Type | Labels |
|---|---|---|---|
| Log ingestion rate | `aegis_ingest_records_total` | counter | source, data_origin, outcome (`accepted`,`rejected`) |
| Ingest request latency | `aegis_ingest_request_seconds` | histogram | status |
| Processing latency (accept → stored) | `aegis_pipeline_latency_seconds` | histogram | stage (`normalize`,`detect`,`correlate`) |
| Event processing failures | `aegis_ingest_records_failed_total` | counter | source, stage, error_code |
| DLQ size | `aegis_dlq_messages` | gauge | |
| Stream lag | `aegis_stream_lag_messages` | gauge | stream, group |
| Detection execution time | `aegis_rule_eval_seconds` | histogram | rule_id (top-N only, others `other`) |
| Rule budget breaches | `aegis_rule_eval_budget_exceeded_total` | counter | rule_id |
| Detection latency (accept → alert) | `aegis_detection_latency_seconds` | histogram | |
| Alert volume | `aegis_alerts_created_total` | counter | severity, rule_id, data_origin |
| Incident resolution time | `aegis_incident_time_to_close_seconds` | histogram | severity |
| Detection precision | `aegis_rule_precision` | gauge (from rollup) | rule_id, data_origin |
| False-positive rate | `aegis_rule_fp_rate` | gauge | rule_id, data_origin |
| Scenario pass rate | `aegis_qa_scenario_pass_ratio` | gauge | scope |
| API response time | `aegis_http_request_seconds` | histogram | method, route (template), status |
| Service availability | `up` (Prometheus) + `aegis_dependency_up` | gauge | dependency |
| AI usage | `aegis_ai_analyses_total`, `aegis_ai_tokens_total` | counter | task, status / direction |
| Auth events | `aegis_auth_events_total` | counter | event (`login_success`,`login_failure`,`throttled`,`repeated_failures`) |

Cardinality rules: no user IDs, IPs or event IDs as labels; `rule_id` capped to active rules (≤ 100).

## 3. Dashboards (Grafana, provisioned from `infrastructure/observability/grafana/`)

1. **Platform health** — availability, API latency p50/p95/p99 by route, error rate, dependency up, worker heartbeats.
2. **Ingestion pipeline** — EPS by source, accepted vs rejected, processing latency per stage, stream lag, DLQ, parse failures by error code.
3. **Detection quality** — alerts by severity/rule, eval time p95 per rule, budget breaches, FP rate and precision per rule (SIMULATED badge), scenario pass ratio.
4. **SOC operations** — open incidents by status/priority, time to triage/close, alert backlog age.
5. **AI usage** — analyses by task/status, tokens per day vs budget, refusals, rejected (validation) rate.

The in-app **Security Overview** screen shows the SOC-facing subset from the API (`/overview`) so the demo works without Grafana.

## 4. Alerting rules (`infrastructure/observability/prometheus/rules.yml`)

| Alert | Condition | Severity |
|---|---|---|
| `AegisApiDown` | `up{job="api"} == 0` for 1 m | critical |
| `AegisWorkerNoHeartbeat` | no worker heartbeat for 1 m | critical |
| `AegisIngestLagHigh` | `aegis_stream_lag_messages{stream="aegis:ingest:raw"} > 50000` for 5 m | warning |
| `AegisDLQGrowing` | `increase(aegis_dlq_messages[15m]) > 0` | warning |
| `AegisParseFailureRate` | failed / total > 5 % for 10 m per source | warning |
| `AegisSourceSilent` | source health `silent` | warning |
| `AegisDetectionLatencyHigh` | p95 `aegis_detection_latency_seconds` > 10 s for 10 m | warning |
| `AegisRuleBudgetBreaches` | `rate(aegis_rule_eval_budget_exceeded_total[5m]) > 1` | warning |
| `AegisApiLatencyHigh` | p95 > 1 s for 10 m | warning |
| `AegisAuthRepeatedFailures` | `increase(aegis_auth_events_total{event="repeated_failures"}[10m]) > 0` | warning |
| `AegisAIBudget80` | tokens today > 80 % budget | info |

Alerts route to Grafana's UI only (no external notification channels in MVP). Rules have `promtool` unit tests (AC-OBS-03).

## 5. Simulated vs real measurements

| Kind | Examples | Labelled |
|---|---|---|
| **Real operational** | API latency, pipeline latency, eval time, stream lag, availability, error rates | measured on the demo host — real for that host, not a capacity claim |
| **Simulated (synthetic-derived)** | precision, FP rate, recall, alert volume, MTTR | `data_origin=synthetic` + SIMULATED badge; reports state "derived from synthetic data and simulated analyst dispositions" |
