# agents/

Development-time agents are specified in [docs/AGENT_SPECIFICATION.md](../docs/AGENT_SPECIFICATION.md) ([ADR-0014](../docs/adr/0014-development-agents-are-dev-time-only.md)).

**Status: specified, not installed.** After approval, task S1-T15 creates the actual Claude Code subagent files in `.claude/agents/` (where Claude Code loads them). This folder then holds only supplementary material: agent evaluation notes and prompt change history.
