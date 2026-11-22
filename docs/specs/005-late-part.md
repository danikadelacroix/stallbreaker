# 005 Late part

**Status:** Built · **Code:** `backend/stalls.py` (`check_late`, `confirm_late`) · **Tests:** `tests/test_api.py`

## Why

A part already ordered will now arrive later. The manager needs to know at once whether the
plan still holds, and if not, what the new plan is.

## Rules

1. Only a part that is on its way (ordered ahead, or chosen in an approved stall) can be re-timed. Otherwise 409.
2. The new arrival time cannot be in the past (422). A job already finished, or already being worked on with its part, cannot be re-timed (409).
3. If the part still arrives no later than the job's start, the plan holds. The answer gives the spare minutes. Nothing is saved until the manager confirms.
4. Confirming saves the new arrival time and adds a `part_late_plan_holds` log entry. Confirming a time that does not hold is rejected with 409.
5. If the plan does not hold, the engine re-plans around the new arrival and returns a `late_part` proposal, approved like any other (004 rules 12 to 17).
6. For a car already taken apart, the re-plan keeps it in the same bay, its remaining work keeps the same length, and the blocked-bay hold is extended to the new restart time.
7. Any open proposal drafted for an older arrival time is replaced once a time that holds is checked.
8. Approving a late-part plan adds a `part_late_replanned` log entry.

## API

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/api/late/check` | `{ro_id, part_id, arrives_min}` | `{holds: true, starts_min, spare_min, arrives_min}` or `{holds: false, proposal}` |
| POST | `/api/late/confirm` | same | `{result, day}` |

## Acceptance checks

| # | Check | Test |
|---|---|---|
| A1 | Rules 3 and 4, including 409 past the spare time | `test_a_late_part_within_the_spare_time_changes_nothing` |
| A2 | Rules 1, 5, 6 and 8 | `test_a_late_part_for_a_dismantled_car_extends_the_blocked_bay` |

## Out of scope

Switching to a different source when a part runs late (it keeps its source today). Arrival
times as ranges.
