# 106 UI tests

**Status:** Proposed · **Owner:** unassigned · **Depends on:** 006

## Why

The backend has 53 automated checks; the screen has none. The manual checks in 006 should run
on every change.

## Rules

1. Browser tests (Playwright) cover manual checks M1 to M6 from spec 006.
2. They run against a fresh test database (`STALLBREAKER_DB` pointed at a temp file) and the real API.
3. They find elements by role and label (the `aria-label`s already in the app), not by CSS class.
4. They run with one command and finish in under 2 minutes.
5. Component tests (Vitest) cover `buildView` in `App.tsx` and the time helpers in `api.ts`.

## Acceptance checks

| # | Check | Test |
|---|---|---|
| A1 | M1 to M6 automated | `frontend/e2e/*.spec.ts` (to write) |
| A2 | `buildView` marks moved jobs and the hatched bay for a preview | `frontend/src/App.test.ts` (to write) |
| A3 | `clock(150)` is `10:30` and `span` formats durations | `frontend/src/api.test.ts` (to write) |

## Out of scope

Visual screenshot comparison.
