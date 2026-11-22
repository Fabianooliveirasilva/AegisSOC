# ADR-0012: REST API, URI versioning, code-first OpenAPI with committed snapshot

- **Status:** Accepted (2026-11-21, decision D-06)
- **Date:** 2026-11-21
- **Related:** API_SPECIFICATION.md; AC-PLAT-14

## Context
API contracts must be explicit and stable for the SPA, tests and Postman collections, while implementation is done by an AI that will evolve endpoints.

## Decision
REST/JSON under `/api/v1`, RFC 9457 errors, cursor pagination. FastAPI generates OpenAPI 3.1 from Pydantic models; the snapshot `docs/api/openapi.json` is committed; CI fails if stale and runs a breaking-change diff (`oasdiff`). Frontend types and the Postman collection are generated from the snapshot.

## Alternatives considered
| Option | Pros | Cons |
|---|---|---|
| Contract-first hand-written OpenAPI | Design-first rigour | Drift between YAML and code; double maintenance |
| GraphQL | Flexible queries | Harder authZ per field, caching, rate limiting; unnecessary |
| **Code-first + snapshot (chosen)** | Single source, reviewable diffs | Design intent lives in API_SPECIFICATION.md |

## Consequences
- Every PR changing the API shows the contract diff.
- Breaking changes require label + ADR.
