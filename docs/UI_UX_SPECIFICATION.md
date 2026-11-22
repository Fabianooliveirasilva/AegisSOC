# AegisSOC — UI/UX Specification

| | |
|---|---|
| Stack | React + TypeScript, Tailwind CSS, shadcn/ui (Radix), TanStack Table/Query, Recharts |
| Theme | Dark SOC theme by default; light theme supported via tokens (not a priority) |
| Accessibility | WCAG 2.2 AA |

## 1. Design principles

1. **Triage speed over decoration.** Dense tables, keyboard shortcuts, stable layouts; colour is reserved for severity and state.
2. **Truth labelling.** Every AI-generated item says so; every synthetic-derived metric carries a SIMULATED badge; every timestamp shows timezone (UTC default, user toggle to local).
3. **Untrusted content looks untrusted.** Raw log fields render in monospace "data" containers, never as rich text.
4. **One primary action per screen.**

## 2. Information architecture and navigation

Left sidebar (collapsible to icons), top bar with global search (event/alert/incident IDs), environment badge `DEMO · SYNTHETIC DATA`, user menu.

```
┌──────────────┬───────────────────────────────────────────────────────────────┐
│ ◆ AegisSOC   │ [ Search IDs…              ]  DEMO·SYNTHETIC   ◐ UTC   jdoe ▾ │
│──────────────│───────────────────────────────────────────────────────────────│
│ ▣ Overview   │                                                               │
│ ⚑ Alerts  12 │                     page content                              │
│ ◎ Incidents 3│                                                               │
│ ≡ Events     │                                                               │
│ ⌕ Hunting    │                                                               │
│ ⛨ Detections │                                                               │
│   Rules      │                                                               │
│   Validation │                                                               │
│   ATT&CK     │                                                               │
│ ✦ AI Analyst │                                                               │
│ ✓ QA Reports │                                                               │
│ ⚙ Admin      │  (admin only: Users, Sources & keys, Retention, System, Audit)│
└──────────────┴───────────────────────────────────────────────────────────────┘
```

Navigation items are filtered by permission (AC-PLAT-13). Unbuilt modules are **not** shown during earlier sprints.

## 3. Screens

| # | Screen | Purpose | Key components | Sprint |
|---|---|---|---|---|
| 1 | Login | Authenticate | form, generic error, generic throttle message with retry countdown, caps-lock hint | S1 |
| 2 | Security overview | At-a-glance posture | KPI tiles (EPS, open alerts by severity, open incidents, MTTR), alert trend, top rules, ingestion health list, SIMULATED badges | S3 basic / S5 |
| 3 | Events explorer | Search & inspect telemetry | query builder (field/op/value chips) + text box, time range picker, results table (virtualised), histogram, field sidebar with top values, event detail drawer (JSON tree, copy), pivot to timeline | S2 |
| 4 | Alerts | Triage queue | filter bar, severity-sorted table, bulk select, side panel with matched events and rule summary, disposition dialog | S3 / S4 |
| 5 | Incident management | List & create | table with status/priority chips, "My incidents" tab, create dialog from alerts | S4 |
| 6 | Incident investigation | Work an incident | header (status stepper, severity, assignee), tabs: Summary · Alerts · Events · Timeline · Notes · Evidence · Playbook · AI; transition dialog with required fields | S4 |
| 7 | Detection rules | Manage rules | rule table (status, level, techniques, FP rate), rule detail: YAML editor (CodeMirror 6, YAML mode), validation findings gutter, version history with diff, ad-hoc test panel, lifecycle actions per role | S3 |
| 8 | Detection validation | Prove rules work | validation runs list, run detail (scenario × result grid, expected/actual diff), "Run regression" button, coverage summary, ATT&CK coverage matrix | S3 / S5 |
| 9 | Threat hunting | Hypothesis-driven search | hunt library, hunt editor (hypothesis, techniques, DSL or rule), results with group-by, run history, conclusion field, IOC lists & matches tab, related-activity panel | S4 |
| 10 | AI analyst | Assisted analysis | contextual panel (in alert/incident/rule) + standalone history page; task picker, status, result cards (finding, confidence badge, citations as links), proposed actions with Apply/Dismiss, "AI-generated" label, disabled empty state | S5 |
| 11 | QA reports | Quality evidence | quality indicators tiles, scenario pass trend, per-rule coverage table, downloadable reports | S5 |
| 12 | System administration | Operate the platform | users, sources & keys (one-time key reveal dialog), retention, system status (stream lag, workers, partitions), audit log viewer | S1 users (incl. login-throttle badge/reset and repeated-failure notices) / S2 audit log viewer + sources / S5 system |

### Incident investigation sketch

