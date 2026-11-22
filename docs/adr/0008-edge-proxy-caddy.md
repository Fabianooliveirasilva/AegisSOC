# ADR-0008: Caddy as edge proxy and static host (no separate API gateway)

- **Status:** Accepted (2026-11-21, decision D-06)
- **Date:** 2026-11-21
- **Related:** SR-19, SR-20, SR-22, SR-24, SR-41

## Context
We need TLS locally (for `Secure` cookies through a real hostname and realism), one origin for SPA + API (no CORS), security headers, body limits, and a single published port.

## Decision
Caddy 2 serves the built SPA, reverse-proxies `/api/*` to the API, terminates TLS with `tls internal`, sets security headers and body limits. It is the only container publishing ports (bound to 127.0.0.1). AuthN/AuthZ and rate limiting stay in the application.

## Alternatives considered
| Option | Pros | Cons |
|---|---|---|
| Nginx | Ubiquitous | Manual local certs; more config |
| Traefik | Dynamic config | More moving parts for static setup |
| Kong/APISIX gateway | Gateway features | Overkill; duplicate auth logic |
| **Caddy (chosen)** | Automatic local CA, concise config, Apache-2.0 | Users must trust local CA or accept warning |

## Consequences
- Proxy headers trusted only from the edge address (SR-41).
- `/metrics` is never routed through the edge.
