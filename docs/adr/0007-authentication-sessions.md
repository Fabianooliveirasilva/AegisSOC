# ADR-0007: Server-side sessions with HttpOnly cookies and CSRF tokens; API keys for ingestion

- **Status:** Accepted (2026-11-21, decision D-06)
- **Date:** 2026-11-21
- **Related:** SECURITY.md SR-01…SR-08

## Context
Browser SPA on the same origin as the API; machine clients only for ingestion. Requirements: revocation on role change, idle timeout, minimal XSS blast radius.

## Decision
Browser users authenticate with username/password (argon2id) and receive an opaque server-side session (Redis) in a `__Host-` cookie (`Secure`, `HttpOnly`, `SameSite=Strict`). Unsafe requests carry a synchroniser CSRF token. Ingestion sources use per-source API keys (hashed, shown once, scoped to `/ingest/*`). No JWTs. MFA post-MVP. No external IdP in MVP.

## Alternatives considered
| Option | Pros | Cons |
|---|---|---|
| JWT in localStorage | Stateless | XSS steals tokens; revocation hard |
| JWT in cookie | Stateless-ish | Revocation still needs a store; no real benefit here |
| OIDC (Keycloak) | Enterprise realism, MFA | Another heavy container and config; out of scope for 10 weeks |
| **Server sessions (chosen)** | Instant revocation, no token in JS | Requires Redis availability for auth |

## Consequences
- Redis outage = authenticated API unavailable (documented, readiness reflects it).
- OIDC can be added later as another login method without changing session handling.

## Amendment — 2026-11-21 (decision D-09, approved by the maintainer)

**Context:** the planning audit (B-6) found that a hard lockout (10 failures → 15 min) lets an unauthenticated attacker keep any user, including the only admin, locked out indefinitely (T-31).

**Decision:** no hard lockout. Login protection is (1) a per-IP limit of 20 attempts/min and (2) a per-username progressive delay after 5 consecutive failures — 30 s, doubling per further failure, capped at 15 min — tracked in Redis for existing and unknown usernames alike. Attempts during the delay are rejected with 429 + `Retry-After` without verifying the password and without lengthening the delay. At 10 consecutive failures (and every 10 after), an `auth.login.repeated_failures` audit event notifies admins, who can reset the delay.

**Consequences:** brute force stays impractical (≤ ~100 guesses/day per username after the cap is reached); targeted denial is reduced to a visible, resettable slow-down (residual risk in THREAT_MODEL §6); `users.failed_login_count` / `locked_until` are removed from the schema; API gains `POST /users/{id}/reset-login-throttle` (replaces `/unlock`).
