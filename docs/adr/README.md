# Architecture Decision Records

ADR-0001…0016 were **Accepted** on 2026-11-21 (decision D-06 in [DECISIONS.md](../DECISIONS.md)). New ADRs start as **Proposed** until the maintainer accepts them. Template: [0000-template.md](0000-template.md). Process: [ADR-0001](0001-record-architecture-decisions.md).

| ADR | Title | Status |
|---|---|---|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | Accepted |
| [0002](0002-modular-monolith-with-workers.md) | Modular monolith with asynchronous workers | Accepted |
| [0003](0003-postgresql-primary-store-opensearch-optional.md) | PostgreSQL primary/event store; OpenSearch optional | Accepted |
| [0004](0004-redis-streams-for-async-processing.md) | Redis Streams instead of Celery | Accepted |
| [0005](0005-sigma-pysigma-custom-evaluator.md) | pySigma parsing + in-house streaming evaluator | Accepted |
| [0006](0006-normalized-event-schema-ecs-subset.md) | ECS subset as normalised schema | Accepted |
| [0007](0007-authentication-sessions.md) | Server-side sessions, CSRF, ingest API keys | Accepted |
| [0008](0008-edge-proxy-caddy.md) | Caddy edge proxy | Accepted |
| [0009](0009-frontend-stack.md) | Frontend stack | Accepted |
| [0010](0010-ai-analyst-claude-messages-api.md) | AI analyst: Messages API, read-only tools, HITL | Accepted |
| [0011](0011-ingestion-http-api-fluent-bit-optional.md) | HTTP ingestion; Fluent Bit optional | Accepted |
| [0012](0012-api-rest-openapi-code-first.md) | REST + code-first OpenAPI snapshot | Accepted |
| [0013](0013-monorepo-tooling.md) | Monorepo with uv and pnpm | Accepted |
| [0014](0014-development-agents-are-dev-time-only.md) | Specialised agents are dev-time only | Accepted |
| [0015](0015-detection-as-code-and-four-eyes.md) | Detection-as-code, regression gate, four-eyes | Accepted |
| [0016](0016-observability-prometheus-grafana.md) | Prometheus/Grafana optional, no tracing in MVP | Accepted |
