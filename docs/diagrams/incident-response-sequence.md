# Incident response sequence

```mermaid
sequenceDiagram
  autonumber
  actor An as Analyst
  participant UI as SPA
  participant API as API
  participant AI as Worker: AI runner
  participant LLM as Anthropic API
  participant DB as PostgreSQL

  An->>UI: open alert queue
  UI->>API: GET /alerts?status=new
  An->>UI: triage alert (acknowledge)
  UI->>API: PATCH /alerts/{id} {status: triaging}
  API->>DB: update + audit_log
  An->>UI: promote to incident
  UI->>API: POST /incidents {alert_ids, severity, title}
  API->>DB: incident + incident_alerts + timeline + audit
  API->>DB: attach default playbook by rule/technique mapping
  An->>UI: request AI summary
  UI->>API: POST /ai/analyses {target: incident, task: summarize}
  API-->>UI: 202 {analysis_id}
  API->>AI: XADD aegis:jobs:ai
  AI->>DB: build minimised context (RBAC of requester)
  AI->>LLM: messages (system rules + untrusted data block + read-only tools)
  LLM-->>AI: tool_use (get_event / search_events)
  AI->>DB: run tool with requester's permissions, bounded
  AI->>LLM: tool_result
  LLM-->>AI: structured result (findings with citations, confidence, proposed_actions)
  AI->>AI: validate schema + citations ⊆ context IDs
  AI->>DB: store analysis (status=completed | rejected | refused)
  UI->>API: GET /ai/analyses/{id}
  An->>UI: review; accept proposed action "set severity=high"
  UI->>API: POST /ai/analyses/{id}/actions/{action_id}/apply
  API->>DB: PATCH incident (actor = analyst, ai_suggested=true) + audit
  An->>UI: work playbook steps, add notes & evidence
  UI->>API: POST /incidents/{id}/evidence (file → SHA-256)
  An->>UI: transition containment → recovery → closed (resolution)
  UI->>API: POST /incidents/{id}/transitions
  API->>DB: validate transition, timeline, audit, dispositions → alerts
```
