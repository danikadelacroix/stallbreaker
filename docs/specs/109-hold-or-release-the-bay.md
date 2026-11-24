# 109 Hold the bay, or roll the car out?

**Status:** Built · **Owner:** danikadelacroix · **Depends on:** 001, 004 · **Code:** `shopcore.py` (`hold_or_roll_out`), `backend/stalls.py`

## Why

A simple planner assumes a waiting car leaves its bay. Ours assumed it never can. A real shop
decides case by case: a car with its wheels off can be put back together enough to roll out in
20 minutes; a car with the engine out cannot move at all. Making that a decision the engine
takes covers both, and each simpler assumption becomes a special case of it.

## Rules

1. Each job type says whether a car taken apart can be made movable, and how many technician minutes that takes (`roll_out_min`), plus the minutes to set it up again (`set_up_min`). Water pump, timing belt and suspension work cannot be moved.
2. For a stall in progress the engine plans both ways. Hold: the bay stays blocked until the work is done. Roll out: the same technician spends `roll_out_min` now, the bay is free after that, and what is left of the job plus `set_up_min` is done later in any bay of the right kind, once the part is here.
3. Both ways are planned with the source chosen inside the model, under the same goal order.
4. The car is rolled out only if that is strictly better on missed promises, late minutes or sourcing cost, in the goal order. Moving fewer jobs is not a reason: rolling a car out costs technician time, so it has to earn it. On a tie the car stays in its bay.
5. Every plan says which way was chosen and why in one sentence, and what the other way would have cost.
6. `validate` checks a rolled-out plan as what it physically is: the bay and the technician are busy until the car is out, and nothing else may use them before then.
7. With no movable cars, results are unchanged.
8. A manager can ask for the other way (`force_bay`) and approve it. A car that cannot be moved, or has not been taken apart, cannot be forced out (422).
9. After a roll-out is approved the car is an ordinary job again: it is not pinned, no bay is held, and its part can still run late like any other. A car already waiting in its bay stays there when its part runs late.
10. A plan that rolls a car out always needs a person, and says so.

## API

`POST /api/stalls` takes `force_bay` (`hold` or `roll_out`). Each plan option gains `bay_decision` (`hold`, `roll_out` or null when work had not started), `bay_note` and `rolled_out_until`. The proposal gains `forced_bay` and `can_roll_out`. Each order in the day gains `roll_out_min` and `set_up_min`.

## Acceptance checks

| # | Check | Test |
|---|---|---|
| A1 | A job type that cannot move is always held | `test_a_car_that_cannot_be_moved_is_always_held`, `test_a_car_that_cannot_be_moved_keeps_its_bay_and_says_so` |
| A2 | A designed day where rolling out saves a promise: the engine rolls out | `test_rolling_the_car_out_frees_the_bay_when_that_saves_a_promise` |
| A3 | A designed day where rolling out saves nothing: the engine holds | `test_the_car_stays_put_when_rolling_it_out_would_help_nobody` |
| A4 | Rule 4: not rolled out just to move fewer jobs | `test_a_car_is_not_rolled_out_just_to_move_fewer_jobs` |
| A5 | Rule 6: the checker rejects a job in a bay the car has not left | `test_the_checker_catches_a_rolled_out_car_that_was_never_really_moved` |
| A6 | Rule 7 | `test_without_movable_cars_the_decision_changes_nothing`, and the six benchmark rows are unchanged |
| A7 | Rules 5 and 8 to 10 in the app | `test_on_a_day_with_free_bays_the_car_stays_put_and_the_card_says_why`, `test_a_manager_can_roll_the_car_out_anyway_and_approve_it`, `test_a_car_that_cannot_move_cannot_be_forced_out` |
| A8 | Where it pays, measured | `experiments/roll_out.py`, output in `experiments/out/roll_out_summary.md` |

## What the measurement says

Rolling out pays when bays are scarce or the part is far away. With two lift bays and the part
six hours away it cut missed promises from 1.70 to 1.07 per stall. With three lift bays and
fast sources it was never chosen in 84 movable stalls, and on the demo day (eight lift bays)
it never beats holding the bay. The app says so on the plan card.

## Open questions

- Roll-out and set-up minutes per job type are our assumption. Ask a service manager for real ones.
- A day with a waiting line of unbooked work would value a freed bay even when no booked promise is at risk. Our days have no such work, so the engine does not count it.
