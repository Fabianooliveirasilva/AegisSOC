# ADR-0005: Sigma rules parsed with pySigma, evaluated by an in-house streaming evaluator

- **Status:** Accepted (2026-11-21, decision D-06)
- **Date:** 2026-11-21
- **Related:** SYSTEM_DESIGN.md §4; AC-DET-02/03; SR-12

## Context
Sigma is the standard detection format. pySigma converts rules into backend queries (e.g. for Splunk/Elastic). We evaluate rules on a stream of normalised events and also need retro-hunts over Postgres.

## Decision
Use pySigma (LGPL-2.1, as an unmodified library dependency) for parsing, validation and field mapping via an AegisSOC processing pipeline. Compile validated rules into an in-house Python predicate tree for streaming evaluation. Regex via RE2 (`google-re2`). Support a documented subset of modifiers/conditions; unsupported features fail static validation. Correlation rules (Sigma v2 correlation spec) parsed by pySigma; evaluated by our correlator with Redis state.

## Alternatives considered
| Option | Pros | Cons |
|---|---|---|
| Convert rules to SQL and poll | Reuse pySigma backends pattern | Polling latency, heavy DB load, no Postgres backend maintained for our schema |
| Use an external engine (e.g. Chainsaw/Zircolite) | Ready-made | File-oriented, not streaming; another language/runtime |
| **pySigma + own evaluator (chosen)** | Streaming, testable, explainable | We own correctness → conformance suite with ≥ 90 % branch coverage |

## Consequences
- Same evaluator powers detection, scenario tests and retro-hunts → one behaviour.
- ReDoS mitigated by RE2 (no backreferences/lookaround — documented limitation).
- SigmaHQ rules imported later must keep DRL 1.1 attribution.
