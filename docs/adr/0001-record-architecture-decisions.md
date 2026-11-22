# ADR-0001: Record architecture decisions

- **Status:** Accepted (2026-11-21, decision D-06)
- **Date:** 2026-11-21
- **Deciders:** human maintainer; Architect Agent

## Context
Implementation is delegated to an AI model across many sessions. Undocumented decisions get silently re-made or contradicted.

## Decision
Significant decisions are recorded as ADRs in `docs/adr/` using `0000-template.md`. An ADR is *Proposed* until the human marks it *Accepted*. A change is **significant** if it alters a component, module boundary, data ownership, external integration, runtime dependency, security control, API contract or a CI gate. Implementers must propose an ADR and wait for approval before implementing a significant change.

## Alternatives considered
| Option | Pros | Cons |
|---|---|---|
| Decisions only in design docs | One place | No history of why; easy to overwrite |
| ADRs (chosen) | Immutable history, reviewable | Small overhead |

## Consequences
- Every PR that implements a significant change links an Accepted ADR.
- Superseded ADRs stay in the repo.
