# 115 Landing page, light and dark theme

**Status:** Built · **Owner:** danikadelacroix · **Depends on:** 006 · **Code:** `frontend/src/Landing.tsx`, `frontend/src/theme.tsx`, `frontend/src/index.css`

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

**The look** (added 28 Nov 2026, after review)

11. The logo is a 12-hour dial with one hour lifted out and moved: the day, with one job re-planned. It is drawn in warm black, off-white and safety orange, and works at 16 px as the favicon.
12. No gradients, glows, gradient text or blue and purple hues anywhere. Safety orange is the one signal colour: the main action and what needs attention. Green means fine, amber means short of a part, red means a missed promise.
13. Clock times and numbers are set in a monospaced face, so columns of times line up.
14. The landing page is laid out for this product, not as a centred template: the first screen shows the board with the stalled job moved, next to the words.

## Acceptance checks

| # | Check | How |
|---|---|---|
| M1 | Rules 1, 2: `/` shows the landing page; its first screen has the four answers and the demo button; `/demo` opens the demo, also when loaded directly | manual, local and on the hosted copy |
| M2 | Rule 3: the sections appear in order | manual |
| M3 | Rules 6, 7: the switch changes theme on both pages, the choice survives a reload, and no flash on load | manual |
| M4 | Rules 8, 11 to 14: both themes checked on the landing page, the demo with a stall open, and the board; no blue or purple left in the styles | manual, screenshots, a grep of the styles |
| M5 | Rule 9: the guide shows once, closes, stays closed after reload | manual |
| M6 | Rule 10: no sideways scroll at 375 px on either page | manual |

## Where it stands

Checked on 28 Nov 2026 in Chrome, locally: M1 `/` and `/demo` (also loaded directly), M2 section order,
M3 the switch on both pages and the choice surviving a reload, M4 both themes on the landing page and on
the demo with the RO-1013 stall open, M5 the guide closing and staying closed, M6 no sideways scroll at
375 px or 1280 px on either page.

After review the look was redone (rules 11 to 14): the dial logo and favicon, warm off-white and warm
black with safety orange as the one signal colour, green for in-progress bars and good numbers, IBM Plex
Mono for times and numbers, Archivo for text, and a landing page whose first screen shows the board with
RO-1013 moved and the decision ticket. A scan of every colour in the styles finds no blue, teal or purple
hue; the only gradient left is the striped hatching that marks a blocked bay. The hosted `/demo` path relies on the rewrite in `vercel.json`; check it after the
next deploy.

## Out of scope

Separate views per role, sign-in, and anything a role is or is not allowed to see. Those are decided
together first and built in a later milestone. Sound on the landing page, a video, or analytics.
