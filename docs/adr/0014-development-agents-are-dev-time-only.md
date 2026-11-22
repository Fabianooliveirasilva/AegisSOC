# ADR-0014: The eight specialised agents are development-time Claude Code subagents, not product runtime components

- **Status:** Accepted (2026-11-21, decision D-06)
- **Date:** 2026-11-21
- **Related:** AGENT_SPECIFICATION.md; SR-39

## Context
The master brief asks for Architect, Blue Team, Detection Engineer, Threat Hunter, QA, Security Reviewer, DevOps and Documentation agents. Mixing them into the product would give an AI broad privileges inside a security platform.

## Decision
These agents exist only in the development workflow as Claude Code subagents under `.claude/agents/`, orchestrated by the main session, with tool allowlists and project permission rules. The product's only runtime AI is the AI Analyst (ADR-0010), which is read-only and human-in-the-loop.

## Alternatives considered
| Option | Pros | Cons |
|---|---|---|
| Runtime multi-agent SOC ("Blue Team agent triages alerts") | Flashy | Excessive agency, cost, non-determinism in core flows |
| **Dev-time agents (chosen)** | Clear separation; agents improve engineering, not production decisions | Agent "skills" don't appear as product features |

## Consequences
- Path-level restrictions for agents are partly instruction-based (tool lists can't express paths); verified at PR review (TC-INF-05).
