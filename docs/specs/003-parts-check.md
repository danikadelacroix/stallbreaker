# 003 Parts check

**Status:** Built · **Code:** `backend/precheck.py`, `backend/repo.py` (`peg`) · **Tests:** `tests/test_api.py`

## Why

The cheapest stall is the one that never happens. Before a car is taken apart, find the jobs
that will run short of a part and order the part while there is still time.

## Rules

1. The home store's shelf stock is handed out to the open jobs in the order they start ("pegging"). Parts already on their way for a job are skipped.
2. A need that cannot be met is flagged with a reason: `out_of_stock` (the shelf never had enough) or `claimed_by_earlier_jobs` (it is on the shelf but earlier jobs will use it).
3. For each flagged job that has not started, look for the cheapest safe source that arrives no later than the job's start. If there is one, it is the job's `fix`.
4. A job already started, or already waiting for a part, has no quiet fix. It needs the stall flow (004).
5. "Order the fixes" places every fix without touching the schedule. Each order is re-checked against live stock, because one order can use up what another relied on.
6. Ordering is idempotent: a second run orders nothing.
7. The order raises the job's release time to the arrival time and adds a `parts_ordered_ahead` entry to the log.

In a dealership this would run every night for the next day. In the demo it runs on the rest of today.

## API

| Method | Path | Returns |
|---|---|---|
| GET | `/api/precheck` | `{checked_at_min, jobs_checked, flagged[], fixable_without_replan, need_a_decision, fix_cost}` |
| POST | `/api/precheck/order` | `{placed[], precheck, day}` |

Each flagged entry: `ro_id, vehicle, description, start_min, promise_min, part_id, part_name, qty, reason, already_started, fix`.

## Acceptance checks

| # | Check | Test |
|---|---|---|
| A1 | Rules 2 to 4: the demo stall is flagged `out_of_stock` with no fix; every fix arrives before its job starts; at least one `claimed_by_earlier_jobs` | `test_parts_check_finds_shortfalls_and_says_which_can_be_fixed_quietly` |
| A2 | Rules 5 to 7: schedule unchanged, fixed jobs no longer short, log entry, second run orders nothing | `test_ordering_ahead_fixes_jobs_without_touching_the_schedule` |

On the seed-2026 day at 10:30 the check finds 5 shortfalls: RO-1013 needs a decision now,
RO-1007 needs a re-plan, and RO-1017, RO-1035 and RO-1040 can be ordered for $45 in total.

## Out of scope

Reorder points and purchasing policy, supplier stock levels (suppliers always have the part).