```
INC-42  Possible SSH brute force followed by login          [HIGH] [P2]  Assignee: jdoe ▾
New ─ Triage ─ ●Investigating ─ Containment ─ Eradication ─ Recovery ─ Closed     [Transition ▾]
┌ Summary │ Alerts 3 │ Events │ Timeline │ Notes 2 │ Evidence 1 │ Playbook 4/9 │ AI ┐
│ Entities: host web-01.corp.test · user root · ip 198.51.100.23                    │
│ ATT&CK:   T1110.001  T1078                                                         │
│ ┌ Timeline ───────────────────────────────────────────────────────────────────┐   │
│ │ 10:00:12  ALR-311 SSH brute force (12 events)                    detection  │   │
│ │ 10:04:55  ALR-312 Successful login after brute force             detection  │   │
│ │ 10:06:10  Status → Investigating                                    jdoe    │   │
│ │ 10:07:02  ✦ AI summary (confidence: medium · 4 citations)             AI    │   │
│ └─────────────────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────────────────────┘
```

## 4. Key user flows

1. **Alert triage:** Alerts → filter High+ → open → review events → (AI explain) → disposition *or* promote to incident.
2. **Investigation:** Incident → attach playbook → work steps → add evidence/notes → hunt related activity → transition to closed with resolution.
3. **Detection engineering:** Rules → New → paste/author YAML → validate → add scenarios → run validation → request approval → second user approves → activate.
4. **Threat hunt:** Hunting → new hunt with hypothesis → run → refine → record conclusion → attach to incident or create rule draft.
5. **Admin onboarding of a source:** Admin → Sources → create → generate key (shown once, copy) → watch health turn healthy.

## 5. Component inventory

App shell, sidebar, top bar, page header, KPI tile, severity badge, status chip, priority chip, SIMULATED badge, AI label, confidence badge, data table (sortable, virtualised, column chooser, row selection), filter bar, query builder chip, time range picker, JSON viewer, code/YAML editor, diff viewer, timeline list, stepper, drawer, dialog, toast, empty state, error state, skeleton loaders, pagination ("Load more" with cursor), file dropzone, copy-once secret dialog, ATT&CK matrix grid, sparkline, bar/line chart.

## 6. Design tokens

Defined as CSS variables (Tailwind theme extension). Contrast ratios verified ≥ 4.5:1 for text, ≥ 3:1 for UI components.

| Token | Dark | Use |
|---|---|---|
| `--bg` | `#0B0F14` | app background |
| `--surface` | `#121821` | cards, tables |
| `--surface-raised` | `#18202B` | drawers, dialogs |
| `--border` | `#263241` | dividers |
| `--text` | `#E6EDF3` | primary text |
| `--text-muted` | `#9AA7B4` | secondary text |
| `--accent` | `#3B82F6` | primary actions, focus ring |
| `--sev-critical` | `#F43F5E` | |
| `--sev-high` | `#F97316` | |
| `--sev-medium` | `#EAB308` | |
| `--sev-low` | `#22C55E` | |
| `--sev-info` | `#64748B` | |
| `--ai` | `#A78BFA` | AI labels |
| `--simulated` | `#14B8A6` | SIMULATED badge |

Typography: Inter (UI), JetBrains Mono (data) — self-hosted (no external font CDN, CSP `font-src 'self'`). Base size 14 px, dense table rows 32 px. Spacing scale 4 px. Radius 6 px. Severity is never conveyed by colour alone (icon + text).

## 7. States

| State | Pattern |
|---|---|
| Loading | skeleton rows for tables, spinners only for actions > 300 ms |
| Empty | icon + one sentence + primary action (e.g. "No alerts yet — start the demo generator: `make demo-data`") |
| Error | problem title + request ID + retry; 403 page explains missing permission; 401 redirects to login preserving return path |
| Partial | banner when a dependency is degraded (from `/health/ready` via `/overview`) |
| AI disabled | explanatory card with how to enable and what data would be sent |
| Long-running | AI analyses, validation runs and retro-hunts show queued/running with polling (2 s backoff to 10 s) |

## 8. Accessibility requirements

- WCAG 2.2 AA; axe-core in Playwright: 0 serious/critical violations on all main screens (TC-E2E-11).
- Full keyboard operation; visible focus ring; skip-to-content link; logical tab order in dialogs (Radix focus trap).
- Shortcuts (`j/k` row navigation, `/` search, `a` assign, `d` disposition) documented in a `?` overlay and disableable.
- Tables use proper `<table>` semantics; live regions for toasts and async status.
- Respect `prefers-reduced-motion`; no information only in charts (data tables available).
- Minimum target size 24×24 px.

## 9. Responsive behaviour

Primary target ≥ 1280 px. 768–1279 px: sidebar collapses to icons, detail panels become drawers. < 768 px: read-only views of overview, alerts and incidents (triage on mobile is out of scope).
