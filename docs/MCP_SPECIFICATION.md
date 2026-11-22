# AegisSOC — MCP Integration Specification

| | |
|---|---|
| Status | **All project MCP servers are proposed, none configured.** No `.mcp.json` exists in this repository. |
| Principle | Read-only where possible; narrowest scope; no secrets in config files; development-time only (the product itself does not use MCP) |

## 1. Availability

| Server | State in the maintainer's environment today | Proposed for project |
|---|---|---|
| Context7 (library docs) | Installed as a Claude Code plugin, **requires authorisation** (not usable in the planning session) | Yes — after the maintainer authorises it via `/mcp` |
| GitHub MCP | Not configured | Yes (once a GitHub remote exists) |
| Playwright MCP | Not configured | Yes (QA exploratory testing) |
| PostgreSQL MCP | Not configured | Optional, read-only, local dev DB only |
| Semgrep MCP | Not configured | Optional; CLI via Bash is sufficient, so **not recommended** for MVP |

## 2. Server specifications

### 2.1 GitHub MCP (official `github/github-mcp-server`)
- **Purpose:** read issues/PRs, post review comments from QA/Security notes, read CI run status.
- **Capabilities needed:** repos (read), issues (read/write comments), pull requests (read, comment), actions (read).
- **Permission scope:** fine-grained PAT restricted to **this repository only**: Contents read, Issues read/write, Pull requests read/write, Actions read, Metadata read. **No** admin, workflows write, secrets, packages, or contents write. Enable the server's read-only mode by default; switch it off only for comment-posting sessions.
- **Authentication:** PAT in the environment variable `GITHUB_PERSONAL_ACCESS_TOKEN`, referenced from config via `${…}` expansion — never written to the file.
- **Security implications:** a write-capable token could alter issues/PR text; merge is denied by scope and by `.claude/settings.json` (`gh pr merge` denied) and by branch protection.
- **Workflows:** QA posts validation note to PR; Security posts review note; orchestrator reads CI failures.
- **Failure handling:** if unavailable, agents write notes to `qa/reports/` and the human pastes them; never fall back to `curl` (denied).

### 2.2 Playwright MCP (`@playwright/mcp`)
- **Purpose:** exploratory testing of the local stack by the QA agent; reproduce UI bugs with screenshots.
- **Capabilities:** navigate, click, fill, snapshot, screenshot.
- **Scope:** `--allowed-origins https://localhost:8443` (only the local edge), `--isolated` browser profile, headless; no file uploads outside `qa/fixtures/uploads/`.
- **Authentication:** demo user credentials from the seeded demo accounts, supplied at runtime by the human; never stored in config.
- **Security implications:** a browser agent can be prompt-injected by page content (our page shows attacker-controlled log data!). Mitigation: only local origin allowed; QA agent instructions treat page text as data; no credentials of real accounts.
- **Workflows:** exploratory session per sprint (≤ 30 min), bug reproduction.
- **Failure handling:** fall back to Playwright test scripts (`make test-e2e`).

### 2.3 PostgreSQL MCP (read-only)
- **Purpose:** let the QA/Detection agents inspect demo data (e.g. alert counts, validation results) without writing ad-hoc SQL scripts.
- **Choice:** the original reference server `@modelcontextprotocol/server-postgres` has been archived by its maintainers; select a maintained read-only Postgres MCP server at approval time (decision D-07). Requirements: read-only transactions, connection string from env, query timeout.
- **Scope:** connects as `aegis_mcp_ro` (DATABASE_DESIGN §6): SELECT on curated views only, no access to `users`, `api_keys`, `audit_log.details`; `statement_timeout=5s`; local dev database only, never CI or anything else.
- **Authentication:** `AEGIS_MCP_DATABASE_URL` env var; the `aegis_mcp_ro` role and its random password (git-ignored secrets folder) are created only after D-07 approves this server.
- **Security implications:** data in the DB is attacker-influenced (log content) → prompt injection risk for the agent; read-only role prevents damage; curated views limit exposure.
- **Failure handling:** agents use `make psql-ro` (same role) instead.

### 2.4 Context7
- **Purpose:** current documentation for FastAPI, SQLAlchemy, pySigma, TanStack, Playwright etc. to avoid stale API usage.
- **Scope:** public library docs, read-only. No repository data sent beyond library names/queries.
- **Authentication:** handled by the plugin's OAuth flow — maintainer must authorise via `/mcp` in an interactive session.
- **Failure handling:** official docs websites; `claude-api` skill for Anthropic SDK.

## 3. Proposed configuration (not active)

To be written to `.mcp.json` only after approval (S1-T15). Secrets come from the environment; the file contains none.

```json
{
  "mcpServers": {
    "github": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/",
      "headers": { "Authorization": "Bearer ${GITHUB_PERSONAL_ACCESS_TOKEN}", "X-MCP-Readonly": "true" }
    },
    "playwright": {
      "type": "stdio",
      "command": "npx",
      "args": ["@playwright/mcp@<pinned-version>", "--headless", "--isolated", "--allowed-origins", "https://localhost:8443"]
    }
  }
}
```

The exact server packages, versions and flags must be verified against each server's current documentation at creation time; the snippet shows intent (pinning, read-only, origin restriction, env-sourced secrets), not a tested configuration.

## 4. MCP review checklist (TC-INF-05)

- [ ] No secret literal in `.mcp.json` (Gitleaks + manual)
- [ ] Each server has a documented purpose and owner agent
- [ ] Scopes match §2 (PAT permissions screenshot/notes in PR)
- [ ] Read-only mode enabled where offered
- [ ] Versions pinned
- [ ] Server removed when no longer used
