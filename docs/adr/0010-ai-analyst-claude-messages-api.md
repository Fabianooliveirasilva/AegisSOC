# ADR-0010: AI analyst on the Claude Messages API with host-side read-only tools and human-in-the-loop

- **Status:** Accepted (2026-11-21, decision D-06)
- **Date:** 2026-11-21
- **Related:** SYSTEM_DESIGN.md §7; SR-28…SR-33; AC-AI-*

## Context
The AI must explain, summarise and suggest — never decide — with citations, confidence, prompt-injection resistance and data minimisation. The data it needs lives in the local database.

## Decision
- Provider interface with `AnthropicProvider` (official `anthropic` Python SDK, Messages API) and a deterministic `FixtureProvider` (tests, offline demo).
- Analyses run as async worker jobs. A host-side loop exposes only read-only tools executed with the requester's permissions, with call and row limits.
- Final output constrained with structured outputs (`output_config.format`, JSON Schema) and re-validated with Pydantic; citations must reference IDs present in the analysis context.
- Consequential actions are returned as proposals that a human applies via the normal API.
- Model configurable (`AEGIS_AI_MODEL`, default `claude-opus-5-5`, effort `medium`); adaptive thinking (model default); refusal handling via `stop_reason` with server-side fallback enabled by default (configurable).
- Disabled by default; no egress unless enabled.

## Alternatives considered
| Option | Pros | Cons |
|---|---|---|
| Managed Agents (Anthropic-hosted loop + sandbox) | No harness to own | Data would need to reach a hosted sandbox; tools read our local DB; short, code-controlled loop doesn't need it |
| Free-form chat | Flexible | No structure, no citation enforcement |
| Agent with write tools | "Autonomous SOC" demo | Violates HITL requirement; excessive agency risk |
| **Messages API + read-only tools + HITL (chosen)** | Data stays host-side except minimised context; verifiable outputs | We own the loop (small) |

## Consequences
- Cost bounded by quotas and a daily token budget.
- Safety classifiers may refuse some security content; the fixture provider keeps demos deterministic; live results reported honestly.
- Exact SDK usage must be checked against current docs at implementation (HANDOFF rule).
- Model choice for cheaper tasks is an open decision (D-04).
