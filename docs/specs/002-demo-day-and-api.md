# 002 Demo day and API basics

**Status:** Built · **Code:** `backend/db.py`, `backend/seed.py`, `backend/repo.py`, `backend/app.py` · **Tests:** `tests/test_api.py`

## Why

Someone trying the demo has to be able to drive one realistic day, refresh the page, and reset it to the same
start.

## Rules

1. The demo day has 40 repair orders, 10 technicians, 8 lift bays and 2 flat bays, the home store "Main Street", two sister stores (North, 40 min away; East, 110 min away), a local vendor (60 min, $85) and an OEM depot (240 min, free).
2. The morning plan comes from the engine in deterministic mode and keeps every promise.
3. Seed 2026 always builds the same day. The clock starts at 10:30 (minute 150).
4. On that day `RO-1013` (water pump) starts at 10:30 in Bay 7 and its gasket kit `WTR-GSK` is out of stock. That is the demo stall. Reported at 10:30 it is caught before the car is taken apart; reported at 11:00 the car is on the lift and the bay stays blocked.
5. A job counts as in progress only after its start minute: a job starting this minute has not been taken apart yet. The engine and the board use the same rule.
6. Any change to the day (clock, ordering ahead, a confirmed arrival time, an approval) raises `plan_version`, so a plan drafted before the change cannot be approved.
7. Every part is tied to a real Monash Car Parts series for shortage risk (see 004).
8. Moving the clock changes what counts as done, running or scheduled. It never changes the plan.
9. Everything is stored in SQLite (`STALLBREAKER_DB`, default `backend/stallbreaker.db`). A refresh or a second browser sees the same state.
10. The database is created and seeded on first use.
11. Every request body is validated. Bad input gets 422, a missing thing 404, a conflict with the current state 409, each with a readable `detail`.

## API

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/api/health` | | `{ok, solver}` |
| GET | `/api/day` | | orders with parts, technicians, bays, segments, summary, `now_min`, `plan_version`, `open_proposal_id` |
| POST | `/api/clock` | `{now_min: 0..600}` | the day |
| POST | `/api/reset` | query `seed_value` (default 2026) | `{reset, day}` |
| GET | `/api/log` | | decision log, newest first |

Each order in the day has `status` (`done`, `in_progress`, `scheduled`, `waiting_for_part`),
`short_of_parts`, and per part `on_hand_home`, `sourced_from`, `arrives_min`, `shortfall`.

## Data model

`stores`, `suppliers`, `technicians`, `bays`, `parts`, `stock`, `job_types`, `job_type_parts`,
`repair_orders`, `ro_parts`, `assignments` (the live plan), `segments` (work done before a stall
and the blocked-bay hold), `sourced` (parts on their way), `proposals`, `audit_log`, `meta`
(`now_min`, `plan_version`). Plain SQL, no ORM.

## Acceptance checks

| # | Check | Test |
|---|---|---|
| A1 | Health answers | `test_health` |
| A2 | Rules 1 and 2, and the plan passes `validate` | `test_day_has_a_full_valid_plan` |
| A3 | Rule 4 | `test_orders_list_their_parts_and_home_stock` |
| A4 | Rule 8, and a clock out of range is rejected | `test_clock_changes_statuses_but_not_the_plan` |
| A5 | Rule 3 | `test_reset_is_repeatable` |
| A6 | Rule 5 | `test_a_job_starting_this_minute_has_not_started` |
| A7 | Rule 6 | `test_a_proposal_goes_stale_when_the_day_changes` |

## Out of scope

More than one home store, real dealer data, logins.
