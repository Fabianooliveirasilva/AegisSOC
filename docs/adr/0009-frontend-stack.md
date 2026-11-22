# ADR-0009: Frontend stack — React, TypeScript, Vite, Tailwind, shadcn/ui, TanStack Query

- **Status:** Accepted (2026-11-21, decision D-06)
- **Date:** 2026-11-21
- **Related:** UI_UX_SPECIFICATION.md

## Context
Dense, accessible SOC UI built by an AI implementer; types must follow the API contract.

## Decision
React + TypeScript (strict) + Vite; Tailwind CSS v4 with design tokens; shadcn/ui components (copied source on Radix primitives); TanStack Query for server state, TanStack Table for grids; React Router; `openapi-typescript` + `openapi-fetch` for a typed client generated from the committed OpenAPI snapshot; Recharts for charts; CodeMirror 6 for YAML editing (S3). Fonts self-hosted.

## Alternatives considered
| Option | Pros | Cons |
|---|---|---|
| Next.js | SSR, routing | SSR unnecessary; extra server; complicates CSP/same-origin story |
| Mantine/MUI | Batteries included | Heavier theming for dense dark UI; less control |
| **Chosen stack** | Mainstream, MIT, strong typing, accessible primitives | More assembly work |

## Consequences
- No `dangerouslySetInnerHTML` (lint error).
- API changes require regenerating types (CI checks freshness).
