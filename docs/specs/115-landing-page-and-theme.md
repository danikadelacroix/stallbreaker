# 115 Landing page, light and dark theme

**Status:** Proposed · **Owner:** danikadelacroix · **Depends on:** 006 · **Code:** `frontend/src/Landing.tsx`, `frontend/src/theme.ts`, `frontend/src/index.css`

## Why

Someone opening the link today lands straight on a dense schedule screen with no word on what the
product is, who it is for, or what to click first. A reviewer should know within ten seconds what
StallBreaker does and for whom, and within two minutes have used it.

## Rules

**The landing page**

1. The site opens on a landing page at `/`. The demo moves to `/demo`, and every page links to the other.
2. The first screen says, without scrolling: what StallBreaker is (a re-planning agent for dealership service departments), the problem it solves (a repair that stops for a missing or late part), what it does about it, and a button that opens the demo.
3. Below that, in this order: the problem; how it works in four steps (report, find every source, re-plan the day, approve and follow up); who it is for (service manager, technician, parts counter, each with what they do); what makes it different; the demo day's own numbers; how to try it in two minutes; and a footer that says the data is simulated and it is not connected to any dealer system.
4. Every number on the page comes from the demo day or the README and says so. Nothing claims an integration, a customer or a result that does not exist.
5. The roles are described as people who use it. The page says that in this prototype one screen serves all three.

**The theme**

6. Light and dark themes, switched from a button on every page. The first visit follows the device setting; a choice is remembered on that browser.
7. The page never flashes the wrong theme on load.
8. Every colour in the app comes from a theme token, so both themes keep text readable (WCAG AA contrast for body text) and the board's status colours distinct.

**Using the demo**

9. The demo shows a short "start here" guide on first visit: what the demo day is, the one stall to try first, and where to look. It can be closed and stays closed on that browser.

**Layout**

10. Both pages work from 375 px wide to a desktop screen with no sideways page scroll. Wide tables and the board scroll inside their own cards, as today.

## Acceptance checks

| # | Check | How |
|---|---|---|
| M1 | Rules 1, 2: `/` shows the landing page; its first screen has the four answers and the demo button; `/demo` opens the demo, also when loaded directly | manual, local and on the hosted copy |
| M2 | Rule 3: the sections appear in order | manual |
| M3 | Rules 6, 7: the switch changes theme on both pages, the choice survives a reload, and no flash on load | manual |
| M4 | Rule 8: both themes checked on the landing page, the demo with a stall open, and the board | manual, screenshots |
| M5 | Rule 9: the guide shows once, closes, stays closed after reload | manual |
| M6 | Rule 10: no sideways scroll at 375 px on either page | manual |

## Out of scope

Separate views per role, sign-in, and anything a role is or is not allowed to see. Those are decided
together first and built in a later milestone. Sound on the landing page, a video, or analytics.
