# AegisSOC — Deployment

Target: a single developer machine with Docker Engine ≥ 25 and Docker Compose v2, 8 GB RAM recommended (core stack ≤ 2.5 GB). Linux, macOS or Windows (WSL2). Diagram: [diagrams/deployment-diagram.md](diagrams/deployment-diagram.md).

> This describes the deployment that Sprint 1 will build. Nothing is runnable yet.

## 0. Developer prerequisites

Checked by `scripts/check-prereqs` (run first by `make setup`), which prints what is missing.

| Tool | Minimum | Notes |
|---|---|---|
| Docker Engine + Compose v2 | 25 / 2.24 | |
| GNU make | 4.x | |
| git | 2.40 | |
| uv | 0.5 | installs and pins Python 3.12 for the project — no separate Python install needed |
| Node.js | 22 LTS | |
| pnpm | 9 | via `corepack enable` |
| pre-commit | 3.x | `uv tool install pre-commit` |
| gitleaks | 8.x | optional on the host: the pre-commit config uses gitleaks' Docker-based hook (exact hook id verified in S1-T01) |
| Playwright browsers | — | `pnpm --filter e2e exec playwright install --with-deps chromium` |
| Hardware | 8 GB RAM, 10 GB free disk | core stack ≤ 2.5 GB |

## 1. Compose profiles

| Profile | Services | Purpose |
|---|---|---|
| `core` (default) | edge, api, worker (from Sprint 2), migrate (one-shot), postgres, redis | The platform |
| `generator` | generator | Synthetic traffic and storylines |
| `fluentbit` | fluent-bit (+ sample log writer) | Demonstrate shipping from files |
| `observability` | prometheus, grafana | Dashboards and alert rules |
| `search` | opensearch | Post-MVP optional search backend |

File layout: `infrastructure/compose/compose.yaml` (core) + `compose.<profile>.yaml` overlays; root `Makefile` wraps them.

## 2. Configuration

All settings via environment variables prefixed `AEGIS_`; secrets via `*_FILE` pointing to Docker secrets mounted at `/run/secrets/*`.

| Variable | Default | Notes |
|---|---|---|
| `AEGIS_ENV` | `local` | `local`, `ci` |
| `AEGIS_DATABASE_URL` | `postgresql+asyncpg://aegis_app@postgres:5432/aegissoc` | password from `AEGIS_DATABASE_PASSWORD_FILE` |
| `AEGIS_REDIS_URL` | `redis://redis:6379/0` | password from `AEGIS_REDIS_PASSWORD_FILE` |
| `AEGIS_SESSION_IDLE_MINUTES` / `_ABSOLUTE_HOURS` | 30 / 8 | |
| `AEGIS_TRUSTED_PROXY_CIDRS` | edge network CIDR | SR-41 |
| `AEGIS_INGEST_MAX_RECORDS` / `_MAX_BODY_BYTES` | 500 / 1048576 | |
| `AEGIS_INGEST_BACKPRESSURE_LAG` | 100000 | |
| `AEGIS_EVIDENCE_DIR` | `/data/evidence` | volume |
| `AEGIS_AI_ENABLED` | `false` | |
| `AEGIS_AI_PROVIDER` | `fixture` | `anthropic` \| `fixture` |
| `AEGIS_AI_MODEL` | `claude-opus-5-5` | |
| `AEGIS_AI_EFFORT` | `medium` | |
| `AEGIS_AI_FALLBACKS` | `true` | server-side refusal fallback |
| `AEGIS_AI_DAILY_TOKEN_BUDGET` | 2000000 | |
| `AEGIS_AI_PSEUDONYMIZE` | `false` | |
| `ANTHROPIC_API_KEY_FILE` | — | secret; only mounted into worker when AI enabled |
| `AEGIS_METRICS_ENABLED` | `true` | |

