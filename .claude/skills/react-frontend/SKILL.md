---
name: react-frontend
description: AegisSOC frontend conventions. Use when writing or changing the React + TypeScript SPA under apps/web — routing, TanStack Query, the generated API client, shadcn/ui components, Tailwind design tokens, accessibility — or tests for it.
---

# react-frontend

Sources of truth: `docs/UI_UX_SPECIFICATION.md`, `docs/adr/0009-frontend-stack.md`, `docs/API_SPECIFICATION.md`, `SECURITY.md` (SR-10, SR-20) and the task in `docs/sprints/SPRINT_01.md`. When this skill and those documents disagree, the documents win; report the conflict.

## Stack
React + TypeScript (`strict`), Vite, Tailwind CSS v4 with design tokens as CSS variables, shadcn/ui (component source copied into the repo, on Radix), TanStack Query (server state), React Router, `openapi-typescript` + `openapi-fetch`, Vitest + Testing Library. Self-hosted fonts only (no CDN). A dependency outside `docs/sprints/SPRINT_01.md` §1 needs the maintainer's approval (HC-2).

## Structure
`src/app` (router, providers), `src/features/<module>` (pages, hooks, components), `src/components/ui` (shadcn), `src/lib` (API client, formatting). Only the screens of the current sprint exist: **no placeholders, nav items or references to future modules.**

## Rules
- **API types are generated** from the committed `docs/api/openapi.json` (`pnpm gen:api`); never hand-write request or response types. CI checks that they are fresh.
- One fetch middleware attaches `X-CSRF-Token` on POST/PUT/PATCH/DELETE and handles `401` by redirecting to `/login?next=…`. Do not scatter CSRF handling.
- **Render all data as text.** No `dangerouslySetInnerHTML` (ESLint `react/no-danger` is an error), no Markdown-to-HTML, no rendering of untrusted strings as markup. Log content, notes and names are attacker-controlled.
- No tokens or secrets in `localStorage` or `sessionStorage`; the session is an HttpOnly cookie.
- Navigation items and routes are filtered by the permissions returned from `GET /auth/me`; the server remains the authority.
- Every data view implements **loading, empty, error and 403** states (UI spec §7).
- Accessibility (WCAG 2.2 AA): keyboard operation, visible focus, proper table semantics, live regions for toasts, no information by colour alone, axe with zero serious or critical violations.
- AI-generated content is labelled and synthetic-derived metrics carry a SIMULATED badge (later sprints); do not design around them now.

## Testing
Vitest for the API middleware (CSRF header, 401 redirect), the auth provider and the permission-filtered navigation. Playwright journeys live in `qa/e2e/` (owned by the QA Engineer).

## Done when
`tsc --noEmit`, `eslint`, `prettier --check` and `vitest` pass with the commands and output recorded as evidence, and the QA Engineer (and Security Reviewer for CSRF, auth and rendering code) have validated independently.
