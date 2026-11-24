# 105 Run anywhere: deployed and offline

**Status:** Proposed · **Owner:** unassigned · **Depends on:** 002

## Why

Anyone should be able to open a link. And the demo must still run on a laptop with no
internet.

## Rules

1. One command starts the whole app locally: API and built frontend served together on one port.
2. Offline, everything works except the LLM step, which falls back as in 103.
3. A hosted copy runs the same code. The frontend calls the API through one configurable base URL, not a hard-coded localhost.
4. Allowed browser origins (CORS) come from an environment variable, not a hard-coded list.
5. The hosted demo database resets to the seed day on start, and "Reset day" works for every visitor.
6. No secret is committed. Hosting settings are documented in the README.
7. The hosted copy survives a cold start: the first request may be slow but must not fail.

## Acceptance checks

| # | Check | Test |
|---|---|---|
| A1 | Rule 1 on a clean clone | manual check, steps written in README |
| A2 | Rule 2 with Wi-Fi off | manual check |
| A3 | Rules 3 and 4: frontend build uses the configured base URL; CORS reads the variable | `test_cors_origins_come_from_the_environment` (to write) |
| A4 | Hosted link opens and the demo stall works end to end | manual check |

## Out of scope

Logins, more than one demo database per visitor.

## Open questions

- Which hosting accounts can we use (for example Vercel for the frontend, Render for the API)? Team decides.
