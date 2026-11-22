# ADR-0015: Detection-as-code with immutable versions, regression gate and four-eyes activation

- **Status:** Accepted (2026-11-21, decision D-06)
- **Date:** 2026-11-21
- **Related:** SYSTEM_DESIGN.md §4.1, §4.7, §8; AC-DET-07/08; AC-QA-03; T-12

## Context
Detection rules are the product's core value; a silently weakened rule is a blind spot. Rules are edited both in the UI and in git.

## Decision
Rules are files in `detections/` and immutable versions in the DB. `detections sync` imports changed files as **draft** versions only. A version becomes active only after static validation, passing positive and negative scenarios, a green regression run < 24 h old, and approval by a user other than the author. All transitions are audited. CI runs validation and scenarios on every relevant PR.

## Alternatives considered
| Option | Pros | Cons |
|---|---|---|
| Git as only source (GitOps) | Strong review | UI editing impossible; analysts can't tune quickly |
| DB only | Simple UI | No code review, no CI testing |
| **Both, with DB versions and file sync (chosen)** | Best of both | Two entry points to keep consistent (hash-based) |

## Consequences
- Demo requires two users with engineering permissions (seeded).