Secrets directory `infrastructure/compose/secrets/` (git-ignored, mode 700) is created by `make setup`, which generates `postgres_superuser_password` (used only by the Postgres init script), `postgres_owner_password`, `postgres_app_password` and `redis_password` (32 random bytes each; files mode 600; never overwritten). It creates **no** application users — the first admin is created after `make up` with `make bootstrap-admin`. `make setup-ci` additionally writes a random `bootstrap_admin_password` used only in CI. `make seed` (from Sprint 3) writes `demo_users.txt` with random per-user passwords and refuses to run unless `AEGIS_ENV` is `local` or `ci` (SR-16). `.env.example` documents non-secret overrides.

## 3. First run

```bash
make setup            # host only: check prerequisites, install pre-commit, generate secrets (no users)
make up               # core profile: migrations, then services; waits for healthchecks
make bootstrap-admin  # prompts for the first admin's password (stdin, no echo)
make seed             # grows per sprint: demo sources + ingest keys (S2), ATT&CK + demo users with random passwords (S3), playbooks + IOCs (S4)
make demo-data        # from Sprint 2: generator baseline + storylines
open https://localhost:8443   # accept the Caddy local CA or run `make trust-ca`
```

## 4. Networks and ports

| Network | Members | Internet |
|---|---|---|
| `public_net` (bridge) | edge only — required for publishing ports (containers on internal-only networks cannot publish) | yes (edge only) |
| `edge_net` (internal) | edge, api, generator, fluent-bit — log shippers reach the API only through the edge | no |
| `app_net` (internal) | api, worker, postgres, redis | no |
| `obs_net` | prometheus, grafana, api, worker | no |
| `egress_net` | worker (only when `AEGIS_AI_ENABLED=true`) | yes |

Generator and Fluent Bit call `https://edge/api/v1/ingest/events` and trust Caddy's local root CA, which is exported to a shared read-only volume on first start (TLS verification stays on).

Published ports: `127.0.0.1:8443` (edge HTTPS), `127.0.0.1:8080` (redirect), `127.0.0.1:3000` (Grafana, observability profile only). Postgres and Redis are never published (SR-24). For debugging, `make psql` uses `docker compose exec`.

## 5. Container hardening (SR-23)

Each service: `user: "10001:10001"` (non-root, where the image allows), `read_only: true` + `tmpfs: [/tmp]`, `cap_drop: [ALL]`, `security_opt: ["no-new-privileges:true"]`, `mem_limit`, `pids_limit`, `healthcheck`, `restart: unless-stopped`, images pinned by digest. Backend image: multi-stage `python:3.12-slim` build with `uv`, runtime contains only the venv and app, no compilers.

## 6. Database lifecycle

- Migrations run by a one-shot `migrate` service (`alembic upgrade head` as `aegis_owner`) before `api`/`worker` start (`depends_on: condition: service_completed_successfully`).
- Partitions ensured on worker start and hourly.

## 7. Backup and recovery (SR-37)

- `make backup` → `backups/aegissoc-<ts>.dump` (pg_dump `-Fc`) + `evidence-<ts>.tar.zst`; optional `AGE_RECIPIENT` encrypts both.
- `make restore FILE=…` → stops api/worker, restores into a fresh DB, re-runs migrations, restarts.
- Redis is not backed up (ephemeral state; in-flight queued batches may be lost — documented residual risk).
- Restore drill once per release (TC-INF-06). Demo RPO 24 h / RTO 1 h.

## 8. Upgrades and reset

- `make upgrade` → pull/build, run migrations, restart.
- `make reset` → **destroys volumes** after confirmation prompt; reseeds.

## 9. Troubleshooting

| Symptom | Check |
|---|---|
| Browser TLS warning | `make trust-ca` installs Caddy's local root, or accept once |
| `/ready` 503 | `make logs s=postgres` / `s=redis` |
| Events not appearing | `GET /api/v1/ingest/batches/{id}`; worker logs; Admin → System stream lag |
| AI returns 503 | `AEGIS_AI_ENABLED`, key file mounted, worker on `egress_net` |
