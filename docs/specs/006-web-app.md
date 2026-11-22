# 006 Web app

**Status:** Built · **Code:** `frontend/src/` · **Tests:** none automated yet (see 106)

## Why

A judge must be able to drive the whole flow without us touching the keyboard.

## Screen

| Part | File | Shows | Controls |
|---|---|---|---|
| Header | `App.tsx` | Demo clock; today at a glance (repair orders, done, in progress, still to start, promises missed, jobs missing a part) | Demo clock slider (locked while a stall is open); Reset day |
| Parts check | `PrecheckPanel.tsx` | "N jobs will be short of a part", one row per shortfall with its quiet fix or none | "Order the N that can arrive in time ($X)"; See the options (for jobs with no fix) |
| Schedule board | `Board.tsx` | Bays by time, one block per job; late jobs, waiting jobs and blocked bays marked; legend | Click a job to open it |
| Repair order | `OrderPanel.tsx` | Vehicle, times, technician, bay, parts with home stock and arrivals | Report missing; Running late? (opens the arrival-time slider for a part on its way) |
| Missing part | `StallCard.tsx` | Source table with stock, arrival, cost, risk and why; one or two plan cards; no re-plan comparison | Use this one (force a source); Let the engine choose; Show on the board; Approve this plan; Close without deciding |
| Decision log | `LogPanel.tsx` | Every decision, newest first, with draft customer messages | |

## Rules

1. All data comes from the API (`src/api.ts`). The browser keeps no state of its own that a refresh would lose.
2. An open proposal is shown again after a refresh.
3. Showing a plan on the board previews it: the blocked bay is hatched and moved jobs are outlined. The live plan changes only on approve.
4. Unsafe sources are marked and explained in words, never just a number.
5. Every control is a real button with a readable label. Board blocks have an `aria-label` with the job, times, technician and any warning.
6. Works at phone width (375 px) with no sideways page scroll. The board scrolls inside its own box.
7. Buttons are disabled while a request is running.
8. Plain words only: "promise time", "jobs moved", "bay blocked", never solver terms.

## Manual checks (until 106 is built)

| # | Check |
|---|---|
| M1 | Reset, open RO-1013, report the gasket kit missing: sources and a plan appear within 5 seconds |
| M2 | Show the plan on the board, then approve: the board redraws and the log has the entry |
| M3 | Refresh with a proposal open: it is still there |
| M4 | "Order the 3 that can arrive in time ($45)": the count drops and the board does not move |
| M5 | Slide a part's arrival later: "plan holds" until past the job start, then "See the new plan" |
| M6 | 375 px wide: no sideways scroll |

## Run

```bash
cd frontend && npm install && npm run dev      # http://localhost:5173, API on port 8000
npx tsc -b && npx oxlint && npm run build      # before every push
```
